#!/usr/bin/env bash
#
# Show the managed ds4-server: process, launch line, memory plan and the
# live model.
#
# shellcheck disable=SC2154  # DS4_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

pid="$(ds4_pid)"
if [[ -z "${pid}" ]]; then
    printf 'server:   not running\n'
    exit 0
fi
printf 'server:   running (pid %s) on 127.0.0.1:%s\n' "${pid}" "${DS4_PORT}"
model="$(curl -sf "http://127.0.0.1:${DS4_PORT}/v1/models" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["data"][0]["id"])' 2> /dev/null \
    || printf 'not answering')"
printf 'model:    %s\n' "${model}"
head -1 "${DS4_LOG}"
grep -E 'memory:|context buffers|SSD streaming|resident sessions|KV disk cache' \
    "${DS4_LOG}" | head -8 || true
