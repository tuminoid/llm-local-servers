"""Managed LM Studio lifecycle, pinned engines and model identity.

The LM Studio service owns the engine processes. This module owns only what
it creates: the server when it started it, one loaded model identifier, and
the record of both. No workload logic lives here.
"""

import fcntl
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("LMSTUDIO_STATE_DIR", Path(os.environ.get(
    "XDG_STATE_HOME", Path.home() / ".local/state")) / "lmstudio"))
RECORD = STATE / "server.json"
LOG = STATE / "server.log"
HOME = Path(os.environ.get("LMSTUDIO_HOME", Path.home() / ".lmstudio"))
INTERNAL = HOME / ".internal"
HOST = "127.0.0.1"
PORT = int(os.environ.get("LMSTUDIO_PORT", "1234"))
# Pulled artifacts live under one publisher folder the operator's own
# downloads never use. LM Studio loads by model key only, and renames keys to
# publisher/name@quant when two copies of a model exist, so start resolves
# the key from this path each time and verifies the loaded path.
PUBLISHER = "llm-local-servers"
# Model format -> (engine preference key, format lms reports, pin variable,
# fixed engine lanes). LM Studio ignores --parallel for Splash and runs its
# requests one at a time: four streams took 3.9x the one-stream wall.
FORMATS = {
    "splash": ("splash", "yuzu", "LMSTUDIO_SPLASH_ENGINE_VERSION", 1),
    "mlx": ("safetensors", "safetensors", "LMSTUDIO_MLX_ENGINE_VERSION", None),
}
CONFIG_KEYS = tuple("LMSTUDIO_" + name for name in (
    "FORMAT", "MODEL_REPO", "MODEL_REVISION", "CONTEXT", "EXPECTED_ARCHITECTURE",
    "EXPECTED_QUANTIZATION", "BENCH_TOLERATE_OFF_BY_ONE", "CAP_REASONING",
    "CAP_TOOLS", "CAP_REASONING_MODE", "CAP_DISABLE_MODE", "CAP_SYSTEM_PROMPT",
))


def config_path(tag):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", tag):
        raise ValueError("MODEL must name an LM Studio model config")
    return ROOT / "models" / (tag + ".conf")


def config(tag):
    script = 'set -eu; source "$1"; shift; for name; do printf "%s\\0" "${!name}"; done'
    output = subprocess.check_output(
        ["bash", "-c", script, "bash", str(config_path(tag)), *CONFIG_KEYS])
    values = dict(zip(CONFIG_KEYS, output.decode().split("\0")[:-1]))
    if values["LMSTUDIO_FORMAT"] not in FORMATS:
        raise ValueError(f"LMSTUDIO_FORMAT must be one of {', '.join(FORMATS)}")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", values["LMSTUDIO_MODEL_REPO"]):
        raise ValueError("LMSTUDIO_MODEL_REPO must be a Hugging Face repository ID")
    if not re.fullmatch(r"[0-9a-f]{40}", values["LMSTUDIO_MODEL_REVISION"]):
        raise ValueError("LMSTUDIO_MODEL_REVISION must be an immutable commit")
    if int(values["LMSTUDIO_CONTEXT"]) <= 0:
        raise ValueError("LMSTUDIO_CONTEXT must be positive")
    return values


def lms_exe():
    return os.environ.get("LMSTUDIO_BIN") or shutil.which("lms") or str(HOME / "bin/lms")


def lms(*args, check=True):
    exe = lms_exe()
    if not os.access(exe, os.X_OK):
        raise RuntimeError("the lms CLI was not found; run LM Studio once, or set LMSTUDIO_BIN")
    done = subprocess.run([exe, *args], capture_output=True, text=True, timeout=900)
    if check and done.returncode:
        raise RuntimeError(f"lms {' '.join(args)} failed: {(done.stderr or done.stdout).strip()[-500:]}")
    return done


def internal(name):
    return json.loads((INTERNAL / name).read_text())


