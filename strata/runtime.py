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
# Flash Next runs on the main engine; Inkling 2 Mini (GGUF architecture
# inkling2_loop) on its own shape engine, a build of its own.
ENGINES = {"qwen": SOURCE / "build" / "strata", "inkling": SOURCE / "build-inkling2" / "strata-inkling"}
# 0.2.16 moved the server, its tools and data under terminal/, the engine's
# CMake project under engine/.
TERMINAL = SOURCE / "terminal"
PYTHON = SOURCE / ".venv" / "bin" / "python"
RECEIPT = SOURCE / "llm-local-servers.json"
MODELS = DATA / "models"
PIDFILE = STATE / "server.json"
LOG = STATE / "server.log"
ENGINE_LOG = STATE / "engine.log"
RUN_CONFIG = STATE / "run.json"
REPOSITORY = "https://github.com/Niko1221/Strata"
HF_HUB = "huggingface_hub[hf_xet]==" + os.environ.get("HF_HUB_VERSION", "1.33.0")
CONFIG_KEYS = tuple("STRATA_" + name for name in (
    "FAMILY", "SERVED_NAME", "MODEL_REPO", "MODEL_REVISION", "PACK", "DENSE_GGUF", "PLE_GGUF", "EMBD_GGUF",
    "GGUF", "DRAFTER",
    "CTX", "PARALLEL", "ENGINE_ARGS", "CAP_REASONING", "CAP_TOOLS", "CAP_REASONING_MODE",
    "CAP_DISABLE_MODE", "CAP_SYSTEM_PROMPT", "SAMPLING",
))
# Engine flags a config may set. Everything else the launcher owns: paths,
# context, slots, and the host-derived memory placement.
ENGINE_FLAGS = {"qwen": {"--spec": r"[0-9]+", "--spec-min-p": r"[0-9.]+", "--kv": r"int8|k8v4|q4_0",
                         "--expert-cache": r"auto", "--prefill": r"auto|[0-9]+"},
                "inkling": {"--kv": r"fp16|fp8|k8v8|k8v4"}}
NAME = r"[a-zA-Z0-9_][a-zA-Z0-9_.-]*"
# A file of another repository: owner/name@commit:path.
REFERENCE = re.compile(rf"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)@([0-9a-f]{{40}}):({NAME}(?:/{NAME})*)")
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
    script = 'set -eu; source "$1"; shift; for name; do printf "%s\\0" "${!name-}"; done'
    output = subprocess.check_output(["bash", "-c", script, "bash", str(path), *CONFIG_KEYS])
    values = dict(zip(CONFIG_KEYS, output.decode().split("\0")[:-1]))
    values["STRATA_FAMILY"] = values["STRATA_FAMILY"] or "qwen"
    if values["STRATA_FAMILY"] not in ENGINES:
        raise ValueError(f"STRATA_FAMILY must be one of {sorted(ENGINES)}")
    if not re.fullmatch(NAME, values["STRATA_SERVED_NAME"]):
        raise ValueError("STRATA_SERVED_NAME must be a plain model name")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", values["STRATA_MODEL_REPO"]):
        raise ValueError("STRATA_MODEL_REPO must be a full Hugging Face repository ID")
    if not re.fullmatch(r"[0-9a-f]{40}", values["STRATA_MODEL_REVISION"]):
        raise ValueError("STRATA_MODEL_REVISION must be an immutable commit")
    if values["STRATA_FAMILY"] == "qwen":
        for key in ("STRATA_PACK", "STRATA_DENSE_GGUF", "STRATA_PLE_GGUF", "STRATA_EMBD_GGUF"):
            if not re.fullmatch(NAME, values[key]):
                raise ValueError(f"{key} must be a file or folder name in the repository's top level")
    else:
        if not re.fullmatch(rf"{NAME}\.gguf", values["STRATA_GGUF"]):
            raise ValueError("STRATA_GGUF must name a GGUF file in the repository's top level")
        reference(values["STRATA_DRAFTER"], "STRATA_DRAFTER")
    if int(values["STRATA_CTX"]) <= 0:
        raise ValueError("STRATA_CTX must be positive")
    if not 1 <= int(values["STRATA_PARALLEL"]) <= 8:
        raise ValueError("STRATA_PARALLEL must be 1..8 (the engine's batch window)")
    engine_flags(values)
    return values


def reference(text, key):
    """A file of another repository as (repository, revision, path)."""
    match = REFERENCE.fullmatch(text)
    if not match:
        raise ValueError(f"{key} must be owner/name@commit:path")
    return match.groups()


