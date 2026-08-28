#!/usr/bin/env bash
#
# Start Ollama detached and wait for its API.
#
# Usage: run.sh <model-config-name>
#
# shellcheck disable=SC2154  # OLLAMA_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    ollama_list_models >&2
    exit 1
fi
MODEL_CONF="$1"
READY_TIMEOUT="${OLLAMA_READY_TIMEOUT:-120}"
base="$(ollama_api_base)"

running_pid="$(ollama_pid)"
if [[ -n "${running_pid}" ]]; then
    printf 'already running (pid %s); stop it first\n' "${running_pid}" >&2
    exit 1
fi
if curl -sf --max-time 2 "${base}/api/version" > /dev/null 2>&1; then
    printf 'error: an unmanaged Ollama server already answers at %s\n' "${base}" >&2
    exit 1
fi

mkdir -p "${OLLAMA_STATE_DIR}"
ollama_gpu_mib > "${OLLAMA_BASELINE_GPU_FILE}"
: > "${OLLAMA_LOG}"

if command -v setsid > /dev/null 2>&1; then
    setsid nohup "${SCRIPT_DIR}/start.sh" "${MODEL_CONF}" \
        < /dev/null > "${OLLAMA_LOG}" 2>&1 &
else
    # macOS ships no setsid. Job control puts the child in its own process
    # group, which is the handle stop.sh signals; nohup still covers SIGHUP.
    set -m
    nohup "${SCRIPT_DIR}/start.sh" "${MODEL_CONF}" \
        < /dev/null > "${OLLAMA_LOG}" 2>&1 &
    set +m
fi
disown || true

printf 'log: %s\n' "${OLLAMA_LOG}"
deadline=$((SECONDS + READY_TIMEOUT))
while ((SECONDS < deadline)); do
    if version="$(curl -sf --max-time 2 "${base}/api/version" 2> /dev/null)"; then
        printf 'ready (pid %s, api %s, %s)\n' \
            "$(ollama_pid)" "${base}" "${version}"
        exit 0
    fi
    if [[ -z "$(ollama_pid)" ]] && [[ -s "${OLLAMA_LOG}" ]]; then
        printf 'startup failed; log tail:\n' >&2
        tail -20 "${OLLAMA_LOG}" >&2
        exit 1
    fi
    sleep 2
done

printf 'timed out after %ss; see %s\n' "${READY_TIMEOUT}" "${OLLAMA_LOG}" >&2
exit 1
