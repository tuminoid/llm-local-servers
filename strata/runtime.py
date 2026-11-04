"""Managed Strata lifecycle, model identity and live capacity evidence.

No workload logic lives here. Stdlib only: the engine is built from the
pinned source on the host that serves it, and Strata's Python server and
model tools run from that tree's own venv.
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
DATA = Path(os.environ.get("STRATA_DATA_DIR", Path(os.environ.get(
    "XDG_DATA_HOME", Path.home() / ".local/share")) / "strata"))
STATE = Path(os.environ.get("STRATA_STATE_DIR", Path(os.environ.get(
    "XDG_STATE_HOME", Path.home() / ".local/state")) / "strata"))
VERSION = os.environ.get("STRATA_VERSION", "")
COMMIT = os.environ.get("STRATA_COMMIT", "")
SOURCE = DATA / "source" / COMMIT
ENGINE = SOURCE / "build" / "strata"
PYTHON = SOURCE / ".venv" / "bin" / "python"
RECEIPT = SOURCE / "llm-local-servers.json"
MODELS = DATA / "models"
PIDFILE = STATE / "server.json"
LOG = STATE / "server.log"
ENGINE_LOG = STATE / "engine.log"
RUN_CONFIG = STATE / "run.json"
REPOSITORY = "https://github.com/Niko1221/Strata"
LLAMA_REPOSITORY = "https://github.com/ggml-org/llama.cpp"
HF_HUB = "huggingface_hub[hf_xet]==" + os.environ.get("HF_HUB_VERSION", "1.33.0")
CONFIG_KEYS = tuple("STRATA_" + name for name in (
    "SERVED_NAME", "MODEL_REPO", "MODEL_REVISION", "PACK", "DENSE_GGUF", "PLE_GGUF", "EMBD_GGUF",
    "CTX", "PARALLEL", "ENGINE_ARGS", "CAP_REASONING", "CAP_TOOLS", "CAP_REASONING_MODE",
    "CAP_DISABLE_MODE", "CAP_SYSTEM_PROMPT", "SAMPLING",
))
# Engine flags a config may set. Everything else the launcher owns: paths,
# context, slots, and the host-derived memory placement.
ENGINE_FLAGS = {"--spec": r"[0-9]+", "--spec-min-p": r"[0-9.]+", "--kv": r"int8|k8v4|q4_0",
                "--expert-cache": r"auto", "--prefill": r"auto|[0-9]+"}
# From this context the KV cache streams: the engine keeps a window resident
# and the rest in pinned RAM, about 13.7 KB per token and slot (Strata
# setup's rule, which also requires the RAM to hold it).
KV_STREAM_FROM = 65536
KV_RESIDENT = 32768
KV_HOST_BYTES = 13_700
HEADROOM = 16 * 1024 ** 3


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
        raise ValueError("MODEL must name a Strata model config")
    return Path(os.environ.get("STRATA_MODEL_CONF", ROOT / "models" / (tag + ".conf"))).resolve()


def config(tag):
    path = config_path(tag)
    script = 'set -eu; source "$1"; shift; for name; do printf "%s\\0" "${!name}"; done'
    output = subprocess.check_output(["bash", "-c", script, "bash", str(path), *CONFIG_KEYS])
    values = dict(zip(CONFIG_KEYS, output.decode().split("\0")[:-1]))
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", values["STRATA_MODEL_REPO"]):
        raise ValueError("STRATA_MODEL_REPO must be a full Hugging Face repository ID")
    if not re.fullmatch(r"[0-9a-f]{40}", values["STRATA_MODEL_REVISION"]):
        raise ValueError("STRATA_MODEL_REVISION must be an immutable commit")
    for key in ("STRATA_PACK", "STRATA_DENSE_GGUF", "STRATA_PLE_GGUF", "STRATA_EMBD_GGUF"):
        if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]*", values[key]):
            raise ValueError(f"{key} must be a file or folder name in the repository's top level")
    if int(values["STRATA_CTX"]) <= 0:
        raise ValueError("STRATA_CTX must be positive")
    if not 1 <= int(values["STRATA_PARALLEL"]) <= 8:
        raise ValueError("STRATA_PARALLEL must be 1..8 (the engine's batch window)")
    engine_flags(values)
    return values


def engine_flags(values):
    """STRATA_ENGINE_ARGS: the model's documented engine flags, as pairs."""
    words = values["STRATA_ENGINE_ARGS"].split()
    if len(words) % 2:
        raise ValueError("STRATA_ENGINE_ARGS must be flag/value pairs")
    result = []
    for flag, value in zip(words[::2], words[1::2]):
        if flag not in ENGINE_FLAGS or not re.fullmatch(ENGINE_FLAGS[flag], value):
            raise ValueError(f"STRATA_ENGINE_ARGS entry {flag} {value} is not one of {sorted(ENGINE_FLAGS)}")
        result += [flag, value]
    return result


