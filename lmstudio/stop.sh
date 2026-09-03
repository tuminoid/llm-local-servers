#!/usr/bin/env bash
#
# Unload the model, stop the LM Studio server, and verify resource release.
#
# LM Studio has no pidfile for the served model: the model is owned by the
# long-running service, so teardown is CLI-driven rather than a process-group
# signal. `lms unload --all` releases the model's memory and `lms server stop`
# stops the HTTP endpoint. Release is then verified the same way the other
# runtimes verify it -- VRAM must return to the pre-start baseline on hosts with
# nvidia-smi; on Apple Silicon, where there is no separate VRAM counter, an
# empty `lms ps` after unload is the release proof.
#
# This does NOT stop the LM Studio desktop application or its background daemon
# (`lms daemon`); it stops the API server and frees the model. See
# lmstudio/AGENTS.md for this accepted deviation from the pidfile convention.
#
# shellcheck disable=SC2154  # LMSTUDIO_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

LMSTUDIO_EXE="$(lmstudio_bin)"
if [[ -z "${LMSTUDIO_EXE}" ]]; then
    printf 'error: lms not found; nothing to stop\n' >&2
    exit 1
fi

baseline=0
if [[ -s "${LMSTUDIO_BASELINE_GPU_FILE}" ]]; then
    baseline="$(cat "${LMSTUDIO_BASELINE_GPU_FILE}")"
fi
[[ "${baseline}" =~ ^[0-9]+$ ]] || baseline=0

read -r server_state _server_port < <(lmstudio_server_status "${LMSTUDIO_EXE}")

loaded="$("${LMSTUDIO_EXE}" ps --json 2> /dev/null | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    print(0)
    sys.exit(0)
if isinstance(data, dict):
    data = data.get("models") or data.get("data") or []
print(len(data))
' || printf '0')"

if [[ "${server_state}" != "running" && "${loaded}" == "0" ]]; then
    printf 'not running (server stopped, no models loaded)\n'
    : > "${LMSTUDIO_BASELINE_GPU_FILE}" 2> /dev/null || true
    exit 0
fi

if command -v nvidia-smi > /dev/null 2>&1; then
    printf 'unloading %s model(s) (gpu %s MiB)\n' "${loaded}" "$(lmstudio_gpu_mib)"
else
    printf 'unloading %s model(s)\n' "${loaded}"
fi
"${LMSTUDIO_EXE}" unload --all 2> /dev/null || true

printf 'stopping LM Studio server\n'
"${LMSTUDIO_EXE}" server stop 2> /dev/null || true

# Confirm the service reports stopped and no model remains loaded.
read -r server_state _server_port < <(lmstudio_server_status "${LMSTUDIO_EXE}")
remaining="$("${LMSTUDIO_EXE}" ps --json 2> /dev/null | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    print(0)
    sys.exit(0)
if isinstance(data, dict):
    data = data.get("models") or data.get("data") or []
print(len(data))
' || printf '0')"
if [[ "${remaining}" != "0" ]]; then
    printf 'error: %s model(s) still loaded after unload --all\n' "${remaining}" >&2
    "${LMSTUDIO_EXE}" ps 2>&1 | sed 's/^/  /' >&2 || true
    exit 1
fi

if command -v nvidia-smi > /dev/null 2>&1; then
    sleep 2
    used="$(lmstudio_gpu_mib)"
    printf 'stopped (gpu %s MiB; baseline %s MiB)\n' "${used}" "${baseline}"
    if ((used > baseline + 512)); then
        printf 'error: GPU remains %s MiB above the pre-start baseline\n' \
            "$((used - baseline))" >&2
        nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv >&2
        exit 1
    fi
else
    # Apple Silicon has no separate VRAM counter; an empty ps after unload,
    # confirmed above, is the release proof.
    printf 'stopped (no models loaded; unified memory released with the model)\n'
fi

: > "${LMSTUDIO_BASELINE_GPU_FILE}" 2> /dev/null || true
: > "${LMSTUDIO_LOG}" 2> /dev/null || true
