#!/usr/bin/env bash
#
# Shared paths and helpers for the vLLM server scripts. Sourced, not executed.
#
# Runtime state (pidfile, logs) lives outside the repo so nothing generated ever
# lands in git.

VLLM_STATE_DIR="${VLLM_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/vllm}"
VLLM_PIDFILE="${VLLM_PIDFILE:-${VLLM_STATE_DIR}/server.pid}"
VLLM_LOG="${VLLM_LOG:-${VLLM_STATE_DIR}/server.log}"

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

# Path to the vllm executable, or empty. Three sources in order: an explicit
# override, a venv beside these scripts, then PATH. The venv case exists because
# not every host has the uv tool wrapper -- a plain `python3 -m venv` install is
# the portable fallback, and it must be found without being activated.
vllm_bin() {
    if [[ -n "${VLLM_BIN:-}" ]]; then
        [[ -x "${VLLM_BIN}" ]] && printf '%s\n' "${VLLM_BIN}"
        return 0
    fi
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -x "${here}/venv/bin/vllm" ]]; then
        printf '%s\n' "${here}/venv/bin/vllm"
        return 0
    fi
    command -v vllm 2> /dev/null || true
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