def pin(name):
    if not os.environ.get(name):
        raise RuntimeError(f"{name} is unset; run through the root Makefile targets")
    return os.environ[name]


def app_version():
    for target in internal("historical-version-info.json")["targetHistories"]:
        if target["target"] == "lmstudio":
            return f"{target['lastRecordedAppVersion']}+{target['lastRecordedAppBuildVersion']}"
    raise RuntimeError("LM Studio app version not recorded; run the app once")


def engine(fmt):
    """The engine LM Studio selects for a format, as name@version."""
    selected = [item for item in internal("backend-preferences-v1.json")
                if item["model_format"] == FORMATS[fmt][0]]
    if not selected:
        raise RuntimeError(f"no LM Studio engine selected for {fmt}; run lms runtime get")
    return f"{selected[0]['name']}@{selected[0]['version']}"


def verify_install():
    engines = {fmt: engine(fmt) for fmt in FORMATS if host_supports(fmt)}
    if not shutil.which("hf"):
        raise RuntimeError("the hf CLI is required for pinned pulls")
    return engines


def pin_drift(app, engines):
    """Differences from the measured release. The operator owns LM Studio and
    it updates itself, so serving accepts drift; bench and capability do not."""
    drift = [] if app == pin("LMSTUDIO_VERSION") else [
        f"LM Studio {app}, pinned LMSTUDIO_VERSION={pin('LMSTUDIO_VERSION')}"]
    for fmt, selected in engines.items():
        variable = FORMATS[fmt][2]
        if selected.rpartition("@")[2] != pin(variable):
            drift.append(f"{selected}, pinned {variable}={pin(variable)}")
    return drift


def host_supports(fmt):
    # Both current formats are Apple-Silicon engines; LM Studio itself refuses
    # Splash below GPU family 9 or macOS 26.4 at load.
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def models_root():
    settings = HOME / "settings.json"
    folder = json.loads(settings.read_text()).get("downloadsFolder") if settings.is_file() else None
    return Path(os.environ.get("LMSTUDIO_MODELS_DIR") or folder or HOME / "models")


def model_path(tag):
    return models_root() / PUBLISHER / tag


def verify_model(tag, values):
    """Every pulled file must carry Hugging Face metadata naming the pin."""
    path = model_path(tag)
    metadata = path / ".cache/huggingface/download"
    files = [item for item in path.rglob("*")
             if item.is_file() and ".cache" not in item.relative_to(path).parts]
    if not files:
        raise RuntimeError(f"{path} holds no model; run make lmstudio-pull MODEL={tag}")
    for item in files:
        record = metadata / item.relative_to(path).parent / f"{item.name}.metadata"
        if not record.is_file() or record.read_text().split("\n")[0] != values["LMSTUDIO_MODEL_REVISION"]:
            raise RuntimeError(f"{item} is not verified at the pinned revision; run make lmstudio-pull")
    return {"source": values["LMSTUDIO_MODEL_REPO"], "revision": values["LMSTUDIO_MODEL_REVISION"],
            "resolved_path": str(path), "verified_files": len(files)}


def pull(tag, values):
    path = model_path(tag)
    repo, revision = values["LMSTUDIO_MODEL_REPO"], values["LMSTUDIO_MODEL_REVISION"]
    snapshot = Path(os.environ.get("HF_HUB_CACHE", Path.home() / ".cache/huggingface/hub")) / (
        "models--" + repo.replace("/", "--")) / "snapshots" / revision
    if not path.exists() and snapshot.is_dir() and platform.system() == "Darwin":
        # LM Studio does not follow symlinks; an APFS clone of the cached
        # snapshot costs no space. hf download below hashes every file
        # against the pinned revision before recording it.
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-cRL", str(snapshot), str(path)], check=True)
    subprocess.run(["hf", "download", repo, "--revision", revision, "--local-dir", str(path)],
                   check=True)
    print(json.dumps(verify_model(tag, values), indent=2))


