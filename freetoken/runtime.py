"""Managed FreeToken lifecycle, model identity and live capacity evidence.

No workload logic lives here. Stdlib only: FreeToken's pinned release wheels
run from a venv of their own, and its `ft serve` is the server.
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
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("FREETOKEN_DATA_DIR", Path(os.environ.get(
    "XDG_DATA_HOME", Path.home() / ".local/share")) / "freetoken"))
STATE = Path(os.environ.get("FREETOKEN_STATE_DIR", Path(os.environ.get(
    "XDG_STATE_HOME", Path.home() / ".local/state")) / "freetoken"))
VERSION = os.environ.get("FREETOKEN_VERSION", "")
VENV = DATA / "venv" / VERSION
FT = VENV / "bin" / "ft"
RECEIPT = VENV / "llm-local-servers.json"
MODELS = DATA / "models"
PIDFILE = STATE / "server.json"
LOG = STATE / "server.log"
RELEASES = "https://github.com/FlashML-org/FreeToken/releases/download"
CONFIG_KEYS = tuple("FREETOKEN_" + name for name in (
    "SERVED_NAME", "MODEL_REPO", "MODEL_REVISION", "MODEL_FILES", "CTX", "PARALLEL", "MOE_STRATEGY",
    "ENGINE_ARGS", "CAP_REASONING", "CAP_TOOLS", "CAP_REASONING_MODE", "CAP_DISABLE_MODE",
    "CAP_SYSTEM_PROMPT", "SAMPLING",
))
# Engine flags a config may set. Everything else the launcher owns: paths,
# bind, context, admission and the MoE strategy, which is its own key.
ENGINE_FLAGS = {"--kv-cache-dtype": r"auto|fp8_per_token_head|int8_per_token_head"}
# fused keeps every expert in VRAM; offload holds them in pinned host RAM
# behind a GPU expert cache. hybrid and cpu compute experts on the CPU.
STRATEGIES = ("fused", "offload")
NAME = r"[a-zA-Z0-9_][a-zA-Z0-9_.-]*"


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
        raise ValueError("MODEL must name a FreeToken model config")
    return Path(os.environ.get("FREETOKEN_MODEL_CONF", ROOT / "models" / (tag + ".conf"))).resolve()


def config(tag):
    path = config_path(tag)
    script = 'set -eu; source "$1"; shift; for name; do printf "%s\\0" "${!name-}"; done'
    output = subprocess.check_output(["bash", "-c", script, "bash", str(path), *CONFIG_KEYS])
    values = dict(zip(CONFIG_KEYS, output.decode().split("\0")[:-1]))
    if not re.fullmatch(NAME, values["FREETOKEN_SERVED_NAME"]):
        raise ValueError("FREETOKEN_SERVED_NAME must be a plain model name")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", values["FREETOKEN_MODEL_REPO"]):
        raise ValueError("FREETOKEN_MODEL_REPO must be a full Hugging Face repository ID")
    if not re.fullmatch(r"[0-9a-f]{40}", values["FREETOKEN_MODEL_REVISION"]):
        raise ValueError("FREETOKEN_MODEL_REVISION must be an immutable commit")
    files = values["FREETOKEN_MODEL_FILES"].split()
    if not files or not all(re.fullmatch(rf"(?:{NAME}/)*{NAME}\.gguf", name) for name in files):
        raise ValueError("FREETOKEN_MODEL_FILES must name the GGUF file(s) in the repository, first shard first")
    if int(values["FREETOKEN_CTX"]) <= 0:
        raise ValueError("FREETOKEN_CTX must be positive")
    if not 1 <= int(values["FREETOKEN_PARALLEL"]) <= 8:
        raise ValueError("FREETOKEN_PARALLEL must be 1..8")
    if values["FREETOKEN_MOE_STRATEGY"] not in STRATEGIES:
        raise ValueError(f"FREETOKEN_MOE_STRATEGY must be one of {STRATEGIES}")
    engine_flags(values)
    return values


def engine_flags(values):
    """FREETOKEN_ENGINE_ARGS: the model's documented engine flags, as pairs."""
    words = values["FREETOKEN_ENGINE_ARGS"].split()
    if len(words) % 2:
        raise ValueError("FREETOKEN_ENGINE_ARGS must be flag/value pairs")
    result = []
    for flag, value in zip(words[::2], words[1::2]):
        if flag not in ENGINE_FLAGS or not re.fullmatch(ENGINE_FLAGS[flag], value):
            raise ValueError(f"FREETOKEN_ENGINE_ARGS entry {flag} {value} is not one of {sorted(ENGINE_FLAGS)}")
        result += [flag, value]
    return result


