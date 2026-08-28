#!/usr/bin/env bash
#
# Fail-closed ownership and GPU-idle checks for remote Ollama targets.
#
# Usage: preflight.sh idle|managed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

mode="${1:-}"
base="$(ollama_api_base)"

case "${mode}" in
    idle)
        if pid="$(ollama_pid)" && [[ -n "${pid}" ]]; then
            printf 'error: isolated Ollama is already running (pid %s)\n' \
                "${pid}" >&2
            exit 1
        fi
        if curl -sf --max-time 2 "${base}/api/version" > /dev/null 2>&1; then
            printf 'error: an unmanaged server already answers at %s\n' \
                "${base}" >&2
            exit 1
        fi
        if [[ "${OLLAMA_REQUIRE_EXISTING_KEY:-1}" == "1" ]]; then
            for key in "${HOME}/.ollama/id_ed25519" \
                "${HOME}/.ollama/id_ed25519.pub"; do
                if [[ ! -f "${key}" || -L "${key}" || ! -r "${key}" ]]; then
                    printf 'error: required existing regular Ollama key is unavailable: %s\n' \
                        "${key}" >&2
                    printf 'refusing startup rather than writing into ~/.ollama\n' >&2
                    exit 1
                fi
            done
        else
            printf 'preflight: one-time Ollama key creation is authorized\n'
        fi
        if ! command -v nvidia-smi > /dev/null 2>&1; then
            printf 'error: nvidia-smi is required for remote GPU preflight\n' >&2
            exit 1
        fi
        if ! compute="$(
            nvidia-smi \
                --query-compute-apps=pid,process_name,used_memory \
                --format=csv,noheader 2>&1
        )"; then
            printf 'error: failed to inspect remote GPU processes:\n%s\n' \
                "${compute}" >&2
            exit 1
        fi
        if [[ -n "${compute//[[:space:]]/}" ]]; then
            printf 'error: GPU compute workload is active; refusing Ollama start:\n' >&2
            printf '%s\n' "${compute}" >&2
            exit 1
        fi
        printf 'preflight: GPU idle and %s unclaimed\n' "${base}"
        ;;
    managed)
        pid="$(ollama_pid)"
        if [[ -z "${pid}" ]]; then
            printf 'error: isolated Ollama pidfile has no live process\n' >&2
            exit 1
        fi
        if ! curl -sf --max-time 5 "${base}/api/version" > /dev/null; then
            printf 'error: isolated Ollama pid %s is not serving at %s\n' \
                "${pid}" "${base}" >&2
            exit 1
        fi
        printf 'preflight: managed Ollama pid %s owns %s\n' "${pid}" "${base}"
        ;;
    *)
        printf 'usage: %s idle|managed\n' "$(basename "$0")" >&2
        exit 1
        ;;
esac
