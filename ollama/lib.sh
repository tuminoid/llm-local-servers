#!/usr/bin/env bash
#
# Shared paths and helpers for the Ollama server scripts. Sourced, not run.

OLLAMA_STATE_DIR="${OLLAMA_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/ollama}"
OLLAMA_PIDFILE="${OLLAMA_PIDFILE:-${OLLAMA_STATE_DIR}/server.pid}"
OLLAMA_LOG="${OLLAMA_LOG:-${OLLAMA_STATE_DIR}/server.log}"
OLLAMA_BASELINE_GPU_FILE="${OLLAMA_BASELINE_GPU_FILE:-${OLLAMA_STATE_DIR}/gpu-baseline-mib}"
OLLAMA_RUNTIME_ROOT="${OLLAMA_RUNTIME_ROOT:-${XDG_DATA_HOME:-${HOME}/.local/share}/ollama/runtime}"
# The managed release is the root Makefile's OLLAMA_VERSION; every make
# target and the remote fixed environment pass it.
OLLAMA_VERSION="${OLLAMA_VERSION:?set by the root Makefile}"

ollama_bin() {
    if [[ -n "${OLLAMA_BIN:-}" ]]; then
        [[ -x "${OLLAMA_BIN}" ]] && printf '%s\n' "${OLLAMA_BIN}"
        return 0
    fi

    local managed="${OLLAMA_RUNTIME_ROOT}/v${OLLAMA_VERSION}/bin/ollama"
    if [[ -x "${managed}" ]]; then
        printf '%s\n' "${managed}"
        return 0
    fi

    command -v ollama 2> /dev/null || true
}

ollama_version() {
    local executable="$1"
    "${executable}" --version 2>&1 |
        grep -oE '[0-9]+\.[0-9]+\.[0-9]+' |
        head -1
}

ollama_version_at_least() {
    local actual="$1"
    local required="$2"
    [[ "$(printf '%s\n%s\n' "${required}" "${actual}" | sort -V | head -1)" == "${required}" ]]
}

ollama_pid() {
    [[ -s "${OLLAMA_PIDFILE}" ]] || return 0
    local pid
    pid="$(cat "${OLLAMA_PIDFILE}")"
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 0
    kill -0 "${pid}" 2> /dev/null || return 0
    printf '%s\n' "${pid}"
}

ollama_gpu_mib() {
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2> /dev/null |
        awk '{sum += $1} END {print sum + 0}' || true
}

ollama_api_base() {
    local host="${OLLAMA_HOST:-127.0.0.1:11434}"
    case "${host}" in
        http://* | https://*) printf '%s\n' "${host%/}" ;;
        *) printf 'http://%s\n' "${host%/}" ;;
    esac
}

ollama_list_models() {
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local conf
    for conf in "${here}/models/"*.conf; do
        [[ -e "${conf}" ]] || continue
        printf '  %s\n' "$(basename "${conf}" .conf)"
    done
}
