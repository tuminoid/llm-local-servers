#!/usr/bin/env bash
#
# Start the LM Studio server + model and confirm it is serving.
#
# Usage: run.sh <model-config-name>
#
# LM Studio's model is owned by the long-running service, which is already a
# detached daemon, so there is nothing for this launcher to fork and hold: the
# other runtimes detach because they own the server process, but here `lms
# load` blocks until the model is resident and the daemon keeps serving after
# this returns. So run.sh invokes start.sh synchronously (weight load included)
# and then confirms the OpenAI-compatible endpoint answers with the configured
# model. stop.sh tears the model and service down. See lmstudio/AGENTS.md.
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

# The served name is what /v1/models must report once the model is loaded.
LMSTUDIO_SERVED_NAME="${LMSTUDIO_SERVED_NAME:-}"
# shellcheck source=models/qwen3.8-27b-gguf.conf disable=SC1091
source "${CONF_FILE}"
if [[ -z "${LMSTUDIO_SERVED_NAME}" ]]; then
    printf 'error: LMSTUDIO_SERVED_NAME is empty; check %s\n' "${CONF_FILE}" >&2
    exit 1
fi

READY_TIMEOUT="${LMSTUDIO_READY_TIMEOUT:-600}"
base="$(lmstudio_api_base)"

mkdir -p "${LMSTUDIO_STATE_DIR}"

# start.sh brings the server up and blocks on `lms load` until the model is
# resident; its output is captured to the run log for status/debugging.
printf 'log: %s\n' "${LMSTUDIO_LOG}"
if ! "${SCRIPT_DIR}/start.sh" "${MODEL_CONF}" > "${LMSTUDIO_LOG}" 2>&1; then
    printf 'startup failed; log tail:\n' >&2
    tail -20 "${LMSTUDIO_LOG}" >&2
    exit 1
fi

# The served model answers on /v1/models once the load has completed. `lms
# load` already returned, so this is a short confirmation, not a long wait.
deadline=$((SECONDS + READY_TIMEOUT))
while ((SECONDS < deadline)); do
    if models="$(curl -sf --max-time 5 "${base}/v1/models" 2> /dev/null)"; then
        if printf '%s' "${models}" | python3 -c '
import json
import sys

served = sys.argv[1]
try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(1)
ids = {str(m.get("id")) for m in data.get("data", [])}
sys.exit(0 if served in ids else 1)
' "${LMSTUDIO_SERVED_NAME}"; then
            printf 'ready (api %s, model %s)\n' "${base}" "${LMSTUDIO_SERVED_NAME}"
            exit 0
        fi
    fi
    sleep 2
done

printf 'timed out after %ss waiting for %s at %s; see %s\n' \
    "${READY_TIMEOUT}" "${LMSTUDIO_SERVED_NAME}" "${base}" "${LMSTUDIO_LOG}" >&2
exit 1
