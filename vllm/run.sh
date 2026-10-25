#!/usr/bin/env bash
#
# Start the vLLM server detached and wait until it is serving.
#
# Usage: run.sh <model-config-name>
#
# nohup alone is not enough: it only ignores SIGHUP. A Ctrl-C in the invoking
# shell sends SIGINT to the whole foreground process group, which includes a
# merely-backgrounded server, and shuts it down mid-startup. setsid puts the
# server in its own session and process group, out of reach of the caller's
# terminal signals.
#
# shellcheck disable=SC2154  # VLLM_* paths are defined in lib.sh, which the
# lint wrapper cannot follow (it runs without -x), so it sees them as unassigned.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

# This server is CUDA vLLM, Linux only. On macOS it would die at setsid.
if [[ "$(uname -s)" != "Linux" ]]; then
    printf 'error: vllm/ serves CUDA vLLM on Linux; this host is %s\n' "$(uname -s)" >&2
    printf 'use make vllm-remote-start for the GPU host, or make vllm-metal-start on Apple Silicon\n' >&2
    exit 1
fi
# The launcher derives its whole host profile from nvidia-smi; without it the
# profile would silently be that of an unknown, unsupported GPU.
for tool in nvidia-smi setsid; do
    if ! command -v "${tool}" > /dev/null 2>&1; then
        printf 'error: %s is required to serve CUDA vLLM\n' "${tool}" >&2
        exit 1
    fi
done

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    vllm_list_models >&2
    exit 1
fi
MODEL_CONF="$1"
READY_TIMEOUT="${VLLM_READY_TIMEOUT:-600}"

running_pid="$(vllm_pid)"
if [[ -n "${running_pid}" ]]; then
    printf 'already running (pid %s); stop.sh first\n' "${running_pid}" >&2
    exit 1
fi

mkdir -p "${VLLM_STATE_DIR}"
: > "${VLLM_LOG}"

setsid nohup "${SCRIPT_DIR}/start.sh" "${MODEL_CONF}" < /dev/null > "${VLLM_LOG}" 2>&1 &
launcher_pid=$!
disown || true

printf 'log: %s\n' "${VLLM_LOG}"

# Startup is slow: weight load, torch.compile, cudagraph capture, and on the
# first FlashInfer run a JIT compile of the attention kernels.
deadline=$((SECONDS + READY_TIMEOUT))
while ((SECONDS < deadline)); do
    if grep -q 'Application startup complete' "${VLLM_LOG}" 2> /dev/null \
        && kill -0 "${launcher_pid}" 2> /dev/null; then
        printf 'ready (pid %s, gpu %s MiB)\n' "$(vllm_pid)" "$(vllm_gpu_mib)"
        grep -oE 'GPU KV cache size: [0-9,]+ tokens' "${VLLM_LOG}" | tail -1 || true
        exit 0
    fi
    if grep -qE 'Engine core initialization failed|OutOfMemoryError' "${VLLM_LOG}" 2> /dev/null; then
        printf 'startup failed; last error:\n' >&2
        grep -oE '(OutOfMemoryError|RuntimeError|ValueError): .*' "${VLLM_LOG}" |
            sort -u | head -3 >&2
        exit 1
    fi
    if ! kill -0 "${launcher_pid}" 2> /dev/null; then
        printf 'startup failed: process exited before readiness; last log lines:\n' >&2
        tail -20 "${VLLM_LOG}" >&2
        exit 1
    fi
    sleep 5
done

printf 'timed out after %ss waiting for startup; see %s\n' "${READY_TIMEOUT}" "${VLLM_LOG}" >&2
exit 1
