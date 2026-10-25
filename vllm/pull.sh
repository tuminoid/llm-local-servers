#!/usr/bin/env bash
#
# Download a model config's pinned Hub artifacts into the Hugging Face cache.
#
# Usage: pull.sh <model-config-name>
#
# start.sh serves them offline, so this is the only step that downloads: the
# model at its revision and, when the conf names one, the speculative drafter
# at its own. Gated repos need `hf auth login` and accepted terms.
#
# shellcheck disable=SC2154  # VLLM_* paths are defined in lib.sh, which the
# lint wrapper cannot follow (it runs without -x), so it sees them as unassigned.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    vllm_list_models >&2
    exit 1
fi
CONF_FILE="${SCRIPT_DIR}/models/${1}.conf"
if [[ ! -f "${CONF_FILE}" ]]; then
    printf 'error: no such model config: %s\n' "${CONF_FILE}" >&2
    exit 1
fi

VLLM_MODEL="${VLLM_MODEL:-}"
VLLM_MODEL_REVISION="${VLLM_MODEL_REVISION:-}"
VLLM_SPECULATIVE_CONFIG="${VLLM_SPECULATIVE_CONFIG:-}"
# shellcheck source=models/qwen3.6-35b-a3b-awq.conf disable=SC1091
source "${CONF_FILE}"

if [[ -z "${VLLM_MODEL}" || ! "${VLLM_MODEL_REVISION}" =~ ^[0-9a-f]{40}$ ]]; then
    printf 'error: %s needs VLLM_MODEL and a 40-character VLLM_MODEL_REVISION\n' "${CONF_FILE}" >&2
    exit 1
fi

HF="$(vllm_hf)"
if [[ -z "${HF}" ]]; then
    printf 'error: no hf CLI on PATH and no managed venv at %s; install first\n' "${VLLM_VENV}" >&2
    exit 1
fi

artifacts="$(vllm_artifacts "${VLLM_MODEL}" "${VLLM_MODEL_REVISION}" "${VLLM_SPECULATIVE_CONFIG}")"
while read -r repo revision; do
    printf 'downloading %s@%s\n' "${repo}" "${revision}"
    "${HF}" download "${repo}" --revision "${revision}" > /dev/null
    if [[ ! -d "$(vllm_snapshot "${repo}" "${revision}")" ]]; then
        printf 'error: download finished but %s is missing\n' "$(vllm_snapshot "${repo}" "${revision}")" >&2
        exit 1
    fi
done <<< "${artifacts}"
printf 'pulled %s\n' "${1}"