def require_host():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError(f"FreeToken's release wheels need Linux x86_64 with an NVIDIA GPU; "
                           f"this host is {platform.system()} {platform.machine()}")
    require_tool("nvidia-smi")


def require_stopped():
    if PIDFILE.exists():
        raise RuntimeError(f"managed state exists at {PIDFILE}; run make freetoken-stop first")


def uv():
    """uv, which the host provides; a non-interactive ssh PATH often lacks the
    user install location, so that is tried as well."""
    found = shutil.which("uv") or (str(Path.home() / ".local/bin/uv")
                                   if (Path.home() / ".local/bin/uv").exists() else None)
    if not found:
        raise RuntimeError("uv is required but not on PATH or in ~/.local/bin")
    return found


def require_tool(name):
    if not shutil.which(name):
        raise RuntimeError(f"{name} is required but not on PATH")


def gpu_processes():
    output = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"], text=True)
    return {int(line) for line in output.split()}


def cuda_root():
    """The CUDA 13 toolkit FreeToken's kernels compile with on first use:
    FREETOKEN_CUDA_HOME, the nvcc on PATH, or the standard install location."""
    nvcc = shutil.which("nvcc")
    for candidate in (os.environ.get("FREETOKEN_CUDA_HOME"), nvcc and str(Path(nvcc).resolve().parent.parent),
                      "/usr/local/cuda"):
        if candidate and (Path(candidate) / "bin" / "nvcc").exists():
            root = Path(candidate).resolve()
            release = subprocess.check_output([str(root / "bin" / "nvcc"), "--version"], text=True)
            if not re.search(r"release 13\.", release):
                raise RuntimeError(f"FreeToken needs a CUDA 13 toolkit; {root} is not")
            return root
    raise RuntimeError("a CUDA 13 toolkit (nvcc) is required; set FREETOKEN_CUDA_HOME to its root")


def wheels():
    """The release's two wheels, each pinned by the root Makefile's digest."""
    python = "cp312"
    tag = f"v{VERSION}"
    return [(f"{RELEASES}/{tag}/freetoken-{VERSION}-{python}-{python}-manylinux_2_27_x86_64.whl",
             os.environ.get("FREETOKEN_WHEEL_SHA256", "")),
            (f"{RELEASES}/{tag}/freetoken_kernel_cache-{VERSION}%2Bcu130-py3-none-linux_x86_64.whl",
             os.environ.get("FREETOKEN_KERNEL_CACHE_SHA256", ""))]


def fetch_wheel(url, expected):
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"no SHA-256 pin for {url}")
    target = DATA / "wheels" / urllib.parse.unquote(url.rsplit("/", 1)[1])
    if not target.exists() or digest(target) != expected:
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".partial")
        with urllib.request.urlopen(url, timeout=600) as response, partial.open("wb") as out:
            shutil.copyfileobj(response, out)
        if digest(partial) != expected:
            partial.unlink()
            raise RuntimeError(f"{url} does not match its pinned SHA-256")
        partial.replace(target)
    return target


def verify_install():
    receipt = json.loads(RECEIPT.read_text())
    if receipt.get("version") != VERSION or receipt.get("ft_sha256") != digest(FT):
        raise RuntimeError(f"the FreeToken install differs from {VERSION}; run make freetoken-install")
    return receipt


