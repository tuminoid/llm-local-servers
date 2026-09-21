#!/usr/bin/env bash
#
# Run the configured Ollama server in the foreground.
#
# Usage: start.sh <model-config-name>
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
CONF_FILE="${SCRIPT_DIR}/models/${MODEL_CONF}.conf"

if [[ ! -f "${CONF_FILE}" ]]; then
    printf 'error: no such model config: %s\n' "${CONF_FILE}" >&2
    printf 'available:\n' >&2
    ollama_list_models >&2
    exit 1
fi

OLLAMA_MODEL="${OLLAMA_MODEL:-}"
OLLAMA_MIN_VERSION="${OLLAMA_MIN_VERSION:-}"
OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-}"
OLLAMA_KV_CACHE_TYPE="${OLLAMA_KV_CACHE_TYPE:-}"
OLLAMA_RUNTIME_VERSION="${OLLAMA_RUNTIME_VERSION:-}"

# shellcheck source=models/qwen3.8-27b.conf disable=SC1091
source "${CONF_FILE}"

# Per-profile managed runtime pin. lib.sh defaults OLLAMA_VERSION before the
# conf is read, so a profile that needs a newer runtime than the fleet default
# declares OLLAMA_RUNTIME_VERSION; an explicit OLLAMA_RUNTIME_VERSION in the
# environment still wins over the conf through the usual ${VAR:-default}
# pattern. The binary and min-version checks below then resolve against the
# selected runtime.
if [[ -n "${OLLAMA_RUNTIME_VERSION}" ]]; then
    # shellcheck disable=SC2034  # read by ollama_bin() in the sourced lib.sh
    OLLAMA_VERSION="${OLLAMA_RUNTIME_VERSION}"
fi

OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}"
OLLAMA_FLASH_ATTENTION="${OLLAMA_FLASH_ATTENTION:-1}"
OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}"
OLLAMA_MAX_QUEUE="${OLLAMA_MAX_QUEUE:-64}"
OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:--1}"
OLLAMA_NO_CLOUD="${OLLAMA_NO_CLOUD:-1}"
OLLAMA_LOAD_TIMEOUT="${OLLAMA_LOAD_TIMEOUT:-30m}"
LLAMA_ARG_FIT="${LLAMA_ARG_FIT:-1}"
LLAMA_ARG_FIT_TARGET="${LLAMA_ARG_FIT_TARGET:-1024}"

for var in OLLAMA_MODEL OLLAMA_MIN_VERSION OLLAMA_CONTEXT_LENGTH OLLAMA_KV_CACHE_TYPE; do
    if [[ -z "${!var}" ]]; then
        printf 'error: %s is empty; check %s\n' "${var}" "${CONF_FILE}" >&2
        exit 1
    fi
done
if [[ ! "${OLLAMA_CONTEXT_LENGTH}" =~ ^[1-9][0-9]*$ ]] \
    || [[ ! "${OLLAMA_NUM_PARALLEL}" =~ ^[1-9][0-9]*$ ]]; then
    printf 'error: context and parallelism must be positive integers\n' >&2
    exit 1
fi
case "${OLLAMA_KV_CACHE_TYPE}" in
    f16 | q8_0 | q4_0) ;;
    mlx-native)
        # Safetensors artifacts take the MLX runner, which keeps KV at model
        # precision and reads no cache-type environment. Documentation value;
        # never forwarded to the server.
        ;;
    *)
        printf 'error: unsupported OLLAMA_KV_CACHE_TYPE: %s\n' \
            "${OLLAMA_KV_CACHE_TYPE}" >&2
        exit 1
        ;;
esac

if [[ -n "$(ollama_pid)" ]]; then
    printf 'error: Ollama is already running under this launcher\n' >&2
    exit 1
fi
if command -v systemctl > /dev/null 2>&1 \
    && systemctl is-active --quiet ollama.service 2> /dev/null; then
    printf 'error: systemd ollama.service is active; refusing to compete with it\n' >&2
    exit 1
