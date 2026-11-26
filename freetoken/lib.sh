#!/usr/bin/env bash
# Sourced by the entry points; no global installation used.
set -euo pipefail

FREETOKEN_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FREETOKEN_DATA_DIR="${FREETOKEN_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/freetoken}"
FREETOKEN_STATE_DIR="${FREETOKEN_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/freetoken}"
export FREETOKEN_DATA_DIR FREETOKEN_STATE_DIR
export PYTHONDONTWRITEBYTECODE=1

# The lifecycle is stdlib Python on the host's python3; FreeToken itself runs
# from the venv install creates.
freetoken_python() {
  python3 -I "${FREETOKEN_DIR}/runtime.py" "$@"
}
