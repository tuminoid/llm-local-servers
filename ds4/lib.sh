#!/usr/bin/env bash
#
# Shared paths and helpers for the ds4 (DwarfStar) server scripts. Sourced,
# not executed. The build tree, weights, pidfile and log all live outside
# the repo.

DS4_STATE_DIR="${DS4_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/ds4}"
DS4_PIDFILE="${DS4_PIDFILE:-${DS4_STATE_DIR}/server.pid}"
DS4_LOG="${DS4_LOG:-${DS4_STATE_DIR}/server.log}"
DS4_DATA_DIR="${DS4_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/ds4}"
# ds4 has no releases; the pin is a source commit, built in place.
DS4_COMMIT="${DS4_COMMIT:-0aaea5a238fb41a35106a551e73c8409dfb751ac}"
DS4_SRC="${DS4_SRC:-${DS4_DATA_DIR}/src/${DS4_COMMIT}}"
DS4_PORT="${DS4_PORT:-8023}"
# Serving knobs, host settings; each model config declares DS4_MTP and
# DS4_KV_DISK_MB.
DS4_SLOTS="${DS4_SLOTS:-1}"
DS4_KV_DISK="${DS4_KV_DISK:-1}"
DS4_KV_DISK_DIR="${DS4_KV_DISK_DIR:-${XDG_CACHE_HOME:-${HOME}/.cache}/ds4/kv}"

# Succeeds when DS4_SRC is a clean tree at the pin. A tree at another
# commit, or with local edits, would build or serve under the pin's name.
ds4_src_pinned() {
    local head
    head="$(git -C "${DS4_SRC}" rev-parse HEAD 2> /dev/null || true)"
    if [[ "${head}" != "${DS4_COMMIT}" ]]; then
        printf 'error: %s is at %s, the pin is %s\n' \
            "${DS4_SRC}" "${head:-nothing}" "${DS4_COMMIT}" >&2
        return 1
    fi
    if [[ -n "$(git -C "${DS4_SRC}" status --porcelain)" ]]; then
        printf 'error: %s has local changes\n' "${DS4_SRC}" >&2
        return 1
    fi
}

# The pinned build's ds4-server, or an error.
ds4_server_bin() {
    if ! ds4_src_pinned; then
        printf 'run make ds4-install\n' >&2
        return 1
    fi
    if [[ ! -x "${DS4_SRC}/ds4-server" ]]; then
        printf 'error: %s/ds4-server is not built; run make ds4-install\n' "${DS4_SRC}" >&2
        return 1
    fi
    printf '%s\n' "${DS4_SRC}/ds4-server"
}

# Pid of the running server, or empty. Treats a stale pidfile as "not running".
ds4_pid() {
    [[ -f "${DS4_PIDFILE}" ]] || return 0
    local pid
    pid="$(cat "${DS4_PIDFILE}")"
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 0
    kill -0 "${pid}" 2> /dev/null || return 0
    printf '%s\n' "${pid}"
}

# Local path of the conf's pinned GGUF in the HF cache, or an error. An LFS
# blob is named by its sha256, so the resolved blob name is the identity
# check; pull.sh leaves hashing the file to the downloader.
# shellcheck disable=SC2154  # DS4_MODEL_* come from the sourced conf.
ds4_gguf() {
    local snapshot blob
    snapshot="${HF_HUB_CACHE:-${HF_HOME:-${HOME}/.cache/huggingface}/hub}/models--${DS4_MODEL_REPO//\//--}/snapshots/${DS4_MODEL_REVISION}/${DS4_MODEL_FILE}"
    if [[ ! -e "${snapshot}" ]]; then
        printf 'error: %s is not downloaded; run make ds4-pull\n' "${DS4_MODEL_FILE}" >&2
        return 1
    fi
    blob="$(basename "$(readlink "${snapshot}")")"
    if [[ "${blob}" != "${DS4_MODEL_SHA256}" ]]; then
        printf 'error: %s resolves to blob %s, the pin is %s\n' \
            "${DS4_MODEL_FILE}" "${blob}" "${DS4_MODEL_SHA256}" >&2
        return 1
    fi
    printf '%s\n' "${snapshot}"
}

# Source models/<name>.conf, or fail with the list of configs.
ds4_load_conf() {
    local dir conf
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/models"
    conf="${dir}/${1:-}.conf"
    if [[ -z "${1:-}" || ! -f "${conf}" ]]; then
        printf 'error: unknown model config %s; available:\n' "${1:-}" >&2
        for conf in "${dir}"/*.conf; do
            printf '  %s\n' "$(basename "${conf}" .conf)" >&2
        done
        return 1
    fi
    # shellcheck disable=SC1090
    source "${conf}"
}