fi
if [[ "${OLLAMA_REQUIRE_EXISTING_KEY:-0}" == "1" ]]; then
    for key in "${HOME}/.ollama/id_ed25519" \
        "${HOME}/.ollama/id_ed25519.pub"; do
        if [[ ! -f "${key}" || -L "${key}" || ! -r "${key}" ]]; then
            printf 'error: required existing regular Ollama key is unavailable: %s\n' \
                "${key}" >&2
            printf 'refusing startup rather than writing into ~/.ollama\n' >&2
            exit 1
        fi
    done
fi

OLLAMA_EXE="$(ollama_bin)"
if [[ -z "${OLLAMA_EXE}" ]]; then
    printf 'error: Ollama not found; run make ollama-install\n' >&2
    exit 1
fi
actual_version="$(ollama_version "${OLLAMA_EXE}")"
if [[ -z "${actual_version}" ]] \
    || ! ollama_version_at_least "${actual_version}" "${OLLAMA_MIN_VERSION}"; then
    printf 'error: %s needs Ollama >= %s; found %s at %s\n' \
        "${OLLAMA_MODEL}" "${OLLAMA_MIN_VERSION}" \
        "${actual_version:-unknown}" "${OLLAMA_EXE}" >&2
    printf 'run: make ollama-install\n' >&2
    exit 1
fi
# Pin guard: the binary must be the pinned release, not merely a new enough
# one. The managed path encodes the version, but an explicit OLLAMA_BIN (the
# remote fixed environment) can name a different runtime than the effective
# OLLAMA_VERSION after the conf's OLLAMA_RUNTIME_VERSION applied above.
if [[ "${actual_version}" != "${OLLAMA_VERSION}" ]]; then
    printf 'error: %s is Ollama %s, the pin for %s is %s\n' \
        "${OLLAMA_EXE}" "${actual_version}" "${OLLAMA_MODEL}" "${OLLAMA_VERSION}" >&2
    printf 'pass OLLAMA_VERSION=%s (and the matching OLLAMA_BIN remotely), or make ollama-install\n' \
        "${OLLAMA_VERSION}" >&2
    exit 1
fi

export OLLAMA_HOST OLLAMA_CONTEXT_LENGTH OLLAMA_NUM_PARALLEL
export OLLAMA_FLASH_ATTENTION OLLAMA_MAX_LOADED_MODELS
export OLLAMA_MAX_QUEUE OLLAMA_KEEP_ALIVE OLLAMA_NO_CLOUD OLLAMA_LOAD_TIMEOUT
export LLAMA_ARG_FIT LLAMA_ARG_FIT_TARGET
if [[ "${OLLAMA_KV_CACHE_TYPE}" != "mlx-native" ]]; then
    export OLLAMA_KV_CACHE_TYPE
fi

printf 'config: model=%s context=%s parallel=%s aggregate=%s kv=%s\n' \
    "${OLLAMA_MODEL}" "${OLLAMA_CONTEXT_LENGTH}" "${OLLAMA_NUM_PARALLEL}" \
    "$((OLLAMA_CONTEXT_LENGTH * OLLAMA_NUM_PARALLEL))" "${OLLAMA_KV_CACHE_TYPE}"
printf 'config: host=%s flash_attention=%s fit_target=%sMiB version=%s\n' \
    "${OLLAMA_HOST}" "${OLLAMA_FLASH_ATTENTION}" "${LLAMA_ARG_FIT_TARGET}" \
    "${actual_version}"
printf 'config: binary=%s models=%s state=%s\n' \
    "${OLLAMA_EXE}" "${OLLAMA_MODELS:-default}" "${OLLAMA_STATE_DIR}"

mkdir -p "${OLLAMA_STATE_DIR}"
printf '%s\n' "$$" > "${OLLAMA_PIDFILE}"
exec "${OLLAMA_EXE}" serve
