#!/usr/bin/env bash
#
# Show vLLM-Metal status: process, memory, KV sizing, NAX evidence, and a
# live /v1/models probe.
#
# shellcheck disable=SC2154  # VLLM_METAL_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

pid="$(vllm_metal_pid)"
base="http://${VLLM_HOST:-127.0.0.1}:${VLLM_PORT:-8021}"

if [[ -z "${pid}" ]]; then
    printf 'server:   not running\n'
    printf 'models:\n'
    vllm_metal_list_models "${SCRIPT_DIR}/models"
    exit 0
fi

printf 'server:   running (pid %s)\n' "${pid}"
printf 'api:      %s\n' "${base}"
printf 'log:      %s\n' "${VLLM_METAL_LOG}"

if [[ -f "${VLLM_METAL_LOG}" ]]; then
    grep '^host:' "${VLLM_METAL_LOG}" | head -1 || true
    grep -oE '(GPU|CPU) KV cache size: [0-9,]+ tokens' "${VLLM_METAL_LOG}" | tail -1 |
        sed -E 's/(GPU|CPU) KV cache size: /kv cache: /' || true
    grep -oE 'Maximum concurrency for [0-9,]+ tokens per request: [0-9.]+x' \
        "${VLLM_METAL_LOG}" | tail -1 | sed 's/^/limit:    /' || true
    # NAX prefill is automatic on M5; surface whatever the plugin logs about
    # it (excluding our own host: line), so an unaccelerated baseline is
    # visible.
    nax_line="$(grep -i 'nax' "${VLLM_METAL_LOG}" | grep -v '^host:' | head -1 || true)"
    if [[ -n "${nax_line}" ]]; then
        printf 'nax:      %s\n' "${nax_line}"
    else
        printf 'nax:      no log evidence yet\n'
    fi
fi

if models="$(curl -sf --max-time 5 "${base}/v1/models" 2> /dev/null)"; then
    printf '%s' "${models}" | python3 -c '
import json
import sys

for model in json.load(sys.stdin).get("data", []):
    print("model:    " + str(model.get("id", "unknown")))
'
else
    printf 'serving:  no response from %s\n' "${base}"
fi

printf 'processes:\n'
ps -o pid=,ppid=,rss=,pcpu=,comm= -g "${pid}" 2> /dev/null |
    awk '{rss += $3; printf "  pid %-8s ppid %-8s rss %7.1f MiB cpu %5s%% %s\n", $1, $2, $3 / 1024, $4, $5}
         END {printf "  process RSS total: %.2f GiB\n", rss / 1048576}' || true

# Phys footprint includes Metal and IOSurface allocations, which RSS misses
# on unified memory.
if command -v footprint > /dev/null 2>&1; then
    printf 'footprint:\n'
    for member in $(ps -o pid= -g "${pid}" 2> /dev/null); do
        footprint "${member}" 2> /dev/null |
            grep -m1 'Footprint:' |
            sed -E 's/^/  /; s/[[:space:]]+/ /g' || true
    done
fi
