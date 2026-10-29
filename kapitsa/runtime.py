"""Managed Kapitsa lifecycle, model identity and live capacity evidence.

No workload logic lives here. Stdlib only: the release is one native binary,
and the model converters run from the pinned source tree.
"""

import fcntl
import hashlib
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
import urllib.request

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("KAPITSA_DATA_DIR", Path(os.environ.get(
    "XDG_DATA_HOME", Path.home() / ".local/share")) / "kapitsa"))
STATE = Path(os.environ.get("KAPITSA_STATE_DIR", Path(os.environ.get(
    "XDG_STATE_HOME", Path.home() / ".local/state")) / "kapitsa"))
VERSION = os.environ.get("KAPITSA_VERSION", "")
COMMIT = os.environ.get("KAPITSA_SOURCE_COMMIT", "")
RELEASE = DATA / "runtime" / VERSION
BINARY = RELEASE / "kapitsa"
SOURCE = DATA / "source" / COMMIT
# The engine's own home (KAPITSA_HOME): its model store, converter work
# folder and saved state stay inside the managed tree.
ENGINE_HOME = DATA / "home"
MODELS = ENGINE_HOME / "models"
PIDFILE = STATE / "server.json"
LOG = STATE / "server.log"
REPOSITORY = "https://github.com/nace-ai/kapitsa"
HF_HUB = "huggingface_hub[hf_xet]==1.25.1"
CONFIG_KEYS = tuple("KAPITSA_" + name for name in (
    "SERVED_NAME", "MODEL_REPO", "MODEL_REVISION", "CONVERTER", "MAX_POSITIONS", "CTX", "ENGINE_ENV", "GENERATION", "CAP_REASONING", "CAP_TOOLS", "CAP_REASONING_MODE",
    "CAP_DISABLE_MODE", "CAP_SYSTEM_PROMPT", "SAMPLING",
))
CONVERTERS = {"convert_clover.py"}


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
        raise ValueError("MODEL must name a Kapitsa model config")
    return Path(os.environ.get("KAPITSA_MODEL_CONF", ROOT / "models" / (tag + ".conf"))).resolve()


def config(tag):
    path = config_path(tag)
    script = 'set -eu; source "$1"; shift; for name; do printf "%s\\0" "${!name}"; done'
    output = subprocess.check_output(["bash", "-c", script, "bash", str(path), *CONFIG_KEYS])
    values = dict(zip(CONFIG_KEYS, output.decode().split("\0")[:-1]))
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", values["KAPITSA_MODEL_REPO"]):
        raise ValueError("KAPITSA_MODEL_REPO must be a full Hugging Face repository ID")
    if not re.fullmatch(r"[0-9a-f]{40}", values["KAPITSA_MODEL_REVISION"]):
        raise ValueError("KAPITSA_MODEL_REVISION must be an immutable commit")
    if values["KAPITSA_CONVERTER"] not in CONVERTERS:
        raise ValueError(f"KAPITSA_CONVERTER must be one of {sorted(CONVERTERS)}")
    engine_env(values)
    generation(values)
    if int(values["KAPITSA_CTX"]) <= 0:
        raise ValueError("KAPITSA_CTX must be positive")
    if values["KAPITSA_MAX_POSITIONS"] and int(values["KAPITSA_MAX_POSITIONS"]) < int(values["KAPITSA_CTX"]):
        raise ValueError("KAPITSA_MAX_POSITIONS must cover KAPITSA_CTX")
    return values


def engine_env(values):
    """KAPITSA_ENGINE_ENV: the model's documented NI_* decode switches."""
    result = {}
    for word in values["KAPITSA_ENGINE_ENV"].split():
        match = re.fullmatch(r"(NI_[A-Z0-9_]+)=([a-zA-Z0-9_.-]+)", word)
        if not match:
            raise ValueError(f"KAPITSA_ENGINE_ENV entry {word!r} is not NI_<NAME>=<value>")
        result[match.group(1)] = match.group(2)
    return result


