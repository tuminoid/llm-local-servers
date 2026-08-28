#!/usr/bin/env bash
#
# Stop the pidfile-owned Ollama process group and verify GPU release.
#
# shellcheck disable=SC2154  # OLLAMA_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

pid="$(ollama_pid)"
if [[ -z "${pid}" ]]; then
    printf 'not running\n'
    exit 0
fi

pgid="$(ps -o pgid= -p "${pid}" | tr -d '[:space:]')"
if [[ "${pgid}" != "${pid}" ]]; then
    printf 'error: pid %s is not the expected session leader; refusing group signal\n' \
        "${pid}" >&2
    exit 1
fi

baseline=0
if [[ -s "${OLLAMA_BASELINE_GPU_FILE}" ]]; then
    baseline="$(cat "${OLLAMA_BASELINE_GPU_FILE}")"
fi
[[ "${baseline}" =~ ^[0-9]+$ ]] || baseline=0

if command -v nvidia-smi > /dev/null 2>&1; then
    printf 'stopping pid %s (gpu %s MiB)\n' "${pid}" "$(ollama_gpu_mib)"
else
    printf 'stopping pid %s (process group %s)\n' "${pid}" "${pgid}"
fi
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

# Empty rather than recursively cleaning state: the next run overwrites both.
: > "${OLLAMA_PIDFILE}"
if command -v nvidia-smi > /dev/null 2>&1; then
    sleep 2
    used="$(ollama_gpu_mib)"
    printf 'stopped (gpu %s MiB; baseline %s MiB)\n' "${used}" "${baseline}"

    if ((used > baseline + 512)); then
        printf 'error: GPU remains %s MiB above the pre-start baseline\n' \
            "$((used - baseline))" >&2
        nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv >&2
        exit 1
    fi
else
    # Unified memory is owned by the process group, so the verified-empty
    # group above is the release proof on this host.
    printf 'stopped (process group %s empty; unified memory released with it)\n' \
        "${pgid}"
fi

: > "${OLLAMA_LOG}"
: > "${OLLAMA_BASELINE_GPU_FILE}"