def require_host():
    if platform.system() != "Linux":
        raise RuntimeError(f"Strata's managed runtime needs Linux with an NVIDIA GPU; this host is {platform.system()}")
    require_tool("nvidia-smi")


def require_stopped():
    if PIDFILE.exists():
        raise RuntimeError(f"managed state exists at {PIDFILE}; run make strata-stop first")


def require_tool(name):
    if not shutil.which(name):
        raise RuntimeError(f"{name} is required but not on PATH")


def gpu_archs():
    output = subprocess.check_output(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"], text=True)
    archs = sorted({int(line.strip().replace(".", "")) for line in output.splitlines() if line.strip()})
    if not archs or min(archs) < 75:
        raise RuntimeError(f"Strata needs compute capability 7.5 or newer; this host reports {archs}")
    return archs


def gpu_processes():
    output = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"], text=True)
    return {int(line) for line in output.split()}


def cuda_root():
    """The CUDA toolkit the engine is compiled against: STRATA_CUDA_HOME, the
    nvcc on PATH, or the toolkit's standard install location."""
    nvcc = shutil.which("nvcc")
    for candidate in (os.environ.get("STRATA_CUDA_HOME"), nvcc and str(Path(nvcc).resolve().parent.parent),
                      "/usr/local/cuda"):
        if candidate and (Path(candidate) / "bin" / "nvcc").exists():
            return Path(candidate).resolve()
    raise RuntimeError("the CUDA toolkit (nvcc) is required; set STRATA_CUDA_HOME to its root")


def git_head(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def fetch(path, repository, commit):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".source-", dir=path.parent))
    for argv in (["init", "-q"], ["remote", "add", "origin", repository + ".git"],
                 ["fetch", "-q", "--depth", "1", "origin", commit],
                 ["-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD"]):
        subprocess.run(["git", "-C", str(stage), *argv], check=True)
    stage.rename(path)


def pinned(name):
    """A pin the source tree states once: setup.py's llama.cpp commit, the
    MTP tensors' checkpoint revision in tools/mtp_fetch.py."""
    files = {"LLAMA_CPP_COMMIT": SOURCE / "setup.py", "PINNED_REVISION": SOURCE / "tools" / "mtp_fetch.py"}
    match = re.search(rf'^{name} = "([0-9a-f]{{40}})"', files[name].read_text(), re.MULTILINE)
    if not match:
        raise RuntimeError(f"no {name} pin in {files[name]}")
    return match.group(1)


def llama_dir():
    return DATA / "llama.cpp" / pinned("LLAMA_CPP_COMMIT")


def verify_source():
    if git_head(SOURCE) != COMMIT:
        raise RuntimeError(f"{SOURCE} is not at the pin {COMMIT}; run make strata-install")
    if subprocess.check_output(["git", "-C", str(SOURCE), "status", "--porcelain", "--untracked-files=no"], text=True):
        raise RuntimeError(f"{SOURCE} has local changes; run make strata-install after removing it")
    receipt = json.loads(RECEIPT.read_text())
    if receipt["engine_sha256"] != digest(ENGINE):
        raise RuntimeError("engine checksum mismatch; run make strata-install")
    if git_head(llama_dir()) != receipt["llama_cpp"]:
        raise RuntimeError("the llama.cpp checkout differs from the install")
    return receipt


