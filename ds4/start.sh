#!/usr/bin/env bash
#
# Foreground ds4-server for run.sh: resolve the pinned build and GGUF, record
# this pid, then exec so the pid stays the server's process-group leader.
#
# Usage: start.sh <model-config-name>
#
# shellcheck disable=SC2154  # DS4_* values come from lib.sh and the conf.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"
ds4_load_conf "${1:-}"
server="$(ds4_server_bin)"
gguf="$(ds4_gguf)"

# Host adaptation: weights that leave under 16 GiB of unified memory for
# context and the OS are streamed from SSD instead of held resident.
mem_gib="$(($(sysctl -n hw.memsize) / 1073741824))"
args=(--metal -m "${gguf}" --ctx "${DS4_CTX}" --host 127.0.0.1 --port "${DS4_PORT}")
if ((DS4_RESIDENT_GIB + 16 > mem_gib)); then
    args+=(--ssd-streaming)
fi
# Resident sessions. More than one lost on deep agent sessions on the M5 Max
# (see BENCHMARKS.md); each extra slot costs its full-context KV.
if ((DS4_SLOTS > 1)); then
    args+=(--batched-session "${DS4_SLOTS}")
fi
# Built-in MTP, per model config. Exact sampling keeps the declared
# distribution; ds4's default accepts greedy drafts at any temperature.
if [[ "${DS4_MTP}" == 1 ]]; then
    args+=(--mtp --mtp-exact-sampling)
fi
# The server runs from the build tree, so its paths must be absolute.
for path in "${DS4_KV_DISK_DIR}" "${DS4_TRACE:-/}"; do
    if [[ "${path}" != /* ]]; then
        printf 'error: %s must be an absolute path\n' "${path}" >&2
        exit 1
    fi
done
# Disk KV checkpoints, one directory per model config: a live-prefix miss
# restores the nearest saved frontier instead of prefilling from token 0.
# They persist across restarts and hold prompt text.
if [[ "${DS4_KV_DISK}" == 1 ]]; then
    mkdir -p "${DS4_KV_DISK_DIR}/$1"
    args+=(--kv-disk-dir "${DS4_KV_DISK_DIR}/$1" --kv-disk-space-mb "${DS4_KV_DISK_MB}")
fi
# Diagnostic trace of prompt rendering, cache decisions and tool parsing.
# It records prompt text.
if [[ -n "${DS4_TRACE:-}" ]]; then
    args+=(--trace "${DS4_TRACE}")
fi

printf 'ds4 %s serving %s on %s GiB: %s\n' "${DS4_COMMIT}" "${DS4_MODEL_FILE}" \
    "${mem_gib}" "${args[*]}"
printf '%s\n' "$$" > "${DS4_PIDFILE}"
# Metal kernels load relative to the source tree.
cd "${DS4_SRC}"
exec "${server}" "${args[@]}"
