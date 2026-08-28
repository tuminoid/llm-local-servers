#!/usr/bin/env bash
#
# Show vLLM server status: process, GPU use, served model, KV cache sizing.
#
# shellcheck disable=SC2154  # VLLM_* paths are defined in lib.sh, which the
# lint wrapper cannot follow (it runs without -x), so it sees them as unassigned.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

pid="$(vllm_pid)"

if [[ -z "${pid}" ]]; then
    printf 'server:   not running\n'
    printf 'models:\n'
    vllm_list_models "${SCRIPT_DIR}/models"
    exit 0
fi

printf 'server:   running (pid %s)\n' "${pid}"
printf 'gpu:      %s MiB\n' "$(vllm_gpu_mib)"
printf 'log:      %s\n' "${VLLM_LOG}"

if [[ -f "${VLLM_LOG}" ]]; then
    grep '^starting ' "${VLLM_LOG}" | head -1 |
        sed 's/^starting /model:    /' || true
    # Two spellings, because MLA and dense models log this differently:
    # dense says "Using AttentionBackendEnum.FLASH_ATTN backend." while MLA
    # says "Using TRITON_MLA attention backend out of potential backends: ...".
    # Matching only the first silently drops the line for every MLA model.
    grep -oE 'Using AttentionBackendEnum\.[A-Z_]+|Using [A-Z_]+ attention backend' "${VLLM_LOG}" |
        tail -1 |
        sed -e 's/Using AttentionBackendEnum\./backend:  /' \
            -e 's/Using \([A-Z_]*\) attention backend/backend:  \1/' || true
    grep -oE 'GPU KV cache size: [0-9,]+ tokens' "${VLLM_LOG}" | tail -1 |
        sed 's/GPU KV cache size: /kv cache: /' || true
    grep -oE 'Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x' "${VLLM_LOG}" |
        tail -1 | sed 's/^/limit:    /' || true
fi

# Confirm it actually answers, not just that the process exists.
host="${VLLM_HOST:-127.0.0.1}"
port="${VLLM_PORT:-8000}"
if served="$(curl -sf --max-time 5 "http://${host}:${port}/v1/models" 2> /dev/null)"; then
    # Parse properly rather than grepping for "id": the response nests a
    # permission object that also carries an id, and a regex picks up that one.
    printf 'serving:  %s\n' "$(printf '%s' "${served}" |
        python3 -c 'import json,sys; print(",".join(m["id"] for m in json.load(sys.stdin)["data"]))')"
else
    printf 'serving:  no response on http://%s:%s\n' "${host}" "${port}"
fi