def engine_flags(values):
    """STRATA_ENGINE_ARGS: the model's documented engine flags, as pairs."""
    words = values["STRATA_ENGINE_ARGS"].split()
    if len(words) % 2:
        raise ValueError("STRATA_ENGINE_ARGS must be flag/value pairs")
    allowed = ENGINE_FLAGS[values["STRATA_FAMILY"]]
    result = []
    for flag, value in zip(words[::2], words[1::2]):
        if flag not in allowed or not re.fullmatch(allowed[flag], value):
            raise ValueError(f"STRATA_ENGINE_ARGS entry {flag} {value} is not one of {sorted(allowed)}")
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


def pinned_mtp_revision():
    """The MTP tensors' checkpoint revision, a pin the source tree states once
    in terminal/tools/mtp_fetch.py."""
    path = TERMINAL / "tools" / "mtp_fetch.py"
    match = re.search(r'^PINNED_REVISION = "([0-9a-f]{40})"', path.read_text(), re.MULTILINE)
    if not match:
        raise RuntimeError(f"no PINNED_REVISION pin in {path}")
    return match.group(1)


def verify_source():
    if git_head(SOURCE) != COMMIT:
        raise RuntimeError(f"{SOURCE} is not at the pin {COMMIT}; run make strata-install")
    if subprocess.check_output(["git", "-C", str(SOURCE), "status", "--porcelain", "--untracked-files=no"], text=True):
        raise RuntimeError(f"{SOURCE} has local changes; run make strata-install after removing it")
    receipt = json.loads(RECEIPT.read_text())
    if receipt.get("engines_sha256") != {family: digest(path) for family, path in ENGINES.items()}:
        raise RuntimeError("engine checksum mismatch; run make strata-install")
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
    # The server, the model tools and the build tools (cmake, ninja) at the
    # versions the release pins, in the tree's own venv.
    if not PYTHON.exists():
        subprocess.run(["python3", "-m", "venv", str(SOURCE / ".venv")], check=True)
    # Plus the root Makefile's pinned Hugging Face client, for the pull.
    subprocess.run([str(PYTHON), "-m", "pip", "install", "-q", "-r", str(TERMINAL / "requirements.txt"),
                    "-r", str(TERMINAL / "requirements-build.txt"), HF_HUB], check=True)
    cuda, archs = cuda_root(), gpu_archs()
    bin_dir = SOURCE / ".venv" / "bin"
    # Strata setup's NVIDIA options for the host's GPUs, on its vendored ggml.
    # A ccache or sccache on PATH breaks nvcc, so CMake is told to use none.
    common = ["-G", "Ninja", f"-DCMAKE_MAKE_PROGRAM={bin_dir / 'ninja'}", "-S", str(SOURCE / "engine"),
              "-DCMAKE_BUILD_TYPE=Release", "-DSTRATA_ENABLE_CUDA=ON", "-DSTRATA_BUILD_TESTS=OFF",
              "-DGGML_CCACHE=OFF", f"-DCMAKE_CUDA_ARCHITECTURES={';'.join(map(str, archs))}",
              f"-DCMAKE_CUDA_COMPILER={cuda / 'bin' / 'nvcc'}", f"-DCUDAToolkit_ROOT={cuda}"]
    for family, flags in (("qwen", ["-DSTRATA_Q6K_EXPERTS=ON"]),
                          ("inkling", ["-DSTRATA_BUILD_INKLING=ON", "-DSTRATA_BUILD_HY4=OFF"])):
        build = ENGINES[family].parent
        subprocess.run([str(bin_dir / "cmake"), *common, "-B", str(build), *flags], check=True)
        # As Strata setup does: CUDA 13's ptxas fails a parse now and then,
        # so a failed build is run once more before it counts.
        argv = [str(bin_dir / "cmake"), "--build", str(build), "--target", ENGINES[family].name,
                "-j", str(os.cpu_count() or 4)]
        if subprocess.run(argv).returncode:
            subprocess.run(argv, check=True)
        if family == "inkling" and not ENGINES[family].exists():
            shutil.copy2(build / "src" / "inkling2" / ENGINES[family].name, ENGINES[family])
    save(RECEIPT, {"version": VERSION, "commit": COMMIT, "cuda": str(cuda), "archs": archs,
                   "engines_sha256": {family: digest(path) for family, path in ENGINES.items()}})
    receipt = verify_source()
    print(f"Strata {VERSION} ({COMMIT}) built for sm_{','.join(map(str, archs))}: "
          f"{', '.join(map(str, ENGINES.values()))}; CUDA {receipt['cuda']}")


def hf_command():
    """A host hf when present, else the pinned client install put in the venv."""
    if shutil.which("hf"):
        return ["hf"]
    return [str(SOURCE / ".venv" / "bin" / "hf")]


def repo_dir(repository, revision):
    return MODELS / repository.replace("/", "--") / revision


def model_dir(values):
    return repo_dir(values["STRATA_MODEL_REPO"], values["STRATA_MODEL_REVISION"])


