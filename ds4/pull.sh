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
hf download "${DS4_MODEL_REPO}" "${DS4_MODEL_FILE}" --revision "${DS4_MODEL_REVISION}"
ds4_gguf
