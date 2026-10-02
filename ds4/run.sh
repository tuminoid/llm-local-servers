#!/usr/bin/env bash
#
# Start ds4-server detached and wait until it serves /v1/models.
#
# Usage: run.sh <model-config-name>
#
# macOS ships no setsid: bash job control gives the child its own process
# group, the handle stop.sh signals.
#
# shellcheck disable=SC2154  # DS4_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"
ds4_load_conf "${1:-}"
READY_TIMEOUT="${DS4_READY_TIMEOUT:-1800}"

if [[ -n "$(ds4_pid)" ]]; then
    printf 'already running (pid %s); stop it first\n' "$(ds4_pid)" >&2
    exit 1
fi
if lsof -nP -iTCP:"${DS4_PORT}" -sTCP:LISTEN > /dev/null 2>&1; then
    printf 'error: port %s is already claimed\n' "${DS4_PORT}" >&2
    exit 1
fi

mkdir -p "${DS4_STATE_DIR}"
: > "${DS4_LOG}"
set -m
nohup "${SCRIPT_DIR}/start.sh" "$1" < /dev/null > "${DS4_LOG}" 2>&1 &
set +m
launcher_pid=$!
disown || true
printf 'log: %s\n' "${DS4_LOG}"

deadline=$((SECONDS + READY_TIMEOUT))
while ((SECONDS < deadline)); do
    if ! kill -0 "${launcher_pid}" 2> /dev/null; then
        printf 'startup failed: process exited before readiness; last log lines:\n' >&2
        tail -20 "${DS4_LOG}" >&2
        exit 1
    fi
    if curl -sf "http://127.0.0.1:${DS4_PORT}/v1/models" > /dev/null 2>&1; then
        printf 'ready (pid %s)\n' "$(ds4_pid)"
        exit 0
    fi
    sleep 5
done
printf 'timed out after %ss waiting for startup; see %s\n' "${READY_TIMEOUT}" "${DS4_LOG}" >&2
exit 1