def install():
    require_stopped()
    require_host()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", VERSION):
        raise ValueError("FREETOKEN_VERSION must be a release version")
    ninja = os.environ.get("FREETOKEN_NINJA_VERSION", "")
    if not re.fullmatch(r"[0-9]+(\.[0-9]+)+", ninja):
        raise ValueError("FREETOKEN_NINJA_VERSION must pin ninja")
    cuda = cuda_root()
    files = [fetch_wheel(url, expected) for url, expected in wheels()]
    if not (VENV / "bin" / "python").exists():
        subprocess.run([uv(), "venv", "--python", "3.12", str(VENV)], check=True)
    # The engine wheel with its accel extras (FlashInfer, sgl-kernel), the
    # prebuilt kernel cache, and ninja: FlashInfer JIT-builds its attention
    # modules at engine start and shells out to it.
    subprocess.run([uv(), "pip", "install", "--python", str(VENV / "bin" / "python"), "--quiet",
                    f"freetoken[accel] @ {files[0].as_uri()}", f"freetoken-kernel-cache @ {files[1].as_uri()}",
                    f"ninja=={ninja}"], check=True)
    freeze = subprocess.check_output([uv(), "pip", "freeze", "--python", str(VENV / "bin" / "python")], text=True)
    save(RECEIPT, {"version": VERSION, "wheels_sha256": [expected for _url, expected in wheels()],
                   "ninja": ninja, "cuda": str(cuda), "ft_sha256": digest(FT),
                   "freeze_sha256": hashlib.sha256(freeze.encode()).hexdigest()})
    verify_install()
    print(f"FreeToken {VERSION} installed in {VENV}; CUDA {cuda}")


def hf_command():
    """A host hf when present, else the client FreeToken's wheel installs."""
    if shutil.which("hf"):
        return ["hf"]
    return [str(VENV / "bin" / "hf")]


def model_dir(values):
    return MODELS / values["FREETOKEN_MODEL_REPO"].replace("/", "--") / values["FREETOKEN_MODEL_REVISION"]


def model_files(values):
    return [model_dir(values) / name for name in values["FREETOKEN_MODEL_FILES"].split()]


def identity_record(values):
    root = model_dir(values)
    return {"source": values["FREETOKEN_MODEL_REPO"], "revision": values["FREETOKEN_MODEL_REVISION"],
            "files": {str(path.relative_to(root)): digest(path) for path in model_files(values)}}


def verify_model(values):
    record = json.loads((model_dir(values) / "llm-local-servers.json").read_text())
    if record != identity_record(values):
        raise RuntimeError("the model files differ from the pulled and verified ones; run make freetoken-pull")
    return {"source": record["source"], "revision": record["revision"],
            "identity_sha256": hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest(),
            "full_artifact_hash_verification": True}


def pull(values):
    require_stopped()
    verify_install()
    root = model_dir(values)
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run([*hf_command(), "download", values["FREETOKEN_MODEL_REPO"],
                    "--revision", values["FREETOKEN_MODEL_REVISION"], "--local-dir", str(root),
                    *[word for name in values["FREETOKEN_MODEL_FILES"].split() for word in ("--include", name)],
                    "--quiet"], check=True, stdout=subprocess.DEVNULL)
    save(root / "llm-local-servers.json", identity_record(values))
    identity = verify_model(values)
    print(f"Verified {identity['source']} at {identity['revision']} in {root}")


def port():
    value = int(os.environ.get("FREETOKEN_PORT", "8027"))
    if not 1 <= value <= 65535:
        raise ValueError("FREETOKEN_PORT must be 1..65535")
    return value


def command(values):
    # Loopback only; remote use goes through an ssh tunnel. The served
    # context is the config's, and every response reports its prefix-cache
    # hits, which the session benchmark reads.
    argv = [str(FT), "serve", "--model", str(model_files(values)[0]),
            "--served-model-name", values["FREETOKEN_SERVED_NAME"],
            "--host", "127.0.0.1", "--port", str(port()),
            "--max-seq-len-override", values["FREETOKEN_CTX"],
            "--max-running-requests", values["FREETOKEN_PARALLEL"],
            "--moe-strategy", values["FREETOKEN_MOE_STRATEGY"], "--enable-cache-report",
            *engine_flags(values)]
    if values["FREETOKEN_MOE_STRATEGY"] == "offload":
        # Offload reserves only 8,192 KV tokens before the expert cache takes
        # the rest of the card; reserve the full context for every admitted
        # request.
        argv += ["--kv-reserve-tokens", str(int(values["FREETOKEN_CTX"]) * int(values["FREETOKEN_PARALLEL"]))]
    return argv