def generation(values):
    """KAPITSA_GENERATION: overrides of the pack's generation_config.json."""
    result = {}
    for word in values["KAPITSA_GENERATION"].split():
        match = re.fullmatch(r"([a-z][a-z0-9_]*)=(-?[0-9]+(?:\.[0-9]+)?)", word)
        if not match:
            raise ValueError(f"KAPITSA_GENERATION entry {word!r} is not <key>=<number>")
        result[match.group(1)] = json.loads(match.group(2))
    return result


def require_host():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("Kapitsa requires Apple Silicon and macOS 14+; "
                           f"this host is {platform.system()}/{platform.machine()}")


def require_stopped():
    if PIDFILE.exists():
        raise RuntimeError(f"managed state exists at {PIDFILE}; run make kapitsa-stop first")


def require_tool(name):
    if not shutil.which(name):
        raise RuntimeError(f"{name} is required but not on PATH")


def verify_release():
    receipt = json.loads((RELEASE / "installation.json").read_text())
    if receipt["archive_sha256"] != os.environ["KAPITSA_ARCHIVE_SHA256"]:
        raise RuntimeError("installed runtime does not match the release pin; run make kapitsa-install")
    if digest(BINARY) != receipt["binary_sha256"]:
        raise RuntimeError("runtime checksum mismatch: kapitsa")
    version = subprocess.check_output([str(BINARY), "--version"], text=True,
                                      env=engine_environment({})).split()
    if version[:2] != ["kapitsa", VERSION]:
        raise RuntimeError(f"installed binary reports {' '.join(version)}, the pin is {VERSION}")
    return receipt


def verify_source():
    head = subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
    if head != COMMIT:
        raise RuntimeError(f"{SOURCE} is at {head}, the pin is {COMMIT}; run make kapitsa-install")
    if subprocess.check_output(["git", "-C", str(SOURCE), "status", "--porcelain"], text=True):
        raise RuntimeError(f"{SOURCE} has local changes; run make kapitsa-install after removing it")


def install():
    require_stopped()
    require_host()
    require_tool("git")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", VERSION):
        raise ValueError("KAPITSA_VERSION must be a release version")
    checksum = os.environ.get("KAPITSA_ARCHIVE_SHA256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("KAPITSA_ARCHIVE_SHA256 must pin the release archive")
    if not re.fullmatch(r"[0-9a-f]{40}", COMMIT):
        raise ValueError("KAPITSA_SOURCE_COMMIT must pin the release's commit")
    if not RELEASE.exists():
        RELEASE.parent.mkdir(parents=True, exist_ok=True)
        name = f"kapitsa-{VERSION}-darwin-arm64"
        url = f"{REPOSITORY}/releases/download/v{VERSION}/{name}.tar.gz"
        archive = RELEASE.parent / f"{name}.tar.gz"
        print(f"Downloading {url}", flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        if digest(archive) != checksum:
            raise RuntimeError(f"release archive checksum mismatch; retained {archive}")
        # Extract only the checksum-verified archive. Keep failed staging
        # directories for diagnosis; never replace an installed tree.
        stage = Path(tempfile.mkdtemp(prefix=".install-", dir=RELEASE.parent))
        subprocess.run(["tar", "-xzf", str(archive), "-C", str(stage)], check=True)
        extracted = stage / name
        save(extracted / "installation.json", {
            "archive_sha256": checksum, "archive_url": url,
            "binary_sha256": digest(extracted / "kapitsa")})
        extracted.rename(RELEASE)
        stage.rmdir()
        archive.unlink()
    release = verify_release()
    # The release ships the engine only; model converters live in the
    # source tree of the same release commit.
    if not SOURCE.exists():
        SOURCE.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".source-", dir=SOURCE.parent))
        for argv in (["init", "-q"], ["remote", "add", "origin", REPOSITORY + ".git"],
                     ["fetch", "-q", "--depth", "1", "origin", COMMIT],
                     ["-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD"]):
            subprocess.run(["git", "-C", str(stage), *argv], check=True)
        stage.rename(SOURCE)
    verify_source()
    print(f"Kapitsa {VERSION} at {RELEASE} (archive {release['archive_sha256']}), "
          f"source {COMMIT} at {SOURCE}")


