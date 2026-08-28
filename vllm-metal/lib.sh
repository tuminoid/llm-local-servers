#!/usr/bin/env bash
#
# Shared paths and helpers for the vLLM-Metal server scripts. Sourced, not
# executed.
#
# Runtime state (pidfile, log) lives outside the repo, and so do the venv and
# the downloaded model weights: nothing generated ever lands in git.

VLLM_METAL_STATE_DIR="${VLLM_METAL_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/vllm-metal}"
VLLM_METAL_PIDFILE="${VLLM_METAL_PIDFILE:-${VLLM_METAL_STATE_DIR}/server.pid}"
VLLM_METAL_LOG="${VLLM_METAL_LOG:-${VLLM_METAL_STATE_DIR}/server.log}"
VLLM_METAL_DATA_DIR="${VLLM_METAL_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/vllm-metal}"
VLLM_METAL_VENV="${VLLM_METAL_VENV:-${VLLM_METAL_DATA_DIR}/venv}"
VLLM_METAL_MODELS_DIR="${VLLM_METAL_MODELS_DIR:-${VLLM_METAL_DATA_DIR}/models}"

# Path to the plugin venv's vllm, or empty. Only the override and the managed
# venv are accepted: a PATH vllm is the CUDA install or the uv tool wrapper,
# and running it here would serve without the Metal plugin. A missing venv
# must fail loudly, not fall back.
vllm_metal_bin() {
    if [[ -n "${VLLM_METAL_BIN:-}" ]]; then
        [[ -x "${VLLM_METAL_BIN}" ]] && printf '%s\n' "${VLLM_METAL_BIN}"
        return 0
    fi
    if [[ -x "${VLLM_METAL_VENV}/bin/vllm" ]]; then
        printf '%s\n' "${VLLM_METAL_VENV}/bin/vllm"
        return 0
    fi
}

# Model config names available under models/.
vllm_metal_list_models() {
    local dir="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/models}"
    local conf
    for conf in "${dir}"/*.conf; do
        [[ -e "${conf}" ]] || continue
        printf '  %s\n' "$(basename "${conf}" .conf)"
    done
}

# Pid of the running server, or empty. Treats a stale pidfile as "not running".
vllm_metal_pid() {
    [[ -f "${VLLM_METAL_PIDFILE}" ]] || return 0
    local pid
    pid="$(cat "${VLLM_METAL_PIDFILE}")"
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 0
    kill -0 "${pid}" 2> /dev/null || return 0
    printf '%s\n' "${pid}"
}

# Unified memory total in GiB. Apple Silicon has no separate VRAM; the GPU
# budget is a fraction of this.
vllm_metal_mem_gib() {
    local bytes
    bytes="$(sysctl -n hw.memsize 2> /dev/null || printf '0')"
    printf '%s\n' "$((bytes / 1073741824))"
}
