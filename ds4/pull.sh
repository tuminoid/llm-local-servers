#!/usr/bin/env bash
#
# Download the conf's pinned GGUF into the HF cache and verify its blob.
#
# Usage: pull.sh <model-config-name>
#
# shellcheck disable=SC2154  # DS4_* values come from the conf.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"
ds4_load_conf "${1:-}"
# The host's hf CLI when it has one, else the pinned one through uv.
if command -v hf > /dev/null 2>&1; then
    hf=(hf)
elif command -v uv > /dev/null 2>&1; then
    hf=(uv tool run --from "huggingface_hub==${HF_HUB_VERSION:?set by make}" hf)
else
    printf 'error: neither hf nor uv is on PATH\n' >&2
    exit 1
fi
"${hf[@]}" download "${DS4_MODEL_REPO}" "${DS4_MODEL_FILE}" --revision "${DS4_MODEL_REVISION}"
ds4_gguf
