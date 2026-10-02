#!/usr/bin/env bash
#
# Stop the pidfile-owned ds4 process group and verify release.
#
# Targets the recorded process group, never a command-line pattern (the
# pkill -f self-kill trap in AGENTS.md). On unified memory there is
# no VRAM counter to poll: the Metal allocations are owned by the process
# group, so the verified-empty group is the release proof.
#
# shellcheck disable=SC2154  # DS4_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

pid="$(ds4_pid)"

if [[ -z "${pid}" ]]; then
    printf 'not running\n'
    rm -f "${DS4_PIDFILE}"
    exit 0
fi

pgid="$(ps -o pgid= -p "${pid}" | tr -d '[:space:]')"
if [[ "${pgid}" != "${pid}" ]]; then
    printf 'error: pid %s is not its process group leader; refusing group signal\n' \
        "${pid}" >&2
    exit 1
fi

printf 'stopping pid %s (process group %s)\n' "${pid}" "${pgid}"
kill -TERM -- "-${pgid}" 2> /dev/null || true

for _ in $(seq 1 30); do
    sleep 1
    kill -0 -- "-${pgid}" 2> /dev/null || break
done

if kill -0 -- "-${pgid}" 2> /dev/null; then
    printf 'still alive after SIGTERM; sending SIGKILL to process group %s\n' \
        "${pgid}" >&2
    kill -KILL -- "-${pgid}" 2> /dev/null || true
    sleep 3
fi

if kill -0 -- "-${pgid}" 2> /dev/null; then
    printf 'error: process group %s survived SIGKILL\n' "${pgid}" >&2
    exit 1
fi

rm -f "${DS4_PIDFILE}"
printf 'stopped (process group %s empty; unified memory released with it)\n' \
    "${pgid}"

# The log belongs to the run. Removed last, and only on this clean path: a
# stop that found nothing running exits at the top, preserving the log of a
# failed startup, and a surviving group exits above with the log intact.
rm -f "${DS4_LOG}"