def hf_command():
    """A host hf when present, else the pinned Hugging Face client through uv."""
    if shutil.which("hf"):
        return ["hf"]
    return ["uv", "tool", "run", "--from", HF_HUB, "hf"]


def pack_dir(tag):
    return MODELS / tag


def serve_dir(tag, values):
    """The folder the server reads: the pack, or for a positions or generation
    override a view of it whose config.json or generation_config.json states
    the override (Kapitsa clamps the context to max_position_embeddings)."""
    if values["KAPITSA_MAX_POSITIONS"] or values["KAPITSA_GENERATION"]:
        return MODELS / f"{tag}-view"
    return pack_dir(tag)


def view_files(tag, values):
    """The view's own files: the pack's, with the config's overrides."""
    pack = pack_dir(tag)
    model_config = json.loads((pack / "config.json").read_text())
    if values["KAPITSA_MAX_POSITIONS"]:
        model_config["max_position_embeddings"] = int(values["KAPITSA_MAX_POSITIONS"])
    controls = json.loads((pack / "generation_config.json").read_text())
    for key, value in generation(values).items():
        if key not in controls:
            raise ValueError(f"KAPITSA_GENERATION key {key} is not in the pack's generation_config.json")
        controls[key] = value
    return {"config.json": model_config, "generation_config.json": controls}


def write_view(tag, values):
    pack, view = pack_dir(tag), serve_dir(tag, values)
    files = view_files(tag, values)
    stage = Path(tempfile.mkdtemp(prefix=".view-", dir=MODELS))
    for entry in sorted(pack.iterdir()):
        if entry.name not in files:
            (stage / entry.name).symlink_to(entry)
    for name, value in files.items():
        (stage / name).write_text(json.dumps(value, indent=2) + "\n")
    if view.exists():
        shutil.rmtree(view)
    stage.rename(view)


def verify_model(tag, values):
    pack = pack_dir(tag)
    record = json.loads((pack / "llm-local-servers.json").read_text())
    expected = {"source": values["KAPITSA_MODEL_REPO"], "revision": values["KAPITSA_MODEL_REVISION"],
                "converter": values["KAPITSA_CONVERTER"], "converter_commit": COMMIT}
    if {key: record.get(key) for key in expected} != expected:
        raise RuntimeError("the converted pack differs from the config; run make kapitsa-pull")
    conversion = json.loads((pack / "conversion.json").read_text())
    for name, entry in conversion["files"].items():
        if digest(pack / name) != entry["sha256"]:
            raise RuntimeError(f"converted pack checksum mismatch: {name}; run make kapitsa-pull")
    identity = {**expected, "recipe": conversion["recipe"],
                "conversion_sha256": digest(pack / "conversion.json")}
    view = serve_dir(tag, values)
    if view != pack:
        files = view_files(tag, values)
        if any(json.loads((view / name).read_text()) != value for name, value in files.items()) or any(
                (view / entry.name).resolve() != entry.resolve()
                for entry in pack.iterdir() if entry.name not in files):
            raise RuntimeError("the serving view differs from the pack and config")
        identity["max_position_embeddings"] = files["config.json"]["max_position_embeddings"]
        identity["generation_overrides"] = generation(values)
    return {**identity, "full_artifact_hash_verification": True}


