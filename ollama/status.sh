#!/usr/bin/env bash
#
# Show Ollama process, allocation, CPU/GPU split, and API status.
#
# shellcheck disable=SC2154  # OLLAMA_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

pid="$(ollama_pid)"
base="$(ollama_api_base)"

if [[ -z "${pid}" ]]; then
    if curl -sf --max-time 2 "${base}/api/version" > /dev/null 2>&1; then
        printf 'server:   unmanaged process answering at %s\n' "${base}"
        exit 1
    fi
    printf 'server:   not running\n'
    printf 'models:\n'
    ollama_list_models
    exit 0
fi

printf 'server:   running (pid %s)\n' "${pid}"
printf 'api:      %s\n' "${base}"
if command -v nvidia-smi > /dev/null 2>&1; then
    printf 'gpu:      %s MiB used\n' "$(ollama_gpu_mib)"
fi
printf 'ram:      '
if command -v free > /dev/null 2>&1; then
    free -h | awk '/^Mem:/ {printf "%s used / %s total, %s available\n", $3, $2, $7}'
else
    top -l 1 -s 0 -n 0 2> /dev/null | awk -F': ' '/PhysMem/ {print $2}'
fi
printf 'log:      %s\n' "${OLLAMA_LOG}"

if [[ -f "${OLLAMA_LOG}" ]]; then
    grep '^config:' "${OLLAMA_LOG}" | head -3 || true
    if grep -q 'starting mlx runner subprocess' "${OLLAMA_LOG}"; then
        printf 'runner:   mlx'
        engine="$(grep 'MLX engine initialized' "${OLLAMA_LOG}" | tail -1)"
        if [[ -n "${engine}" ]]; then
            mlx_version="$(grep -oE 'MLX version"?=[^ ]+' <<< "${engine}" |
                tail -1 | sed 's/.*=//')"
            device="$(grep -oE 'device=[a-z]+' <<< "${engine}" | tail -1)"
            printf ' (MLX %s, %s)' \
                "${mlx_version:-version unknown}" "${device:-device unknown}"
        fi
        printf '\n'
        # Debug-level line; present only under OLLAMA_DEBUG=1. The loaded
        # variant is the Metal 4 / M5 evidence.
        variant="$(grep -oE 'mlx_metal_v[0-9]+' "${OLLAMA_LOG}" | tail -1 || true)"
        [[ -n "${variant}" ]] && printf 'backend:  %s\n' "${variant}"
        printf 'jobs:     1 effective (MLX runner serializes requests)\n'
    elif grep -q 'starting llama-server' "${OLLAMA_LOG}"; then
        printf 'runner:   llama.cpp\n'
        if grep -q 'model architecture does not currently support parallel requests' \
            "${OLLAMA_LOG}"; then
            printf 'jobs:     1 effective (Ollama qwen35 parallel guard)\n'
        elif jobs="$(grep 'starting llama-server' "${OLLAMA_LOG}" |
            grep -oE -- '-np [0-9]+' | tail -1 | awk '{print $2}')"; then
            [[ -n "${jobs}" ]] && printf 'jobs:     %s effective\n' "${jobs}"
        fi
    fi
fi

if response="$(curl -sf --max-time 5 "${base}/api/ps" 2> /dev/null)"; then
    printf '%s' "${response}" | python3 -c '
import json
import sys

models = json.load(sys.stdin).get("models", [])
if not models:
    print("model:    none loaded")
for model in models:
    total = model.get("size", 0)
    vram = model.get("size_vram", 0)
    cpu = max(total - vram, 0)
    gpu_pct = (100 * vram / total) if total else 0
    cpu_pct = 100 - gpu_pct if total else 0
    name = model.get("name", "unknown")
    digest = model.get("digest") or "unknown"
    context = model.get("context_length", 0)
    details = model.get("details") or {}
    artifact_format = details.get("format") or "unknown"
    quantization = details.get("quantization_level") or "unknown"
    print(f"model:    {name}")
    print(f"digest:   {digest}")
    print(f"artifact: {artifact_format} {quantization}")
    print(
        f"split:    {cpu_pct:.1f}% CPU / {gpu_pct:.1f}% GPU "
        f"({cpu / 2**30:.2f} / {vram / 2**30:.2f} GiB)"
    )
    print(
        f"resident: {total / 2**30:.2f} GiB, "
        f"context {context:,}"
    )
'
else
    printf 'serving:  no response\n'
fi

if [[ -f "${OLLAMA_LOG}" ]]; then
    layer_line="$(
        grep -Ei 'offload|layers to GPU|memory weights|memory required' "${OLLAMA_LOG}" |
            tail -1 || true
    )"
    [[ -n "${layer_line}" ]] && printf 'offload:  %s\n' "${layer_line}"
fi

printf 'processes:\n'
ps -o pid=,ppid=,rss=,pcpu=,comm= -g "${pid}" 2> /dev/null |
    awk '{rss += $3; printf "  pid %-8s ppid %-8s rss %7.1f MiB cpu %5s%% %s\n", $1, $2, $3 / 1024, $4, $5}
         END {printf "  process RSS total: %.2f GiB\n", rss / 1048576}' || true

# Unified-memory hosts have no nvidia-smi; phys footprint is the measured
# process-owned total including Metal allocations.
if command -v footprint > /dev/null 2>&1; then
    printf 'footprint:\n'
    for member in $(ps -o pid= -g "${pid}" 2> /dev/null); do
        footprint "${member}" 2> /dev/null |
            grep -m1 'Footprint:' |
            sed -E 's/^/  /; s/[[:space:]]+/ /g' || true
    done
fi
