#!/usr/bin/env bash
# Sourced by the entry points; no global installation used.
set -euo pipefail

STRATA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STRATA_DATA_DIR="${STRATA_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/strata}"
STRATA_STATE_DIR="${STRATA_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/strata}"
export STRATA_DATA_DIR STRATA_STATE_DIR
export PYTHONDONTWRITEBYTECODE=1

# The lifecycle is stdlib Python on the host's python3; Strata's server and
# model tools run from the source tree's own venv.
strata_python() {
  python3 -I "${STRATA_DIR}/runtime.py" "$@"
}
