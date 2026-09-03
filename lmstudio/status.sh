#!/usr/bin/env bash
#
# Show LM Studio server status, loaded model identity, allocation, and API.
#
# shellcheck disable=SC2154  # LMSTUDIO_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

LMSTUDIO_EXE="$(lmstudio_bin)"
base="$(lmstudio_api_base)"

if [[ -z "${LMSTUDIO_EXE}" ]]; then
    printf 'server:   lms not found (run make lmstudio-install)\n'
    printf 'models:\n'
    lmstudio_list_models "${SCRIPT_DIR}/models"
    exit 0
fi

read -r server_state server_port < <(lmstudio_server_status "${LMSTUDIO_EXE}")

if [[ "${server_state}" != "running" ]]; then
    printf 'server:   not running\n'
    printf 'models:\n'
    lmstudio_list_models "${SCRIPT_DIR}/models"
    exit 0
fi

printf 'server:   running (port %s)\n' "${server_port:-${LMSTUDIO_PORT}}"
printf 'api:      %s\n' "${base}"
printf 'log:      %s\n' "${LMSTUDIO_LOG}"

if command -v nvidia-smi > /dev/null 2>&1; then
    printf 'gpu:      %s MiB used\n' "$(lmstudio_gpu_mib)"
fi
printf 'ram:      '
if command -v free > /dev/null 2>&1; then
    free -h | awk '/^Mem:/ {printf "%s used / %s total, %s available\n", $3, $2, $7}'
elif command -v top > /dev/null 2>&1; then
    top -l 1 -s 0 -n 0 2> /dev/null | awk -F': ' '/PhysMem/ {print $2}'
else
    printf 'unknown\n'
fi

# The launch profile this server recorded, mirroring the other runtimes'
# config:/host: lines.
if [[ -f "${LMSTUDIO_LOG}" ]]; then
    grep -E '^(config|host):' "${LMSTUDIO_LOG}" | head -2 || true
fi

# Loaded model identity from lms ps.
if ps_json="$("${LMSTUDIO_EXE}" ps --json 2> /dev/null)"; then
    printf '%s' "${ps_json}" | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    print("model:    ps output not parseable")
    sys.exit(0)
if isinstance(data, dict):
    data = data.get("models") or data.get("data") or []
if not data:
    print("model:    none loaded")
for model in data:
    ident = model.get("identifier") or model.get("modelKey") or model.get("key") or "unknown"
    path = model.get("path") or "unknown"
    arch = model.get("architecture") or (model.get("details") or {}).get("architecture") or "unknown"
    fmt = model.get("format") or model.get("type") or "unknown"
    quant = model.get("quantization")
    if isinstance(quant, dict):
        quant = quant.get("name") or quant.get("level")
    quant = quant or ""
    ctx = model.get("contextLength") or model.get("context_length") or model.get("maxContextLength") or 0
    size = model.get("sizeBytes") or model.get("size") or 0
    try:
        size_gib = f"{int(size) / 2**30:.2f} GiB"
    except (TypeError, ValueError):
        size_gib = str(size)
    print(f"model:    {ident}")
    print(f"path:     {path}")
    print(f"artifact: {fmt} {arch} {quant}".rstrip())
    if ctx:
        print(f"context:  {int(ctx):,}")
    print(f"size:     {size_gib}")
'
else
    printf 'model:    lms ps unavailable\n'
fi

# Live confirmation the OpenAI endpoint is answering.
if models="$(curl -sf --max-time 5 "${base}/v1/models" 2> /dev/null)"; then
    printf '%s' "${models}" | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin).get("data", [])
except (json.JSONDecodeError, ValueError):
    data = []
for model in data:
    print("serving:  " + str(model.get("id", "unknown")))
if not data:
    print("serving:  no models on /v1/models")
'
else
    printf 'serving:  no response from %s\n' "${base}"
fi