def install():
    require_stopped()
    require_host()
    for tool in ("git", "python3", "c++"):
        require_tool(tool)
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", VERSION):
        raise ValueError("STRATA_VERSION must be a release version")
    if not re.fullmatch(r"[0-9a-f]{40}", COMMIT):
        raise ValueError("STRATA_COMMIT must pin the release's commit")
    fetch(SOURCE, REPOSITORY, COMMIT)
    if git_head(SOURCE) != COMMIT:
        raise RuntimeError(f"{SOURCE} is not at the pin {COMMIT}; remove it and run make strata-install")
    llama = llama_dir()
    fetch(llama, LLAMA_REPOSITORY, llama.name)
    # The server, the model tools and the build tools (cmake, ninja) at the
    # versions the release pins, in the tree's own venv.
    if not PYTHON.exists():
        subprocess.run(["python3", "-m", "venv", str(SOURCE / ".venv")], check=True)
    # Plus the root Makefile's pinned Hugging Face client, for the pull.
    subprocess.run([str(PYTHON), "-m", "pip", "install", "-q", "-r", str(SOURCE / "requirements.txt"),
                    "-r", str(SOURCE / "requirements-build.txt"), HF_HUB], check=True)
    cuda, archs = cuda_root(), gpu_archs()
    bin_dir = SOURCE / ".venv" / "bin"
    # The options Strata's own source setup passes for an NVIDIA build, for
    # the GPUs in this host; vision is off in the fleet's profiles.
    subprocess.run([str(bin_dir / "cmake"), "-G", "Ninja", f"-DCMAKE_MAKE_PROGRAM={bin_dir / 'ninja'}",
                    "-S", str(SOURCE), "-B", str(SOURCE / "build"), "-DCMAKE_BUILD_TYPE=Release",
                    "-DSTRATA_ENABLE_CUDA=ON", "-DSTRATA_BUILD_TESTS=OFF", "-DSTRATA_Q6K_EXPERTS=ON",
                    "-DSTRATA_MMQ_KQUANTS=ON", f"-DCMAKE_CUDA_ARCHITECTURES={';'.join(map(str, archs))}",
                    f"-DCMAKE_CUDA_COMPILER={cuda / 'bin' / 'nvcc'}", f"-DCUDAToolkit_ROOT={cuda}",
                    f"-DSTRATA_GGML_DIR={llama}"], check=True)
    subprocess.run([str(bin_dir / "cmake"), "--build", str(SOURCE / "build"), "--target", "strata",
                    "-j", str(os.cpu_count() or 4)], check=True)
    save(RECEIPT, {"version": VERSION, "commit": COMMIT, "llama_cpp": git_head(llama),
                   "cuda": str(cuda), "archs": archs, "engine_sha256": digest(ENGINE)})
    receipt = verify_source()
    print(f"Strata {VERSION} ({COMMIT}) built for sm_{','.join(map(str, archs))} at {ENGINE}, "
          f"CUDA {receipt['cuda']}, llama.cpp {receipt['llama_cpp']}")


def hf_command():
    """A host hf when present, else the pinned client install put in the venv."""
    if shutil.which("hf"):
        return ["hf"]
    return [str(SOURCE / ".venv" / "bin" / "hf")]


def model_dir(values):
    return MODELS / values["STRATA_MODEL_REPO"].replace("/", "--") / values["STRATA_MODEL_REVISION"]


def mtp_dir():
    """The MTP draft layer every Flash-Next pack shares, built from the
    original checkpoint's MTP tensors at the source tree's pinned revision."""
    return DATA / "mtp" / pinned("PINNED_REVISION")


