#!/usr/bin/env bash
#
# Download a model's pinned revision into the managed models directory.
#
# Usage: pull.sh <model-config-name>
#
# Uses the authenticated hf CLI with an explicit local directory. The HF
# cache is treated as read-only and never served from: an explicit directory
# makes the served bytes inspectable and survives cache eviction.
#
# shellcheck disable=SC2154  # VLLM_METAL_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    vllm_metal_list_models >&2
    exit 1
fi
MODEL_CONF="$1"
CONF_FILE="${SCRIPT_DIR}/models/${MODEL_CONF}.conf"
if [[ ! -f "${CONF_FILE}" ]]; then
    printf 'error: no such model config: %s\n' "${CONF_FILE}" >&2
    exit 1
fi

VLLM_MODEL_REPO="${VLLM_MODEL_REPO:-}"
VLLM_MODEL_REVISION="${VLLM_MODEL_REVISION:-}"
VLLM_MODEL_INCLUDE="${VLLM_MODEL_INCLUDE:-}"
# shellcheck source=models/ornith1.5-35b-a3b-4bit.conf disable=SC1091
source "${CONF_FILE}"

for var in VLLM_MODEL_REPO VLLM_MODEL_REVISION; do
    if [[ -z "${!var}" ]]; then
        printf 'error: %s is empty; check %s\n' "${var}" "${CONF_FILE}" >&2
        exit 1
    fi
done

command -v hf > /dev/null 2>&1 || {
    printf 'error: the hf CLI is required (and must be logged in)\n' >&2
    exit 1
}

MODEL_DIR="${VLLM_METAL_MODELS_DIR}/${MODEL_CONF}"
mkdir -p "${MODEL_DIR}"

printf 'downloading %s@%s to %s\n' \
    "${VLLM_MODEL_REPO}" "${VLLM_MODEL_REVISION}" "${MODEL_DIR}"
# VLLM_MODEL_INCLUDE (optional, space-separated hf glob patterns) limits the
# download to the files that constitute this operating point. Multi-quant
# repos ship every quantization in one repo; without the filter a 15 GiB
# serving artifact costs the full 80+ GiB repo. Patterns are matched against
# the whole relative path, so anchor them (e.g. "model-*", "config.json") --
# a bare "*.safetensors" would pull every subfolder quant too. Unset
# downloads the whole repo, the prior behavior.
download_args=("${VLLM_MODEL_REPO}"
    --revision "${VLLM_MODEL_REVISION}"
    --local-dir "${MODEL_DIR}")
if [[ -n "${VLLM_MODEL_INCLUDE}" ]]; then
    # One --include per pattern: the flag takes a single TEXT argument, and
    # extra tokens would be parsed as positional filenames instead.
    for pattern in ${VLLM_MODEL_INCLUDE}; do
        download_args+=(--include "${pattern}")
    done
fi
hf download "${download_args[@]}"

if [[ ! -f "${MODEL_DIR}/config.json" ]]; then
    printf 'error: download completed but %s/config.json is missing\n' \
        "${MODEL_DIR}" >&2
    exit 1
fi
printf 'model ready at %s\n' "${MODEL_DIR}"
