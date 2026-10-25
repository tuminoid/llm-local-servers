#!/usr/bin/env bash
#
# Shared paths and helpers for the vLLM server scripts. Sourced, not executed.
#
# Runtime state (pidfile, logs) lives outside the repo so nothing generated ever
# lands in git.

VLLM_STATE_DIR="${VLLM_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/vllm}"
VLLM_PIDFILE="${VLLM_PIDFILE:-${VLLM_STATE_DIR}/server.pid}"
VLLM_LOG="${VLLM_LOG:-${VLLM_STATE_DIR}/server.log}"
# The managed venv install.sh creates at the Makefile pins. Remote targets
# place it inside the deployed tree, which owns everything it runs.
VLLM_VENV="${VLLM_VENV:-${XDG_DATA_HOME:-${HOME}/.local/share}/vllm/venv}"

# GPU memory currently in use, in MiB. Prints 0 when nvidia-smi is unavailable
# so callers can compare numerically without guarding.
vllm_gpu_mib() {
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2> /dev/null || printf '0\n'
}

# Total GPU memory in MiB, or 0 when nvidia-smi is unavailable. Used to pick a
# host profile: a 12 GB desktop card and an 80 GB datacentre card want opposite
# answers for utilization, sequence count, and batch size.
vllm_gpu_total_mib() {
    nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2> /dev/null \
        | head -1 || printf '0\n'
}

# Compute capability as a comparable integer: sm_80 -> 80, sm_120 -> 120.
# Prints 0 when it cannot be determined, which callers must treat as "assume
# nothing is supported" rather than "assume everything is".
vllm_compute_cap() {
    local cap
    cap="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2> /dev/null | head -1)" \
        || cap=""
    cap="${cap//[[:space:]]/}"
    if [[ ! "${cap}" =~ ^[0-9]+\.[0-9]+$ ]]; then
        printf '0\n'
        return 0
    fi
    printf '%s\n' "${cap/./}"
}

# Path to the vllm executable, or empty: the VLLM_BIN override, else the
# managed venv. Never PATH, so a missing install fails rather than serving
# whatever release the host happens to carry.
vllm_bin() {
    local exe="${VLLM_BIN:-${VLLM_VENV}/bin/vllm}"
    [[ -x "${exe}" ]] && printf '%s\n' "${exe}"
    return 0
}

# uv, which the host must provide, or empty. A non-interactive ssh PATH often
# lacks the user install location, so that is tried as well.
vllm_uv() {
    command -v uv 2> /dev/null && return 0
    [[ -x "${HOME}/.local/bin/uv" ]] && printf '%s\n' "${HOME}/.local/bin/uv"
    return 0
}

# The hf CLI, or empty: the host's when it has one, else the managed venv's,
# which vllm's huggingface_hub dependency installs.
vllm_hf() {
    command -v hf 2> /dev/null && return 0
    [[ -x "${VLLM_VENV}/bin/hf" ]] && printf '%s\n' "${VLLM_VENV}/bin/hf"
    return 0
}

# The pinned Hub artifacts of a model conf, one "repo revision" line each:
# the model, then the speculative drafter when the conf names one. Arguments
# are the conf's VLLM_MODEL, VLLM_MODEL_REVISION and VLLM_SPECULATIVE_CONFIG.
# A drafter without a commit SHA revision is an error, not a floating download.
vllm_artifacts() {
    printf '%s %s\n' "$1" "$2"
    [[ -n "${3:-}" ]] || return 0
    python3 -c '
import json, re, sys
config = json.loads(sys.argv[1])
if "model" in config:
    if not re.fullmatch(r"[0-9a-f]{40}", str(config.get("revision", ""))):
        sys.exit("error: the speculative drafter needs a 40-character commit SHA revision")
    print(config["model"], config["revision"])
' "$3"
}

# Hugging Face cache directory of one artifact's pinned snapshot, resolved
# the way huggingface_hub resolves its cache.
vllm_snapshot() {
    local hub="${HF_HUB_CACHE:-${HUGGINGFACE_HUB_CACHE:-${HF_HOME:-${XDG_CACHE_HOME:-${HOME}/.cache}/huggingface}/hub}}"
    printf '%s\n' "${hub}/models--${1//\//--}/snapshots/$2"
}

# Model config names available under models/.
vllm_list_models() {
    local dir="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/models}"
    local conf
    for conf in "${dir}"/*.conf; do
        [[ -e "${conf}" ]] || continue
        printf '  %s\n' "$(basename "${conf}" .conf)"
    done
}

# Pid of the running server, or empty. Treats a stale pidfile as "not running".
vllm_pid() {
    [[ -f "${VLLM_PIDFILE}" ]] || return 0
    local pid
    pid="$(cat "${VLLM_PIDFILE}")"
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 0
    kill -0 "${pid}" 2> /dev/null || return 0
    printf '%s\n' "${pid}"
}