def model_key(tag):
    path = f"{PUBLISHER}/{tag}"
    keys = [item["modelKey"] for item in json.loads(lms("ls", "--json").stdout)
            if item["path"] == path]
    if len(keys) != 1:
        raise RuntimeError(f"LM Studio does not list {path}; run make lmstudio-pull MODEL={tag}")
    return keys[0]


def loaded():
    return json.loads(lms("ps", "--json").stdout)


def server():
    return json.loads(lms("server", "status", "--json", "--quiet").stdout)


def port_answers():
    with socket.socket() as probe:
        probe.settimeout(1)
        return probe.connect_ex((HOST, PORT)) == 0


def log(*lines):
    with LOG.open("a") as sink:
        sink.write("".join(line if line.endswith("\n") else line + "\n" for line in lines))


def check_live(tag, values, owner):
    """The owned identifier must be loaded exactly as the record says."""
    fmt = values["LMSTUDIO_FORMAT"]
    entries = [item for item in loaded() if item["identifier"] == owner["identifier"]]
    if len(entries) != 1:
        raise RuntimeError(f"{owner['identifier']} is not loaded in LM Studio")
    entry = entries[0]
    quantization = (entry.get("quantization") or {}).get("name")
    expected = {"path": f"{PUBLISHER}/{tag}", "format": FORMATS[fmt][1],
                "contextLength": int(values["LMSTUDIO_CONTEXT"]),
                "architecture": values["LMSTUDIO_EXPECTED_ARCHITECTURE"]}
    actual = {key: entry.get(key) for key in expected}
    if FORMATS[fmt][3] is None:
        expected["parallel"], actual["parallel"] = owner["parallel"], entry.get("parallel")
    expected["quantization"], actual["quantization"] = values["LMSTUDIO_EXPECTED_QUANTIZATION"], quantization
    if actual != expected:
        raise RuntimeError(f"loaded model differs from the record: {actual} != {expected}")
    base = f"http://{HOST}:{PORT}"
    with urllib.request.urlopen(f"{base}/v1/models", timeout=10) as response:
        served = {card["id"] for card in json.load(response)["data"]}
    if owner["identifier"] not in served:
        raise RuntimeError(f"{owner['identifier']} is not served at {base}/v1/models")
    return base, entry


def reuse_server(tag):
    """True when the operator's LM Studio server is already up on PORT.

    The operator's own loads and server stay theirs: start coexists with them
    and stop leaves them. Only the identifier and a server started here are
    owned."""
    if RECORD.exists():
        raise RuntimeError(f"managed state exists at {RECORD}; run make lmstudio-stop first")
    if any(item["identifier"] == tag for item in loaded()):
        raise RuntimeError(f"LM Studio already holds a model named {tag}; unload it first")
    running = server()
    if running["running"] and running["port"] != PORT:
        raise RuntimeError(f"LM Studio's server listens on port {running['port']}; "
                           f"set LMSTUDIO_PORT={running['port']}")
    if not running["running"] and port_answers():
        raise RuntimeError(f"port {PORT} is in use by another process")
    return running["running"]


