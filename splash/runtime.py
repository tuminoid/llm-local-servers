"""Managed Splash lifecycle, model identity and live capacity evidence.

No workload logic lives here. The embedded runtime supplies the upstream
installer and Hugging Face client; lifecycle inspection is stdlib.
"""

import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("SPLASH_DATA_DIR", Path(os.environ.get(
    "XDG_DATA_HOME", Path.home() / ".local/share")) / "splash"))
STATE = Path(os.environ.get("SPLASH_STATE_DIR", Path(os.environ.get(
    "XDG_STATE_HOME", Path.home() / ".local/state")) / "splash"))
VERSION = os.environ.get("SPLASH_VERSION", "1.5.0")
RELEASE = DATA / "runtime" / VERSION
PYTHON = RELEASE / "python/bin/python3"
PIDFILE = STATE / "server.json"
LOG = STATE / "server.log"
CONFIG_KEYS = tuple("SPLASH_" + name for name in (
    "MODEL_REPO", "MODEL_REVISION", "DRAFT_REPO", "DRAFT_REVISION", "MAX_LEN",
    "CAP_REASONING", "CAP_TOOLS", "CAP_REASONING_MODE", "CAP_DISABLE_MODE",
    "CAP_SYSTEM_PROMPT", "SAMPLING",
))


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def config_path(tag):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", tag):
        raise ValueError("MODEL must name a Splash model config")
    return Path(os.environ.get("SPLASH_MODEL_CONF", ROOT / "models" / (tag + ".conf"))).resolve()


def config(tag):
    path = config_path(tag)
    script = 'set -eu; source "$1"; shift; for name; do printf "%s\\0" "${!name}"; done'
    output = subprocess.check_output(["bash", "-c", script, "bash", str(path), *CONFIG_KEYS])
    values = dict(zip(CONFIG_KEYS, output.decode().split("\0")[:-1]))
    for key in ("SPLASH_MODEL_REPO", "SPLASH_DRAFT_REPO"):
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", values[key]):
            raise ValueError(f"{key} must be a full Hugging Face repository ID")
    for key in ("SPLASH_MODEL_REVISION", "SPLASH_DRAFT_REVISION"):
        if not re.fullmatch(r"[0-9a-f]{40}", values[key]):
            raise ValueError(f"{key} must be an immutable commit")
    if int(values["SPLASH_MAX_LEN"]) <= 0:
        raise ValueError("SPLASH_MAX_LEN must be positive")
    return values


def upstream():
    sys.path.insert(0, str(RELEASE))
    from install import assembly, hub
    return assembly, hub


def draft_snapshot(values):
    _assembly, hub = upstream()
    return hub.snapshot(values["SPLASH_DRAFT_REPO"], values["SPLASH_DRAFT_REVISION"])


def installer(values, *command):
    """Run the release's installer for the pinned target and draft. The
    installer has no draft revision option and installs a draft repository's
    default branch, so the draft is passed as its pinned snapshot directory."""
    return [str(PYTHON), "-m", "install.models", "--models", str(DATA / "models"),
            "--model", values["SPLASH_MODEL_REPO"], "--revision", values["SPLASH_MODEL_REVISION"],
            "--draft-model", str(draft_snapshot(values)), *command]


def model_path(values):
    link = subprocess.check_output(installer(values, "link"), cwd=RELEASE, text=True).strip()
    return Path(link)


def verify_model(values):
    assembly, hub = upstream()
    path = model_path(values)
    record = assembly.verify(path, full=True)
    target = record["sources"]["target"]
    if target != {"repo": values["SPLASH_MODEL_REPO"], "revision": values["SPLASH_MODEL_REVISION"]}:
        raise RuntimeError("installed target differs from the config; run make splash-pull")
    draft = draft_snapshot(values).resolve()
    linked = [entry["path"] for name, entry in record["files"].items() if name.startswith("draft/")]
    if not linked or any(hub.snapshot_of(item) != draft for item in linked):
        raise RuntimeError("installed draft differs from the config; run make splash-pull")
    return {
        "source": values["SPLASH_MODEL_REPO"], "revision": target["revision"],
        "draft_source": values["SPLASH_DRAFT_REPO"], "draft_revision": values["SPLASH_DRAFT_REVISION"],
        "family": record["family"], "target_format": record["target_format"],
        "vision_format": record["vision_format"],
        "model_record_sha256": digest(path / "model.json"),
        "full_artifact_hash_verification": True,
    }