def pull(tag, values):
    require_stopped()
    verify_release()
    verify_source()
    require_tool("c++")
    MODELS.mkdir(parents=True, exist_ok=True)
    # The source checkpoint is only the converter's input: download it into
    # the managed tree, not the Hugging Face cache, and drop it once the pack
    # verifies. A failed pull keeps it, so a rerun resumes the download.
    source = DATA / "work" / f"{tag}-{values['KAPITSA_MODEL_REVISION']}"
    subprocess.run([*hf_command(), "download", values["KAPITSA_MODEL_REPO"],
                    "--revision", values["KAPITSA_MODEL_REVISION"], "--local-dir", str(source),
                    "--quiet"], check=True, stdout=subprocess.DEVNULL)
    pack = pack_dir(tag)
    if pack.exists():
        shutil.rmtree(pack)
    subprocess.run([sys.executable, "-I", str(SOURCE / "tools" / values["KAPITSA_CONVERTER"]),
                    str(source), str(pack)], check=True, env=engine_environment({}))
    save(pack / "llm-local-servers.json", {
        "source": values["KAPITSA_MODEL_REPO"], "revision": values["KAPITSA_MODEL_REVISION"],
        "converter": values["KAPITSA_CONVERTER"], "converter_commit": COMMIT})
    if serve_dir(tag, values) != pack:
        write_view(tag, values)
    identity = verify_model(tag, values)
    shutil.rmtree(source)
    print(f"Verified {identity['source']} at {identity['revision']} in {serve_dir(tag, values)}")


