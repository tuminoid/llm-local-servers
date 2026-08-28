#!/usr/bin/env bash
#
# Stop the vLLM server.
#
# Targets the pid recorded by start.sh, never a command-line pattern. pkill -f is
# actively unsafe here: the pattern appears in the command line of any shell that
# mentions it, including the shell invoking the kill, so pkill matches and kills
# the caller instead of the server.
#
# Signalling the top-level process is enough -- vLLM traps it and tears down its
# EngineCore children. We verify via GPU memory rather than assuming, since an
# orphaned worker holds VRAM and would break the next start.
#
# shellcheck disable=SC2154  # VLLM_* paths are defined in lib.sh, which the
# lint wrapper cannot follow (it runs without -x), so it sees them as unassigned.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

pid="$(vllm_pid)"

if [[ -z "${pid}" ]]; then
    printf 'not running\n'
    rm -f "${VLLM_PIDFILE}"
    exit 0
fi

printf 'stopping pid %s (gpu %s MiB)\n' "${pid}" "$(vllm_gpu_mib)"
kill "${pid}" 2> /dev/null || true

for _ in $(seq 1 30); do
    sleep 1
    kill -0 "${pid}" 2> /dev/null || break
done

if kill -0 "${pid}" 2> /dev/null; then
    printf 'still alive after SIGTERM; sending SIGKILL\n' >&2
    kill -9 "${pid}" 2> /dev/null || true
    sleep 3
fi

rm -f "${VLLM_PIDFILE}"

sleep 2
used="$(vllm_gpu_mib)"
printf 'stopped (gpu %s MiB)\n' "${used}"

if ((used > 500)); then
    printf 'warning: GPU still holding %s MiB, possible orphaned worker\n' "${used}" >&2
    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv >&2
    exit 1
fi

# The log belongs to the run, not to the filesystem: a stopped server has no log,
# and run.sh creates a fresh one on the next start. Without this a single wedged
# run can leave a very large file behind -- one heartbeat-failure loop wrote
# 238 MB in 37 hours, long after the last request was served.
#
# Deliberately last, so it is skipped on both paths where the log is still
# evidence: a teardown that left VRAM held exits above, and a stop that found
# nothing running exits at the top without touching it, which is what preserves
# the log of a startup that failed.
rm -f "${VLLM_LOG}"
