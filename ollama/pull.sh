#!/usr/bin/env bash
#
# Pull the configured model through the running Ollama server.
#
# Usage: pull.sh <model-config-name>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    exit 1
fi
CONF_FILE="${SCRIPT_DIR}/models/${1}.conf"
if [[ ! -f "${CONF_FILE}" ]]; then
    printf 'error: no such model config: %s\n' "${CONF_FILE}" >&2
    exit 1
fi

OLLAMA_MODEL="${OLLAMA_MODEL:-}"
# shellcheck source=models/qwen3.8-27b.conf disable=SC1091
source "${CONF_FILE}"

base="$(ollama_api_base)"
managed_pid="$(ollama_pid)"
if [[ -z "${managed_pid}" ]]; then
    printf 'error: no pidfile-owned Ollama server is running at %s\n' \
        "${base}" >&2
    exit 1
fi
if ! curl -sf --max-time 5 "${base}/api/version" > /dev/null; then
    printf 'error: managed Ollama pid %s is not serving at %s\n' \
        "${managed_pid}" "${base}" >&2
    exit 1
fi

OLLAMA_EXE="$(ollama_bin)"
if [[ -z "${OLLAMA_EXE}" ]]; then
    printf 'error: Ollama client not found; run make ollama-install\n' >&2
    exit 1
fi

export OLLAMA_HOST
"${OLLAMA_EXE}" pull "${OLLAMA_MODEL}"