def serve_environment(receipt):
    """The venv's tools (ninja) and the CUDA toolkit first on PATH for the
    kernels FreeToken compiles at start; offline, so nothing is fetched."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("FREETOKEN_")}
    environment["PATH"] = os.pathsep.join([str(VENV / "bin"), str(Path(receipt["cuda"]) / "bin"),
                                           environment.get("PATH", "")])
    environment["HF_HUB_OFFLINE"] = "1"
    return environment


def port_free(number):
    with socket.socket(socket.AF_INET) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", number))


def stat_fields(pid):
    try:
        return (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return None


def started(pid):
    """A live process's start time in clock ticks since boot, from /proc;
    None for a process that is gone or a zombie."""
    fields = stat_fields(pid)
    return None if not fields or fields[0] == "Z" else int(fields[19])


def arguments(pid):
    try:
        return (Path("/proc") / str(pid) / "cmdline").read_bytes().split(b"\0")
    except OSError:
        return []


def group(pgid):
    """Live processes of the managed process group: the server and the
    engine processes it spawns."""
    members = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            fields = stat_fields(int(entry.name))
            if fields and fields[0] != "Z" and int(fields[2]) == pgid:
                members.append(int(entry.name))
    return members


def owned(owner):
    """True while the recorded session leader is alive, is the same process
    (start time) and runs ft, start.sh or runtime.py serve."""
    if type(owner.get("pid")) is not int or owner["pid"] <= 1:
        raise RuntimeError("invalid managed PID")
    tick = started(owner["pid"])
    if tick is None:
        return False
    if tick != owner["started"]:
        raise RuntimeError("managed PID has been reused; refusing to signal it")
    argv = arguments(owner["pid"])
    if not any(os.fsencode(str(path)) in argv for path in (FT, ROOT / "start.sh", ROOT / "runtime.py")):
        raise RuntimeError(f"managed PID {owner['pid']} runs an unrecognized command")
    return True


def post(url, body, timeout=600):
    data = json.dumps(body).encode()
    request = urllib.request.Request(url, data, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def get(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def ready(base, name):
    """/v1/models answers while the model still loads (503 "model is still
    loading" on completions), so readiness is a completed one-token request."""
    try:
        post(f"{base}/v1/chat/completions", {"model": name, "max_tokens": 1,
                                             "messages": [{"role": "user", "content": "hi"}]})
        return True
    except urllib.error.HTTPError as error:
        if error.code == 503:
            return False
        raise


def engine_facts():
    """FreeToken's own report of what it resolved: the MoE strategy and the
    KV pool it allocated."""
    log = LOG.read_text()
    strategy = re.search(r"Resolved config: moe_strategy='([a-z]+)'", log)
    pool = re.search(r"Allocating ([0-9]+) tokens for KV cache", log)
    return {"moe_strategy": strategy and strategy.group(1), "kv_pool_tokens": pool and int(pool.group(1))}


def check_live(values, owner, identity):
    if owner["model_identity"] != identity or owner["command"] != command(values):
        raise RuntimeError("selected model/config differs from the managed launch")
    if not owned(owner):
        raise RuntimeError("managed FreeToken server is not running")
    base = f"http://127.0.0.1:{owner['port']}"
    models = get(f"{base}/v1/models")["data"]
    if [item["id"] for item in models] != [values["FREETOKEN_SERVED_NAME"]]:
        raise RuntimeError("live served model differs from the config")
    if owner["engine"]["moe_strategy"] != values["FREETOKEN_MOE_STRATEGY"]:
        raise RuntimeError(f"FreeToken resolved MoE strategy {owner['engine']['moe_strategy']}, "
                           f"not the config's {values['FREETOKEN_MOE_STRATEGY']}")
    return base


def meminfo():
    fields = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        name, value = line.split(":", 1)
        fields[name] = int(value.split()[0]) * 1024
    return fields


def start(tag, values):
    require_stopped()
    require_host()
    port_free(port())
    busy = gpu_processes()
    if busy:
        raise RuntimeError(f"another GPU compute process is active (pids {sorted(busy)}); refusing to start")
    receipt = verify_install()
    print("Verifying all model artifacts before launch...", flush=True)
    identity = verify_model(values)
    if values["FREETOKEN_MOE_STRATEGY"] == "offload":
        # Offloaded experts sit in pinned host RAM; never start into swap.
        need = sum(path.stat().st_size for path in model_files(values))
        if meminfo()["MemAvailable"] < need + 16 * 1024 ** 3:
            raise RuntimeError("host RAM cannot hold the offloaded experts with 16 GiB to spare")
    STATE.mkdir(parents=True, exist_ok=True)
    argv = command(values)
    with LOG.open("w") as log:
        log.write("starting " + shlex.join(argv) + "\n")
        log.flush()
        process = subprocess.Popen([str(ROOT / "start.sh"), tag], stdin=subprocess.PIPE, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    try:
        tick = started(process.pid)
        if tick is None:
            raise RuntimeError(f"FreeToken launcher exited before registration; see {LOG}")
        owner = {"pid": process.pid, "started": tick, "command": argv, "port": port(),
                 "parallel": int(values["FREETOKEN_PARALLEL"]), "receipt": receipt, "model_identity": identity}
        save(PIDFILE, owner)
        # The foreground child cannot exec the server until registration is
        # durable. EOF on a failed parent makes it exit without the GPU.
        process.stdin.write(b"\n")
        process.stdin.close()
        base = f"http://127.0.0.1:{port()}"
        deadline = time.monotonic() + int(os.environ.get("FREETOKEN_START_TIMEOUT", "1800"))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"FreeToken exited during startup; see {LOG}")
            try:
                if ready(base, values["FREETOKEN_SERVED_NAME"]):
                    owner["engine"] = engine_facts()
                    save(PIDFILE, owner)
                    check_live(values, owner, identity)
                    print(f"Ready: {values['FREETOKEN_SERVED_NAME']} at {base}; PID {process.pid}; "
                          f"MoE {owner['engine']['moe_strategy']}, KV pool {owner['engine']['kv_pool_tokens']} tokens")
                    return
            except (OSError, ValueError):
                pass
            time.sleep(5)
        raise TimeoutError(f"FreeToken readiness timeout; see {LOG}")
    except BaseException:
        if not process.stdin.closed:
            process.stdin.close()
        if PIDFILE.exists():
            stop(preserve_log=True)
        else:
            process.kill()
        process.wait()
        raise


def stop(preserve_log=False):
    if not PIDFILE.exists():
        print("FreeToken is stopped (no managed pidfile); retained any existing log.")
        return
    owner = json.loads(PIDFILE.read_text())
    running = owned(owner)
    # The server's engine processes share its session's process group.
    pgid = owner["pid"]
    members = set(group(pgid))
    if running or members:
        os.killpg(pgid, signal.SIGTERM)
        for attempt in range(120):
            if not group(pgid):
                break
            if attempt == 90:
                os.killpg(pgid, signal.SIGKILL)
            time.sleep(0.5)
    if group(pgid):
        raise RuntimeError(f"FreeToken processes {group(pgid)} did not exit; state retained")
    for _ in range(60):
        if not gpu_processes() & members:
            break
        time.sleep(1)
    else:
        raise RuntimeError("a FreeToken process still holds the GPU; state retained")
    port_free(owner["port"])
    PIDFILE.unlink()
    if not running:
        print(f"FreeToken was not running; removed its pidfile and kept the log in {STATE} as evidence.")
        return
    if not preserve_log:
        LOG.unlink(missing_ok=True)
    print(f"Stopped: process group {pgid} exited, GPU released, port {owner['port']} free.")


def status():
    if not PIDFILE.exists():
        print("server:   not running")
        return
    owner = json.loads(PIDFILE.read_text())
    if not owned(owner):
        raise RuntimeError("managed server is not running; use make freetoken-stop to inspect teardown")
    models = get(f"http://127.0.0.1:{owner['port']}/v1/models")["data"]
    print(f"server:   running (pid {owner['pid']}, port {owner['port']})")
    print(f"model:    {', '.join(item['id'] for item in models)} ({owner['model_identity']['source']})")
    print(json.dumps({"model": owner["model_identity"], "receipt": owner["receipt"],
                      "engine": owner.get("engine"), "slots": owner["parallel"],
                      "processes": group(owner["pid"]), "args": owner["command"][2:]}, indent=2))


def main():
    action = sys.argv[1]
    if action == "status":
        status()
        return
    if action == "serve":
        if sys.stdin.isatty() or sys.stdin.buffer.read(1) != b"\n":
            raise RuntimeError("start.sh is internal; use make freetoken-start")
        owner = json.loads(PIDFILE.read_text())
        if owner["pid"] != os.getpid() or os.getpgrp() != os.getpid():
            raise RuntimeError("foreground child does not own the managed session")
        os.execve(owner["command"][0], owner["command"], serve_environment(owner["receipt"]))
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
            raise ValueError("unknown FreeToken action")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