def model_files(values):
    """Every file the engine reads from the model folder."""
    root = model_dir(values)
    pack = root / values["STRATA_PACK"]
    files = sorted(path for path in pack.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError(f"{pack} holds no pack; run make strata-pull")
    return files + [root / values[key] for key in ("STRATA_DENSE_GGUF", "STRATA_PLE_GGUF", "STRATA_EMBD_GGUF")]


def identity_record(values):
    root, mtp = model_dir(values), mtp_dir() / "rt"
    return {"source": values["STRATA_MODEL_REPO"], "revision": values["STRATA_MODEL_REVISION"],
            "mtp_revision": mtp.parent.name,
            "files": {str(path.relative_to(root)): digest(path) for path in model_files(values)},
            "mtp": {str(path.relative_to(mtp)): digest(path)
                    for path in sorted(mtp.rglob("*")) if path.is_file()}}


def verify_model(values):
    record = json.loads((model_dir(values) / "llm-local-servers.json").read_text())
    if record != identity_record(values):
        raise RuntimeError("the model files differ from the pulled and verified ones; run make strata-pull")
    return {"source": record["source"], "revision": record["revision"], "mtp_revision": record["mtp_revision"],
            "identity_sha256": hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest(),
            "full_artifact_hash_verification": True}


def tool(name, *argv):
    environment = {**os.environ, "STRATA_GGUF_PY": str(llama_dir() / "gguf-py")}
    subprocess.run([str(PYTHON), str(SOURCE / "tools" / name), *argv], check=True, env=environment)


def pull(values):
    require_stopped()
    verify_source()
    MODELS.mkdir(parents=True, exist_ok=True)
    root = model_dir(values)
    subprocess.run([*hf_command(), "download", values["STRATA_MODEL_REPO"],
                    "--revision", values["STRATA_MODEL_REVISION"], "--local-dir", str(root),
                    "--include", values["STRATA_PACK"] + "/*", "--include", values["STRATA_DENSE_GGUF"],
                    "--include", values["STRATA_PLE_GGUF"], "--include", values["STRATA_EMBD_GGUF"],
                    "--quiet"], check=True, stdout=subprocess.DEVNULL)
    mtp = mtp_dir()
    if not (mtp / "rt").is_dir():
        # Strata setup's draft-layer recipe: fetch the MTP tensors (resumable,
        # SHA-256 checked against the pin), pack them, build the runtime form
        # into a staging folder that becomes rt/ only when complete.
        tool("mtp_fetch.py", "fetch", "--out", str(mtp))
        tool("mtp_fetch.py", "verify", "--out", str(mtp))
        tool("mtp_pack.py", "--src", str(mtp), "--experts", "q2_0", "--out", str(mtp / "mtp-q2_0.gguf"))
        stage = mtp / "rt.partial"
        if stage.exists():
            shutil.rmtree(stage)
        tool("mtp_rt.py", "--gguf", str(mtp / "mtp-q2_0.gguf"), "--out", str(stage))
        stage.rename(mtp / "rt")
    save(root / "llm-local-servers.json", identity_record(values))
    identity = verify_model(values)
    print(f"Verified {identity['source']} at {identity['revision']} in {root}; MTP {identity['mtp_revision']}")


def meminfo():
    fields = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        name, value = line.split(":", 1)
        fields[name] = int(value.split()[0]) * 1024
    return fields


def placement(values):
    """Host-derived memory placement beside the pinned expert copy: the KV
    cache streamed from RAM from KV_STREAM_FROM when the RAM holds it, then
    the n-gram table in RAM when it fits too, otherwise read from the disk."""
    root = model_dir(values)
    pack = root / values["STRATA_PACK"]
    used = sum(path.stat().st_size for path in pack.glob("experts*.bin")) + HEADROOM
    available = meminfo()["MemAvailable"]
    flags = []
    context = int(values["STRATA_CTX"])
    kv = KV_HOST_BYTES * context * int(values["STRATA_PARALLEL"])
    if context >= KV_STREAM_FROM and available >= used + kv:
        flags += ["--kv-resident", str(KV_RESIDENT)]
        used += kv
    if available >= used + (root / values["STRATA_PLE_GGUF"]).stat().st_size:
        flags += ["--ple-io", "ram"]
    return flags


def run_config(values, receipt):
    root = model_dir(values)
    dense = str(root / values["STRATA_DENSE_GGUF"])
    args = ["--pack", str(root / values["STRATA_PACK"]), "--native", dense, "--native-dense-gguf", dense,
            "--ple-gguf", str(root / values["STRATA_PLE_GGUF"]),
            "--embd-gguf", str(root / values["STRATA_EMBD_GGUF"]),
            "--expert-profile", str(SOURCE / "data" / "expert-profile.bin"),
            "--mtp", str(mtp_dir() / "rt"), "--max-context", values["STRATA_CTX"],
            *engine_flags(values), *placement(values)]
    cuda = Path(receipt["cuda"])
    return {"exe": str(ENGINE), "args": args, "cwd": str(SOURCE),
            "tokenizer": str(root / values["STRATA_PACK"] / "tokenizer"),
            "model_name": values["STRATA_SERVED_NAME"], "log": str(ENGINE_LOG),
            "lib_dirs": [str(cuda / "bin"), str(cuda / "lib64")],
            "port": port(), "gpu": 0, "parallel": int(values["STRATA_PARALLEL"]), "open_browser": False}


def port():
    value = int(os.environ.get("STRATA_PORT", "8025"))
    if not 1 <= value <= 65535:
        raise ValueError("STRATA_PORT must be 1..65535")
    return value


def command():
    # 127.0.0.1 is the server's default bind; --offline refuses image URLs
    # and MCP subprocesses. Remote use goes through an ssh tunnel.
    return [str(PYTHON), str(SOURCE / "serve" / "server.py"), "--engine", "strata", "--config", str(RUN_CONFIG),
            "--host", "127.0.0.1", "--port", str(port()), "--offline"]


def serve_environment():
    """The engine reads STRATA_* tuning switches from the environment the
    server passes on; only the config's flags may tune a managed run."""
    return {key: value for key, value in os.environ.items() if not key.startswith("STRATA_")}


def port_free(number):
    with socket.socket(socket.AF_INET) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", number))


def started(pid):
    """A live process's start time in clock ticks since boot, from /proc;
    None for a process that is gone or a zombie."""
    try:
        fields = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else int(fields[19])
    except (OSError, IndexError, ValueError):
        return None


def executable(pid):
    try:
        return os.readlink(Path("/proc") / str(pid) / "exe")
    except OSError:
        return None


def arguments(pid):
    try:
        return (Path("/proc") / str(pid) / "cmdline").read_bytes().split(b"\0")
    except OSError:
        return []


def owned(entry, marker):
    """True while the recorded process is alive, is the same process (start
    time) and runs the managed script or binary (marker in its arguments)."""
    if type(entry.get("pid")) is not int or entry["pid"] <= 1:
        raise RuntimeError("invalid managed PID")
    tick = started(entry["pid"])
    if tick is None:
        return False
    if tick != entry["started"]:
        raise RuntimeError("managed PID has been reused; refusing to signal it")
    if os.fsencode(marker) not in arguments(entry["pid"]):
        raise RuntimeError(f"managed PID {entry['pid']} runs an unrecognized command")
    return True


def server_owned(owner):
    # Until the handshake completes the session leader is start.sh, then
    # runtime.py serve; both exec into the server.
    try:
        return owned(owner, str(SOURCE / "serve" / "server.py"))
    except RuntimeError:
        if any(os.fsencode(str(ROOT / name)) in arguments(owner["pid"]) for name in ("start.sh", "runtime.py")):
            return True
        raise


def engine_owned(owner):
    """The server restarts a dead engine on the next request, so the engine
    is looked up again under the server when the recorded one is gone."""
    if owner.get("engine") and owned(owner["engine"], str(ENGINE)):
        return True
    owner["engine"] = engine_child(owner["pid"]) if started(owner["pid"]) is not None else None
    return bool(owner["engine"])


def request(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def engine_child(server_pid):
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit() and executable(int(entry.name)) == os.path.realpath(ENGINE):
            try:
                parent = int((entry / "stat").read_text().rsplit(")", 1)[1].split()[1])
            except (OSError, IndexError, ValueError):
                continue
            if parent == server_pid:
                return {"pid": int(entry.name), "started": started(int(entry.name))}
    return None


def residency():
    """The engine's own report of where the routed experts live."""
    match = re.search(r"every expert is in the GPU cache \(([0-9]+) of ([0-9]+)\)", ENGINE_LOG.read_text())
    if match:
        return {"experts_in_vram": int(match.group(1)), "experts": int(match.group(2))}
    match = re.search(r"expert cache ([0-9]+) slots", ENGINE_LOG.read_text())
    return {"experts_in_vram": int(match.group(1)) if match else 0, "experts": None}


def check_live(values, owner, identity):
    if (owner["model_identity"] != identity or owner["command"] != command()
            or owner["engine_flags"] != engine_flags(values)
            or owner["run_config"]["parallel"] != int(values["STRATA_PARALLEL"])):
        raise RuntimeError("selected model/config differs from the managed launch")
    if not server_owned(owner) or not engine_owned(owner):
        raise RuntimeError("managed Strata server is not running")
    base = f"http://127.0.0.1:{owner['port']}"
    models = request(f"{base}/v1/models")["data"]
    if [item["id"] for item in models] != [values["STRATA_SERVED_NAME"]]:
        raise RuntimeError("live served model differs from the config")
    health = request(f"{base}/health")
    if not health.get("loaded") or health.get("max_context") != int(values["STRATA_CTX"]):
        raise RuntimeError("live context differs from the config")
    return base, health


def start(tag, values):
    require_stopped()
    require_host()
    port_free(port())
    busy = gpu_processes()
    if busy:
        raise RuntimeError(f"another GPU compute process is active (pids {sorted(busy)}); refusing to start")
    receipt = verify_source()
    if receipt["archs"] != gpu_archs():
        raise RuntimeError("the engine was built for other GPUs; run make strata-install")
    print("Verifying all model artifacts before launch...", flush=True)
    identity = verify_model(values)
    STATE.mkdir(parents=True, exist_ok=True)
    save(RUN_CONFIG, run_config(values, receipt))
    ENGINE_LOG.unlink(missing_ok=True)
    argv = command()
    with LOG.open("w") as log:
        log.write("starting " + shlex.join(argv) + "\n")
        log.flush()
        process = subprocess.Popen([str(ROOT / "start.sh"), tag], stdin=subprocess.PIPE, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    try:
        tick = started(process.pid)
        if tick is None:
            raise RuntimeError(f"Strata launcher exited before registration; see {LOG}")
        owner = {"pid": process.pid, "started": tick, "command": argv, "port": port(),
                 "run_config": json.loads(RUN_CONFIG.read_text()), "engine_flags": engine_flags(values),
                 "receipt": receipt, "model_identity": identity}
        save(PIDFILE, owner)
        # The foreground child cannot exec the server until registration is
        # durable. EOF on a failed parent makes it exit without the GPU.
        process.stdin.write(b"\n")
        process.stdin.close()
        deadline = time.monotonic() + int(os.environ.get("STRATA_START_TIMEOUT", "1800"))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Strata exited during startup; see {LOG} and {ENGINE_LOG}")
            if not owner.get("engine"):
                owner["engine"] = engine_child(process.pid)
                if owner["engine"]:
                    save(PIDFILE, owner)
            try:
                if owner.get("engine") and request(f"http://127.0.0.1:{port()}/health").get("loaded"):
                    base, _health = check_live(values, owner, identity)
                    owner["residency"] = residency()
                    save(PIDFILE, owner)
                    print(f"Ready: {values['STRATA_SERVED_NAME']} at {base}; PID {process.pid}; "
                          f"{owner['residency']['experts_in_vram']} experts in VRAM")
                    return
            except (OSError, ValueError):
                pass
            time.sleep(5)
        raise TimeoutError(f"Strata readiness timeout; see {LOG}")
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
        print("Strata is stopped (no managed pidfile); retained any existing log.")
        return
    owner = json.loads(PIDFILE.read_text())
    # The server stops its engine, which runs in a process group of its own,
    # on SIGTERM; a surviving engine is signalled directly.
    running = engine_owned(owner)
    running = server_owned(owner) or running
    engine = (owner.get("engine") or {}).get("pid")
    for key, check in (("server", server_owned), ("engine", engine_owned)):
        entry = owner if key == "server" else owner.get("engine")
        if not entry or not check(owner):
            continue
        os.kill(entry["pid"], signal.SIGTERM)
        for attempt in range(120):
            if started(entry["pid"]) is None:
                break
            if attempt == 90:
                check(owner)
                os.kill(entry["pid"], signal.SIGKILL)
            time.sleep(0.5)
        if started(entry["pid"]) is not None:
            raise RuntimeError(f"Strata {key} PID {entry['pid']} did not exit; state retained")
    for _ in range(60):
        if engine not in gpu_processes():
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"Strata engine PID {engine} still holds the GPU; state retained")
    port_free(owner["port"])
    PIDFILE.unlink()
    RUN_CONFIG.unlink(missing_ok=True)
    if not running:
        print(f"Strata was not running; removed its pidfile and kept the logs in {STATE} as evidence.")
        return
    if not preserve_log:
        LOG.unlink(missing_ok=True)
        ENGINE_LOG.unlink(missing_ok=True)
    print(f"Stopped: server and engine exited, GPU released, port {owner['port']} free.")


def status():
    if not PIDFILE.exists():
        print("server:   not running")
        return
    owner = json.loads(PIDFILE.read_text())
    if not server_owned(owner) or not engine_owned(owner):
        raise RuntimeError("managed server is not running; use make strata-stop to inspect teardown")
    health = request(f"http://127.0.0.1:{owner['port']}/health")
    print(f"server:   running (pid {owner['pid']}, engine {owner['engine']['pid']}, port {owner['port']})")
    print(f"model:    {health['model']} ({owner['model_identity']['source']})")
    print(json.dumps({"model": owner["model_identity"], "receipt": owner["receipt"],
                      "context": health["max_context"], "slots": owner["run_config"]["parallel"],
                      "residency": owner.get("residency"), "args": owner["run_config"]["args"]}, indent=2))


def main():
    action = sys.argv[1]
    if action == "status":
        status()
        return
    if action == "serve":
        if sys.stdin.isatty() or sys.stdin.buffer.read(1) != b"\n":
            raise RuntimeError("start.sh is internal; use make strata-start")
        owner = json.loads(PIDFILE.read_text())
        if owner["pid"] != os.getpid() or os.getpgrp() != os.getpid():
            raise RuntimeError("foreground child does not own the managed session")
        os.chdir(SOURCE)
        os.execve(owner["command"][0], owner["command"], serve_environment())
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
            raise ValueError("unknown Strata action")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"error: {error}") from error