def start(tag, values):
    fmt = values["LMSTUDIO_FORMAT"]
    if not host_supports(fmt):
        raise RuntimeError(f"{fmt} needs macOS on Apple Silicon")
    engines = verify_install()
    identity = verify_model(tag, values)
    link = json.loads(lms("link", "status", "--json").stdout)
    preferred = link.get("preferredDeviceIdentifier")
    if preferred and preferred != link.get("deviceIdentifier"):
        raise RuntimeError("LM Link routes loads to another device; make this device preferred")
    reused = reuse_server(tag)
    lanes = FORMATS[fmt][3]
    parallel = lanes or int(os.environ.get("LMSTUDIO_PARALLEL", "4"))
    owner = {"identifier": tag, "port": PORT, "context": int(values["LMSTUDIO_CONTEXT"]),
             "parallel": parallel, "format": fmt, "app": app_version(), "engine": engines[fmt],
             "started_server": not reused, "started": time.time()}
    STATE.mkdir(parents=True, exist_ok=True)
    LOG.write_text("")
    RECORD.write_text(json.dumps(owner, indent=2) + "\n")
    command = ["load", model_key(tag), "--context-length", str(owner["context"]),
               "--gpu", "max", "--identifier", tag, "--yes"]
    if lanes is None:
        command += ["--parallel", str(parallel)]
    log(f"config: model={tag} format={fmt} path={identity['resolved_path']} "
        f"revision={identity['revision']} context={owner['context']}",
        f"host: lmstudio {owner['app']}, engine {owner['engine']}, bind {HOST}:{PORT}, "
        f"parallel {parallel}", "launch: lms " + " ".join(command))
    try:
        if not reused:
            log(lms("server", "start", "--port", str(PORT), "--bind", HOST).stdout)
        http = internal("http-server-config.json")
        exposed = http["networkInterface"] != HOST or http["cors"]
        if exposed and not reused:
            raise RuntimeError(f"server is not loopback-only without CORS: {http}")
        output = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", lms(*command).stdout).replace("\r", "\n")
        log(*(line for line in output.splitlines() if line.strip() and "Loading" not in line))
        base, entry = check_live(tag, values, owner)
    except Exception:
        stop(preserve_log=True)
        raise
    print(f"ready: {tag} ({entry['path']}, {owner['engine']}) at {base}/v1")
    drift = pin_drift(owner["app"], {fmt: owner["engine"]})
    if drift:
        print(f"note: {'; '.join(drift)}; bench and capability need the pinned release")
    if reused:
        exposure = ", which is not loopback-only without CORS" if exposed else ""
        print(f"note: serving on LM Studio's running server{exposure}; stop leaves it running")


def stop(preserve_log=False):
    if not RECORD.exists():
        print("not running (no managed record); nothing of LM Studio touched")
        return
    owner = json.loads(RECORD.read_text())
    if any(item["identifier"] == owner["identifier"] for item in loaded()):
        lms("unload", owner["identifier"])
    if any(item["identifier"] == owner["identifier"] for item in loaded()):
        raise RuntimeError(f"{owner['identifier']} is still loaded; state retained")
    if owner.get("started_server", True):
        lms("server", "stop", check=False)
        for _ in range(30):
            if not server()["running"] and not port_answers():
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"the LM Studio server still answers on port {PORT}; state retained")
    RECORD.unlink()
    if not preserve_log:
        LOG.unlink(missing_ok=True)
    released = (f"server on port {PORT} released" if owner.get("started_server", True)
                else "LM Studio's own server left running")
    print(f"stopped: {owner['identifier']} unloaded, {released}")


def status():
    if not os.access(lms_exe(), os.X_OK):
        print("server:   not installed")
        return
    owner = json.loads(RECORD.read_text()) if RECORD.exists() else None
    entries = [{key: item.get(key) for key in (
        "identifier", "path", "format", "contextLength", "parallel", "sizeBytes")}
        for item in loaded()]
    live = server()
    print(f"server:   running (port {live.get('port')})" if live.get("running")
          else "server:   not running")
    for entry in entries:
        print(f"model:    {entry['identifier']}")
    print(json.dumps({"record": owner, "server": live, "loaded": entries}, indent=2))


def main():
    action = sys.argv[1]
    if action == "status":
        status()
        return
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / ".lifecycle.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("another lmstudio install, pull, start or stop is running") from None
        if action == "install":
            app, engines = app_version(), verify_install()
            print(json.dumps({"lmstudio": app, "engines": engines,
                              "drift": pin_drift(app, engines)}, indent=2))
        elif action == "pull":
            pull(sys.argv[2], config(sys.argv[2]))
        elif action == "start":
            start(sys.argv[2], config(sys.argv[2]))
        elif action == "stop":
            stop()
        else:
            raise ValueError("unknown LM Studio action")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