def engine_environment(values):
    """The engine's environment: its own home, no self-update, and the model's
    decode switches."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("NI_")}
    return {**environment, "KAPITSA_HOME": str(ENGINE_HOME), "KAPITSA_NO_AUTO_UPDATE": "1",
            **(engine_env(values) if values else {})}


def command(tag, values):
    port = int(os.environ.get("KAPITSA_PORT", "8024"))
    if not 1 <= port <= 65535:
        raise ValueError("KAPITSA_PORT must be 1..65535")
    # --private: loopback only and out of Bonjour; Kapitsa's own default is
    # 0.0.0.0 with no authentication. Remote use goes through an ssh tunnel.
    return [str(BINARY), "serve", "--model", str(serve_dir(tag, values)), "--model-id", values["KAPITSA_SERVED_NAME"],
            "--private", "--port", str(port), "--context", values["KAPITSA_CTX"],
            "--disk-cache", os.environ.get("KAPITSA_DISK_CACHE", "0")]


def port_free(port):
    with socket.socket(socket.AF_INET) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))


def processes():
    output = subprocess.check_output(["ps", "-axo", "pid=,pgid=,stat=,lstart=,args="], text=True)
    result = {}
    for line in output.splitlines():
        parts = line.split(None, 8)
        if len(parts) == 9:
            result[int(parts[0])] = {"group": int(parts[1]), "state": parts[2],
                                    "started": " ".join(parts[3:8]), "command": parts[8]}
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
    allowed = (str(BINARY), str(ROOT / "start.sh"), str(ROOT / "runtime.py"))
    if any(not member["state"].startswith("Z") and not any(path in member["command"] for path in allowed)
           for member in members.values()):
        raise RuntimeError("managed process group contains an unrecognized process")
    return members


def group_alive(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # macOS can reject signals while a native process is exiting; the
        # group still exists.
        return True
    return True


def request(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def live_model(owner):
    """The served model's /v1/models entry: Kapitsa lists its whole catalog,
    the served model is the one entry marked active."""
    active = [item for item in request(f"http://127.0.0.1:{owner['port']}/v1/models")["data"]
              if item.get("active")]
    if len(active) != 1:
        raise RuntimeError("live Kapitsa does not report exactly one active model")
    return active[0]


def kv_room():
    """The KV room the engine planned at load, in tokens, from its launch log."""
    match = re.search(r"KV room [0-9.]+ GB = ([0-9]+) tokens", LOG.read_text())
    if not match:
        raise RuntimeError(f"no KV room line in {LOG}")
    return int(match.group(1))


def check_live(tag, values, owner, identity):
    if owner["model_identity"] != identity or owner["command"] != command(tag, values):
        raise RuntimeError("selected model/config differs from the managed launch")
    if owner["pid"] not in owned_group(owner):
        raise RuntimeError("managed Kapitsa server is not running")
    entry = live_model(owner)
    if entry["id"] != values["KAPITSA_SERVED_NAME"] or entry["context_length"] != int(values["KAPITSA_CTX"]):
        raise RuntimeError("live served model or context differs from the config")
    return f"http://127.0.0.1:{owner['port']}", entry


def start(tag, values):
    require_stopped()
    require_host()
    argv = command(tag, values)
    port = int(argv[argv.index("--port") + 1])
    port_free(port)
    release = verify_release()
    # The view is derived from the pack and the config, so a changed
    # override takes effect at the next start without a pull.
    if serve_dir(tag, values) != pack_dir(tag):
        write_view(tag, values)
    print("Verifying all model artifacts before launch...", flush=True)
    identity = verify_model(tag, values)
    STATE.mkdir(parents=True, exist_ok=True)
    with LOG.open("w") as log:
        log.write("starting " + shlex.join(argv) + "\n")
        log.flush()
        process = subprocess.Popen([str(ROOT / "start.sh"), tag], stdin=subprocess.PIPE,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        entry = processes().get(process.pid)
        if entry is None:
            raise RuntimeError(f"Kapitsa launcher exited before registration; see {LOG}")
        owner = {"pid": process.pid, "started": entry["started"], "command": argv, "port": port,
                 "engine_env": engine_env(values), "release": release, "model_identity": identity}
        save(PIDFILE, owner)
        # The foreground child cannot exec the engine until registration is
        # durable. EOF on a failed parent makes it exit without the GPU.
        process.stdin.write(b"\n")
        process.stdin.close()
        deadline = time.monotonic() + int(os.environ.get("KAPITSA_START_TIMEOUT", "600"))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Kapitsa exited during startup; see {LOG}")
            try:
                if request(f"http://127.0.0.1:{port}/health").get("status") == "ok":
                    base, _entry = check_live(tag, values, owner, identity)
                    print(f"Ready: {values['KAPITSA_SERVED_NAME']} at {base}; PID {process.pid}")
                    return
            except (OSError, ValueError):
                pass
            time.sleep(2)
        raise TimeoutError(f"Kapitsa readiness timeout; see {LOG}")
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
        print("Kapitsa is stopped (no managed pidfile); retained any existing log.")
        return
    owner = json.loads(PIDFILE.read_text())
    members = owned_group(owner)
    if members:
        os.killpg(owner["pid"], signal.SIGTERM)
        for attempt in range(120):
            if child:
                child.poll()
            if not group_alive(owner["pid"]):
                break
            if attempt == 90:
                owned_group(owner)
                os.killpg(owner["pid"], signal.SIGKILL)
            time.sleep(0.5)
    if group_alive(owner["pid"]):
        raise RuntimeError("Kapitsa process group did not release its resources; state retained")
    port_free(owner["port"])
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
        raise RuntimeError("managed server is not running; use make kapitsa-stop to inspect teardown")
    entry = live_model(owner)
    print(f"server:   running (pid {owner['pid']}, port {owner['port']})")
    print(f"model:    {entry['id']} ({owner['model_identity']['source']})")
    print(json.dumps({"pid": owner["pid"], "model": owner["model_identity"], "release": owner["release"],
                      "context": entry["context_length"], "slots": entry["slots"],
                      "engine_env": owner["engine_env"]}, indent=2))


def main():
    action = sys.argv[1]
    if action == "status":
        status()
        return
    if action == "serve":
        if sys.stdin.isatty() or sys.stdin.buffer.read(1) != b"\n":
            raise RuntimeError("start.sh is internal; use make kapitsa-start")
        owner = json.loads(PIDFILE.read_text())
        if owner["pid"] != os.getpid() or os.getpgrp() != os.getpid():
            raise RuntimeError("foreground child does not own the managed session")
        environment = engine_environment({})
        os.execve(owner["command"][0], owner["command"], {**environment, **owner["engine_env"]})
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / ".lifecycle.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if action == "install":
            install()
        elif action == "stop":
            stop()
        elif action == "pull":
            pull(sys.argv[2], config(sys.argv[2]))
        elif action == "start":
            start(sys.argv[2], config(sys.argv[2]))
        else:
            raise ValueError("unknown Kapitsa action")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
