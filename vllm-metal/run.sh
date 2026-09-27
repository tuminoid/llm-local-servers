#!/usr/bin/env bash
#
# Start the vLLM-Metal server detached and wait until it is serving.
#
# Usage: run.sh <model-config-name>
#
# nohup alone is not enough: it only ignores SIGHUP, and a Ctrl-C in the
# invoking shell would SIGINT the whole foreground process group. macOS ships
# no setsid, so when it is absent the launcher falls back to bash job
# control, which gives the child its own process group -- the same handle
# stop.sh signals.
#
# shellcheck disable=SC2154  # VLLM_METAL_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

# The Metal plugin runs only on Apple Silicon macOS.
if [[ "$(uname -s)/$(uname -m)" != "Darwin/arm64" ]]; then
    printf 'error: vllm-metal/ serves on macOS Apple Silicon; this host is %s/%s\n' "$(uname -s)" "$(uname -m)" >&2
    printf 'use make vllm-start on a CUDA Linux host\n' >&2
    exit 1
fi

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    vllm_metal_list_models >&2
    exit 1
fi
MODEL_CONF="$1"
READY_TIMEOUT="${VLLM_METAL_READY_TIMEOUT:-600}"

running_pid="$(vllm_metal_pid)"
if [[ -n "${running_pid}" ]]; then
    printf 'already running (pid %s); stop it first\n' "${running_pid}" >&2
    exit 1
fi

mkdir -p "${VLLM_METAL_STATE_DIR}"
: > "${VLLM_METAL_LOG}"

if command -v setsid > /dev/null 2>&1; then
    setsid nohup "${SCRIPT_DIR}/start.sh" "${MODEL_CONF}" \
        < /dev/null > "${VLLM_METAL_LOG}" 2>&1 &
else
    set -m
    nohup "${SCRIPT_DIR}/start.sh" "${MODEL_CONF}" \
        < /dev/null > "${VLLM_METAL_LOG}" 2>&1 &
    set +m
fi
launcher_pid=$!
disown || true

printf 'log: %s\n' "${VLLM_METAL_LOG}"

# Startup covers weight load and the first Metal kernel compilations.
deadline=$((SECONDS + READY_TIMEOUT))
while ((SECONDS < deadline)); do
    if grep -q 'Application startup complete' "${VLLM_METAL_LOG}" 2> /dev/null \
        && kill -0 "${launcher_pid}" 2> /dev/null; then
        printf 'ready (pid %s)\n' "$(vllm_metal_pid)"
        grep -oE '(GPU|CPU) KV cache size: [0-9,]+ tokens' "${VLLM_METAL_LOG}" | tail -1 || true
        exit 0
    fi
    if grep -qE 'Engine core initialization failed|OutOfMemoryError|MemoryError' \
        "${VLLM_METAL_LOG}" 2> /dev/null; then
        printf 'startup failed; last error:\n' >&2
        grep -oE '(OutOfMemoryError|MemoryError|RuntimeError|ValueError): .*' \
            "${VLLM_METAL_LOG}" | sort -u | head -3 >&2
        exit 1
    fi
    if ! kill -0 "${launcher_pid}" 2> /dev/null; then
        printf 'startup failed: process exited before readiness; last log lines:\n' >&2
        tail -20 "${VLLM_METAL_LOG}" >&2
        exit 1
    fi
    sleep 5
done

printf 'timed out after %ss waiting for startup; see %s\n' \
    "${READY_TIMEOUT}" "${VLLM_METAL_LOG}" >&2
exit 1
