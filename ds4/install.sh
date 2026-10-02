#!/usr/bin/env bash
#
# Build the pinned ds4 commit in DS4_SRC, cloning it there when absent.
#
# shellcheck disable=SC2154  # DS4_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -n "$(ds4_pid)" ]]; then
    printf 'error: ds4 is running (pid %s); stop it before rebuilding\n' "$(ds4_pid)" >&2
    exit 1
fi
if [[ ! -d "${DS4_SRC}" ]]; then
    git clone https://github.com/antirez/ds4.git "${DS4_SRC}"
    git -C "${DS4_SRC}" checkout --detach "${DS4_COMMIT}"
fi
ds4_src_pinned
# ds4's Makefile relies on built-in rules; drop the flags this repository's
# Makefile exports, --no-builtin-rules among them.
env -u MAKEFLAGS -u MFLAGS -u MAKELEVEL make -C "${DS4_SRC}"
ds4_server_bin
