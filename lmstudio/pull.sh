#!/usr/bin/env bash
#
# Download a model's pinned artifact into the LM Studio model store.
#
# Usage: pull.sh <model-config-name>
#
# Format is explicit, not inferred: the conf names LMSTUDIO_FORMAT (mlx or
# gguf) and `lms get` is invoked with the matching --mlx/--gguf filter and the
# quantization pinned with the `@quant` suffix. LM Studio keeps MLX and GGUF
# variants as distinct model keys, so the artifact -- and therefore the runner
# (llama.cpp for GGUF, MLX for Apple Silicon) -- is selected here, exactly as
# the Ollama and vLLM-Metal servers keep one conf per artifact.
#
# Note the accepted deviation (lmstudio/AGENTS.md): LM Studio identifies a model
# by its Hugging Face repo path plus quant, not by a served content digest, so
# there is no registry SHA256 to pin the way the Ollama configs do. The pin is
# the repo path plus the quantization tag.
#
# shellcheck disable=SC2154  # LMSTUDIO_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    lmstudio_list_models >&2
    exit 1
fi
MODEL_CONF="$1"
CONF_FILE="${SCRIPT_DIR}/models/${MODEL_CONF}.conf"
if [[ ! -f "${CONF_FILE}" ]]; then
    printf 'error: no such model config: %s\n' "${CONF_FILE}" >&2
    printf 'available:\n' >&2
    lmstudio_list_models >&2
    exit 1
fi

LMSTUDIO_GET_SPEC="${LMSTUDIO_GET_SPEC:-}"
LMSTUDIO_FORMAT="${LMSTUDIO_FORMAT:-}"
# shellcheck source=models/qwen3.8-27b-gguf.conf disable=SC1091
source "${CONF_FILE}"

for var in LMSTUDIO_GET_SPEC LMSTUDIO_FORMAT; do
    if [[ -z "${!var}" ]]; then
        printf 'error: %s is empty; check %s\n' "${var}" "${CONF_FILE}" >&2
        exit 1
    fi
done

case "${LMSTUDIO_FORMAT}" in
    gguf) format_flag="--gguf" ;;
    mlx)
        if [[ "$(uname -s)/$(uname -m)" != "Darwin/arm64" ]]; then
            printf 'error: the MLX runtime requires macOS on Apple Silicon\n' >&2
            printf 'this config (%s) is Darwin/arm64 only; use a gguf config here\n' \
                "${MODEL_CONF}" >&2
            exit 1
        fi
        format_flag="--mlx"
        ;;
    *)
        printf 'error: unsupported LMSTUDIO_FORMAT: %s (want gguf or mlx)\n' \
            "${LMSTUDIO_FORMAT}" >&2
        exit 1
        ;;
esac

LMSTUDIO_EXE="$(lmstudio_bin)"
if [[ -z "${LMSTUDIO_EXE}" ]]; then
    printf 'error: lms not found; run make lmstudio-install\n' >&2
    exit 1
fi

printf 'downloading %s (%s) via lms get\n' "${LMSTUDIO_GET_SPEC}" "${LMSTUDIO_FORMAT}"
# --yes accepts the exact-match auto-selection non-interactively; the @quant in
# the spec plus the format filter pin the artifact. lms is idempotent: an
# already-downloaded artifact is a fast no-op.
"${LMSTUDIO_EXE}" get "${LMSTUDIO_GET_SPEC}" "${format_flag}" --yes

# Confirm the artifact is present with the expected format in the local store.
if ! "${LMSTUDIO_EXE}" ls --llm --json 2> /dev/null | python3 -c '
import json
import sys

spec = sys.argv[1]
fmt = sys.argv[2].lower()
# Match on the repo/path stem before any @quant, case-insensitively: lms
# reports the canonical key which may differ in case or carry the quant tag.
stem = spec.split("@", 1)[0].lower()
# lms reports an MLX artifact as the on-disk container "safetensors", never
# "mlx"; accept either so the mlx confirmation does not warn spuriously.
accepted = {"mlx", "safetensors"} if fmt == "mlx" else {fmt}
try:
    models = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(1)
if isinstance(models, dict):
    models = models.get("models") or models.get("data") or []
for model in models:
    path = str(model.get("path") or model.get("modelKey") or model.get("key") or "").lower()
    fmt_field = str(model.get("format") or model.get("type") or "").lower()
    fmt_ok = (
        not fmt_field
        or any(name in fmt_field for name in accepted)
        or fmt == "gguf" and path.endswith(".gguf")
    )
    if stem in path and fmt_ok:
        sys.exit(0)
sys.exit(1)
' "${LMSTUDIO_GET_SPEC}" "${LMSTUDIO_FORMAT}"; then
    printf 'warning: could not confirm %s (%s) in the local store via lms ls\n' \
        "${LMSTUDIO_GET_SPEC}" "${LMSTUDIO_FORMAT}" >&2
    printf 'check lms ls --llm --detailed; start.sh will verify at load time\n' >&2
fi

printf 'model ready: %s (%s)\n' "${LMSTUDIO_GET_SPEC}" "${LMSTUDIO_FORMAT}"
