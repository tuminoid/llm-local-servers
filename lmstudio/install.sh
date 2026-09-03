#!/usr/bin/env bash
#
# Verify the LM Studio CLI is present and recent enough to manage the server.
#
# This is a deliberately weaker guard than the other runtimes in this tree, and
# that is the accepted deviation for LM Studio (see lmstudio/AGENTS.md). Ollama
# and vLLM-Metal install a pinned, checksum-verified release into a runtime tree
# this repository owns. LM Studio ships the `lms` CLI and its inference runtimes
# (llama.cpp for GGUF, MLX for Apple Silicon) inside an auto-updating desktop
# application; there is no per-platform release tarball with a published digest
# to fetch and verify, and the app must have been launched at least once before
# `lms` works at all. So install here means: confirm lms is on PATH, meets the
# version floor, its backing service is reachable, and the inference runtimes
# are present. The desktop app itself is installed out of band by the operator.
#
# shellcheck disable=SC2154  # LMSTUDIO_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

min_version="${LMSTUDIO_MIN_VERSION:-0.4.0}"
if [[ ! "${min_version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'error: invalid LMSTUDIO_MIN_VERSION: %s\n' "${min_version}" >&2
    exit 1
fi

LMSTUDIO_EXE="$(lmstudio_bin)"
if [[ -z "${LMSTUDIO_EXE}" ]]; then
    printf 'error: the lms CLI was not found\n' >&2
    printf 'install LM Studio from https://lmstudio.ai and run it once, then\n' >&2
    printf 'ensure the lms CLI is on PATH (or set LMSTUDIO_BIN=<path-to-lms>)\n' >&2
    exit 1
fi

# `lms` talks to the desktop service; a first invocation that cannot reach it
# means the app has never been launched. `lms ls` is a cheap read that requires
# the service, so it doubles as a reachability probe.
if ! "${LMSTUDIO_EXE}" ls > /dev/null 2>&1; then
    printf 'error: lms could not reach the LM Studio service\n' >&2
    printf 'launch the LM Studio app once (it starts the service), then retry\n' >&2
    exit 1
fi

# The version floor is about the LM Studio app's v1 REST API, not the CLI build
# string. Some `lms` builds print only a commit hash, so a missing semver is not
# fatal: enforce the floor when a semver is parseable, otherwise note that the
# real gate is the v1 API check performed at bench/capability time.
actual_version="$(lmstudio_version "${LMSTUDIO_EXE}")"
if [[ -n "${actual_version}" ]]; then
    if ! lmstudio_version_at_least "${actual_version}" "${min_version}"; then
        printf 'error: lms %s is older than the required %s at %s\n' \
            "${actual_version}" "${min_version}" "${LMSTUDIO_EXE}" >&2
        printf 'update LM Studio; the v1 REST API (load/unload/list) needs >= %s\n' \
            "${min_version}" >&2
        exit 1
    fi
    printf 'lms %s ready at %s (service reachable)\n' \
        "${actual_version}" "${LMSTUDIO_EXE}"
else
    printf 'lms ready at %s (service reachable; CLI reports no semver)\n' \
        "${LMSTUDIO_EXE}"
    printf 'note: the v1 REST API floor (>= %s) is verified at start/bench time\n' \
        "${min_version}" >&2
fi

# Report the installed inference runtimes so a missing GGUF or MLX backend is
# visible before a load fails. Informational only: which backend a model needs
# is decided by its artifact (see pull.sh and the model configs).
if runtimes="$("${LMSTUDIO_EXE}" runtime ls 2> /dev/null)"; then
    printf 'inference runtimes:\n'
    printf '%s\n' "${runtimes}" | sed 's/^/  /'
fi

mkdir -p "${LMSTUDIO_STATE_DIR}"