def source_path(source):
    return repo_dir(source[0], source[1]) / source[2]


def inkling_sources(values):
    """An Inkling build's downloads as (repository, revision, path): the GGUF,
    the DSpark drafter (the original checkpoint's mtp.safetensors, which an
    engine that reports dspark_f32_widen reads), and that checkpoint's
    tokenizer and chat template, from which the server's tokenizer is made."""
    repository, revision, drafter = reference(values["STRATA_DRAFTER"], "STRATA_DRAFTER")
    return [(values["STRATA_MODEL_REPO"], values["STRATA_MODEL_REVISION"], values["STRATA_GGUF"]),
            (repository, revision, drafter), (repository, revision, "tokenizer.json"),
            (repository, revision, "chat_template.jinja")]


def tokenizer_dir(values):
    return model_dir(values) / "tokenizer"


def mtp_dir():
    """The MTP draft layer every Flash-Next pack shares, built from the
    original checkpoint's MTP tensors at the source tree's pinned revision."""
    return DATA / "mtp" / pinned_mtp_revision()


def model_files(values):
    """Every file the engine reads from the model folder."""
    if values["STRATA_FAMILY"] == "inkling":
        tokenizer = sorted(path for path in tokenizer_dir(values).rglob("*") if path.is_file())
        if not tokenizer:
            raise RuntimeError(f"{tokenizer_dir(values)} holds no tokenizer; run make strata-pull")
        return [source_path(source) for source in inkling_sources(values)] + tokenizer
    root = model_dir(values)
    pack = root / values["STRATA_PACK"]
    files = sorted(path for path in pack.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError(f"{pack} holds no pack; run make strata-pull")
    return files + [root / values[key] for key in ("STRATA_DENSE_GGUF", "STRATA_PLE_GGUF", "STRATA_EMBD_GGUF")]


def identity_record(values):
    if values["STRATA_FAMILY"] == "inkling":
        return {"source": values["STRATA_MODEL_REPO"], "revision": values["STRATA_MODEL_REVISION"],
                "files": {str(path.relative_to(MODELS)): digest(path) for path in model_files(values)}}
    root, mtp = model_dir(values), mtp_dir() / "rt"
    return {"source": values["STRATA_MODEL_REPO"], "revision": values["STRATA_MODEL_REVISION"],
            "mtp_revision": mtp.parent.name,
            "files": {str(path.relative_to(root)): digest(path) for path in model_files(values)},
            "mtp": {str(path.relative_to(mtp)): digest(path)
                    for path in sorted(mtp.rglob("*")) if path.is_file()}}


def identity_path(values):
    return model_dir(values) / "llm-local-servers.json"


def verify_model(values):
    record = json.loads(identity_path(values).read_text())
    if record != identity_record(values):
        raise RuntimeError("the model files differ from the pulled and verified ones; run make strata-pull")
    return {"source": record["source"], "revision": record["revision"], "mtp_revision": record.get("mtp_revision"),
            "identity_sha256": hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest(),
            "full_artifact_hash_verification": True}


def tool(name, *argv):
    subprocess.run([str(PYTHON), str(TERMINAL / "tools" / name), *argv], check=True)


def download(repository, revision, paths):
    subprocess.run([*hf_command(), "download", repository, "--revision", revision,
                    "--local-dir", str(repo_dir(repository, revision)),
                    *[word for path in paths for word in ("--include", path)], "--quiet"],
                   check=True, stdout=subprocess.DEVNULL)


def pull_inkling(values):
    sources = inkling_sources(values)
    for repository, revision in dict.fromkeys(source[:2] for source in sources):
        download(repository, revision, [path for *pin, path in sources if pin == [repository, revision]])
    out = tokenizer_dir(values)
    if not out.is_dir():
        # Strata setup's recipe: the checkpoint's tokenizer.json and chat
        # template converted into the server's tokenizer folder, staged.
        stage = out.with_name(out.name + ".partial")
        if stage.exists():
            shutil.rmtree(stage)
        script = "import sys; sys.path.insert(0, sys.argv[1]); import inkling_tokenizer as t; t.convert_files(*sys.argv[2:5])"
        subprocess.run([str(PYTHON), "-c", script, str(TERMINAL / "tools"),
                        *[str(source_path(source)) for source in sources[2:]], str(stage)], check=True)
        stage.rename(out)


def pull(values):
    require_stopped()
    verify_source()
    MODELS.mkdir(parents=True, exist_ok=True)
    root = model_dir(values)
    if values["STRATA_FAMILY"] == "inkling":
        pull_inkling(values)
        save(identity_path(values), identity_record(values))
        identity = verify_model(values)
        print(f"Verified {identity['source']} at {identity['revision']} and its drafter and tokenizer")
        return
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
    cuda = Path(receipt["cuda"])
    common = {"model_name": values["STRATA_SERVED_NAME"], "log": str(ENGINE_LOG),
              "lib_dirs": [str(cuda / "bin"), str(cuda / "lib64")],
              "port": port(), "gpu": 0, "parallel": int(values["STRATA_PARALLEL"]), "open_browser": False}
    if values["STRATA_FAMILY"] == "inkling":
        # Strata setup's Inkling launch on a card that holds every expert:
        # all of them in VRAM, no RAM tier; the DSpark drafter on, as the
        # setup's probe turns it on for a CUDA card. No thinking budget: the
        # model thinks as long as its request lets it, as on every runtime.
        gguf, drafter = (source_path(source) for source in inkling_sources(values)[:2])
        experts = -(-gguf.stat().st_size // 1024 ** 3) + 1
        args = ["--native", str(gguf), "--max-context", values["STRATA_CTX"], "--dspark", str(drafter),
                "--vram-experts-gb", f"{experts}.00", *engine_flags(values)]
        return {**common, "exe": str(ENGINES["inkling"]), "args": args, "cwd": str(TERMINAL),
                "tokenizer": str(tokenizer_dir(values)), "arch": "inkling2_loop", "drafting": "dspark",
                "inkling_thinking_budget": 0,
                "lib_dirs": [*common["lib_dirs"], str(ENGINES["inkling"].parent)]}
    root = model_dir(values)
    dense = str(root / values["STRATA_DENSE_GGUF"])
    args = ["--pack", str(root / values["STRATA_PACK"]), "--native", dense, "--native-dense-gguf", dense,
            "--ple-gguf", str(root / values["STRATA_PLE_GGUF"]),
            "--embd-gguf", str(root / values["STRATA_EMBD_GGUF"]),
            "--expert-profile", str(TERMINAL / "data" / "expert-profile.bin"),
            "--mtp", str(mtp_dir() / "rt"), "--max-context", values["STRATA_CTX"],
            *engine_flags(values), *placement(values)]
    # MTP as set up for this pack: the server's auto drafting would choose
    # by the served name, which is no model fact.
    return {**common, "exe": str(ENGINES["qwen"]), "args": args, "cwd": str(TERMINAL),
            "tokenizer": str(root / values["STRATA_PACK"] / "tokenizer"), "drafting": "mtp"}


def port():
    value = int(os.environ.get("STRATA_PORT", "8025"))
    if not 1 <= value <= 65535:
        raise ValueError("STRATA_PORT must be 1..65535")
    return value


def command():
    # 127.0.0.1 is the server's default bind; --offline refuses image URLs
    # and MCP subprocesses. Remote use goes through an ssh tunnel.
    return [str(PYTHON), str(TERMINAL / "serve" / "server.py"), "--engine", "strata", "--config", str(RUN_CONFIG),
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
        return owned(owner, str(TERMINAL / "serve" / "server.py"))
    except RuntimeError:
        if any(os.fsencode(str(ROOT / name)) in arguments(owner["pid"]) for name in ("start.sh", "runtime.py")):
            return True
        raise


def engine_owned(owner):
    """The server restarts a dead engine on the next request, so the engine
    is looked up again under the server when the recorded one is gone."""
    engine = owner["run_config"]["exe"]
    if owner.get("engine") and owned(owner["engine"], engine):
        return True
    owner["engine"] = engine_child(owner["pid"], engine) if started(owner["pid"]) is not None else None
    return bool(owner["engine"])


def request(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def engine_child(server_pid, engine):
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit() and executable(int(entry.name)) == os.path.realpath(engine):
            try:
                parent = int((entry / "stat").read_text().rsplit(")", 1)[1].split()[1])
            except (OSError, IndexError, ValueError):
                continue
            if parent == server_pid:
                return {"pid": int(entry.name), "started": started(int(entry.name))}
    return None


def residency():
    """The engine's own report of where the routed experts live."""
    log = ENGINE_LOG.read_text()
    # Inkling: "experts=3072 GPU0 + 0 GPU-1 / 0 host".
    match = re.search(r"experts=([0-9]+) GPU0 \+ ([0-9]+) GPU-1 / ([0-9]+) host", log)
    if match:
        gpu0, gpu1, host = map(int, match.groups())
        return {"experts_in_vram": gpu0 + gpu1, "experts": gpu0 + gpu1 + host}
    match = re.search(r"every expert is in the GPU cache \(([0-9]+) of ([0-9]+)\)", log)
    if match:
        return {"experts_in_vram": int(match.group(1)), "experts": int(match.group(2))}
    match = re.search(r"expert cache ([0-9]+) slots", log)
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
                owner["engine"] = engine_child(process.pid, owner["run_config"]["exe"])
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
        os.chdir(TERMINAL)
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