ENGINE_FILES = (("splash", "binary_sha256"), ("splash.metallib", "metallib_sha256"))


def verify_release():
    release = json.loads((RELEASE / "release.json").read_text())
    receipt = json.loads((RELEASE / "installation.json").read_text())
    if release["version"] != VERSION or receipt["archive_sha256"] != os.environ["SPLASH_ARCHIVE_SHA256"]:
        raise RuntimeError("installed runtime does not match the release pin")
    for name, key in ENGINE_FILES:
        # 1.5.0's release.json no longer states them; install records them
        # from the checksum-verified archive.
        expected = release.get(key) or receipt.get(key)
        if digest(RELEASE / "engine" / name) != expected:
            raise RuntimeError(f"runtime checksum mismatch: {name}")
    return {**release, **receipt}


def require_stopped():
    if PIDFILE.exists():
        raise RuntimeError(f"managed state exists at {PIDFILE}; run make splash-stop first")


def require_host():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Splash requires Apple Silicon (M3 or newer) and macOS 26.4+; "
                           f"this host is {platform.system()}/{platform.machine()}")


def install():
    require_stopped()
    require_host()
    if tuple(map(int, platform.mac_ver()[0].split(".")[:2])) < (26, 4):
        raise RuntimeError("Splash requires macOS 26.4+")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", VERSION):
        raise ValueError("invalid Splash version")
    checksum = os.environ.get("SPLASH_ARCHIVE_SHA256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("SPLASH_ARCHIVE_SHA256 must pin the release archive")
    if RELEASE.exists():
        verify_release()
        subprocess.run([str(PYTHON), "-c", "import huggingface_hub, tokenizers, jsonschema"], check=True)
        print(f"Splash {VERSION} already installed at {RELEASE}")
        return
    RELEASE.parent.mkdir(parents=True, exist_ok=True)
    archive = RELEASE.parent / f"splash-{VERSION}.tar.gz"
    url = f"https://github.com/incoai/splash/releases/download/{VERSION}/splash-{VERSION}-arm64-macos26.tar.gz"
    print(f"Downloading {url}", flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as output:
        shutil.copyfileobj(response, output)
    if digest(archive) != checksum:
        raise RuntimeError(f"release archive checksum mismatch; retained {archive}")
    # Extract only the checksum-verified upstream archive. Keep failed staging
    # directories for diagnosis; never recursively replace an installed tree.
    stage = Path(tempfile.mkdtemp(prefix=".install-", dir=RELEASE.parent))
    subprocess.run(["tar", "-xzf", str(archive), "-C", str(stage)], check=True)
    extracted = stage / f"splash-{VERSION}-arm64-macos26"
    save(extracted / "installation.json", {
        "archive_sha256": checksum, "archive_url": url,
        **{key: digest(extracted / "engine" / name) for name, key in ENGINE_FILES}})
    extracted.rename(RELEASE)
    stage.rmdir()
    verify_release()
    subprocess.run([str(PYTHON), "-c", "import huggingface_hub, tokenizers, jsonschema"], check=True)
    print(f"Installed Splash {VERSION} at {RELEASE}")


def pull(values):
    require_stopped()
    verify_release()
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=values["SPLASH_DRAFT_REPO"], revision=values["SPLASH_DRAFT_REVISION"])
    subprocess.run(installer(values, "prepare"), cwd=RELEASE, check=True)
    # The installer pins only Hub sources; pin the draft snapshot too, so
    # pruning the Hub cache cannot remove the files the assembly links.
    _assembly, hub = upstream()
    hub.pin(draft_snapshot(values), values["SPLASH_DRAFT_REPO"], model_path(values))
    identity = verify_model(values)
    print(f"Verified {identity['source']} at {identity['revision']} with draft "
          f"{identity['draft_source']} at {identity['draft_revision']}")


def command(values):
    host = os.environ.get("SPLASH_HOST", "127.0.0.1")
    if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
        if not os.environ.get("SPLASH_API_KEY"):
            raise RuntimeError("non-loopback SPLASH_HOST requires SPLASH_API_KEY")
    port = int(os.environ.get("SPLASH_PORT", "8022"))
    if not 1 <= port <= 65535:
        raise ValueError("SPLASH_PORT must be 1..65535")
    # The resolved assembly, as the release launcher serves it: the link may
    # advance on a later install, the assembly it names does not.
    path = model_path(values).resolve(strict=True)
    return [str(PYTHON), "-u", "-P", "-m", "server.server",
            str(path), "--model", values["SPLASH_MODEL_REPO"], "--binary", str(RELEASE / "engine/splash"),
            "--host", host, "--port", str(port), "--no-webui",
            "--max-context", values["SPLASH_MAX_LEN"],
            "--max-memory", os.environ.get("SPLASH_MAX_MEMORY", "64G"),
            "--request-timeout", os.environ.get("SPLASH_REQUEST_TIMEOUT", "7200")]


def port_free(host, port):
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((host, port))


def processes():
    output = subprocess.check_output(["ps", "-axo", "pid=,pgid=,stat=,lstart=,args="], text=True)
    result = {}
    for line in output.splitlines():
        parts = line.split(None, 8)
        if len(parts) == 9:
            result[int(parts[0])] = {"group": int(parts[1]),
                                    "state": parts[2], "started": " ".join(parts[3:8]),
                                    "command": parts[8]}
    return result


def owned_group(owner):
    pid = owner["pid"]
    if type(pid) is not int or pid <= 1:
        raise RuntimeError("invalid managed PID")
    all_processes = processes()
    leader = all_processes.get(pid)
    if leader and (leader["group"] != pid or leader["started"] != owner["started"]):
        raise RuntimeError("managed PID has been reused; refusing to signal it")
    members = {key: value for key, value in all_processes.items() if value["group"] == pid}
    allowed = (owner["command"][0], str(ROOT / "start.sh"), str(ROOT / "runtime.py"),
               owner["command"][owner["command"].index("--binary") + 1])
    if any(not member.get("state", "").startswith("Z")
           and not any(path in member["command"] for path in allowed)
           for member in members.values()):
        raise RuntimeError("managed process group contains an unrecognized process")
    return members


def group_alive(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # macOS can reject signals while a native worker is exiting.
        # EPERM still means the group exists; keep waiting for release.
        return True
    return True


class Authorization(urllib.request.BaseHandler):
    """Add credentials only to this managed origin, including harness requests."""

    def __init__(self, base, key):
        self.origin = urllib.parse.urlsplit(base)[:2]
        self.key = key

    def http_request(self, request):
        if urllib.parse.urlsplit(request.full_url)[:2] == self.origin:
            request.add_unredirected_header("Authorization", "Bearer " + self.key)
        return request

    https_request = http_request


def connect(owner):
    host = owner["host"]
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1" if host == "0.0.0.0" else "::1"
    base = f"http://{'[' + host + ']' if ':' in host else host}:{owner['port']}"
    if owner["authentication"]:
        key = os.environ.get("SPLASH_API_KEY")
        if not key:
            raise RuntimeError("this server requires SPLASH_API_KEY")
        urllib.request.install_opener(urllib.request.build_opener(Authorization(base, key)))
    return base


def request(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def check_live(values, owner, identity):
    if owner["model_identity"] != identity or owner["context"] != int(values["SPLASH_MAX_LEN"]):
        raise RuntimeError("selected model/config differs from the managed launch")
    if owner["pid"] not in owned_group(owner):
        raise RuntimeError("managed Splash server is not running")
    # Identity is the fully hashed assembly verified before launch, served from
    # its immutable resolved path in the launch argv. The native /status
    # hashes describe layout, not content; they are retained as evidence.
    if str(model_path(values).resolve(strict=True)) not in owner["command"]:
        raise RuntimeError("the managed server does not serve the configured assembly")
    base = connect(owner)
    status = request(base + "/status")
    if not status["ready"] or status["maximum_context_tokens"] != owner["context"]:
        raise RuntimeError("live Splash readiness or context does not match the launch")
    if [item["id"] for item in request(base + "/v1/models")["data"]] != [values["SPLASH_MODEL_REPO"]]:
        raise RuntimeError("live served model differs from the config")
    return base, status


def start(tag, values):
    require_stopped()
    require_host()
    argv = command(values)
    host, port = argv[argv.index("--host") + 1], int(argv[argv.index("--port") + 1])
    port_free(host, port)
    release = verify_release()
    print("Verifying all model artifacts before launch...", flush=True)
    identity = verify_model(values)
    STATE.mkdir(parents=True, exist_ok=True)
    with LOG.open("w") as log:
        log.write("starting " + shlex.join(argv) + "\n")
        log.flush()
        process = subprocess.Popen([str(ROOT / "start.sh"), tag], stdin=subprocess.PIPE,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        entry = processes().get(process.pid)
        if entry is None:
            raise RuntimeError(f"Splash launcher exited before registration; see {LOG}")
        owner = {"pid": process.pid, "started": entry["started"],
                 "command": argv, "host": host, "port": port, "release": release,
                 "authentication": bool(os.environ.get("SPLASH_API_KEY")),
                 "context": int(values["SPLASH_MAX_LEN"]), "model_identity": identity}
        save(PIDFILE, owner)
        # The foreground child cannot exec the engine until registration is
        # durable. EOF on a failed parent makes it exit without acquiring GPU.
        process.stdin.write(b"\n")
        process.stdin.close()
        deadline = time.monotonic() + int(os.environ.get("SPLASH_START_TIMEOUT", "600"))
        base = connect(owner)
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Splash exited during startup; see {LOG}")
            try:
                if request(base + "/status").get("ready"):
                    check_live(values, owner, identity)
                    print(f"Ready: {values['SPLASH_MODEL_REPO']} at {base}; PID {process.pid}")
                    return
            except (OSError, ValueError):
                pass
            time.sleep(2)
        raise TimeoutError(f"Splash readiness timeout; see {LOG}")
    except BaseException:
        if not process.stdin.closed:
            process.stdin.close()
        if PIDFILE.exists():
            stop(preserve_log=True, child=process)
        else:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        raise


def stop(preserve_log=False, child=None):
    if not PIDFILE.exists():
        print("Splash is stopped (no managed pidfile); retained any existing log.")
        return
    owner = json.loads(PIDFILE.read_text())
    members = owned_group(owner)
    if members:
        os.killpg(owner["pid"], signal.SIGTERM)
        for attempt in range(90):
            if child:
                child.poll()
            if not group_alive(owner["pid"]):
                break
            if attempt == 60:
                owned_group(owner)
                os.killpg(owner["pid"], signal.SIGKILL)
            time.sleep(0.5)
    if group_alive(owner["pid"]):
        raise RuntimeError("Splash process group did not release its resources; state retained")
    port_free(owner["host"], owner["port"])
    PIDFILE.unlink()
    if members and not preserve_log:
        LOG.unlink(missing_ok=True)
    print(f"Stopped: group {owner['pid']} empty, port {owner['port']} released.")


def status():
    if not PIDFILE.exists():
        print("server:   not running")
        return
    owner = json.loads(PIDFILE.read_text())
    if owner["pid"] not in owned_group(owner):
        raise RuntimeError("managed server is not running; use make splash-stop to inspect teardown")
    live = request(connect(owner) + "/status")
    print(f"server:   running (pid {owner['pid']})")
    print(f"model:    {owner['model_identity']}")
    print(json.dumps({"pid": owner["pid"], "model": owner["model_identity"],
                      "release": owner["release"], "context": live["maximum_context_tokens"],
                      "ready": live["ready"], "memory_plan": live["memory_plan"]}, indent=2))


def main():
    action = sys.argv[1]
    if action == "status":
        status()
        return
    if action == "serve":
        if sys.stdin.isatty() or sys.stdin.buffer.read(1) != b"\n":
            raise RuntimeError("start.sh is internal; use make splash-start")
        owner = json.loads(PIDFILE.read_text())
        if owner["pid"] != os.getpid() or os.getpgrp() != os.getpid():
            raise RuntimeError("foreground child does not own the managed session")
        argv = owner["command"]
        # The release launcher's environment: -P keeps the working directory
        # off sys.path and PYTHONPATH names the release root.
        os.execve(argv[0], argv, {**os.environ, "PYTHONPATH": str(RELEASE),
                                  "PYTHONUNBUFFERED": "1", "TRANSFORMERS_VERBOSITY": "error"})
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / ".lifecycle.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if action == "install":
            install()
        elif action == "stop":
            stop()
        elif action == "pull":
            pull(config(sys.argv[2]))
        elif action == "start":
            start(sys.argv[2], config(sys.argv[2]))
        else:
            raise ValueError("unknown Splash action")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
