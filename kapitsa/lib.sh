#!/usr/bin/env bash
# Sourced by the root Makefile's entry points; no global installation used.
set -euo pipefail

KAPITSA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
KAPITSA_DATA_DIR="${KAPITSA_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/kapitsa}"
KAPITSA_STATE_DIR="${KAPITSA_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/kapitsa}"
export KAPITSA_DATA_DIR KAPITSA_STATE_DIR
export PYTHONDONTWRITEBYTECODE=1

# The lifecycle is stdlib Python; uv supplies the interpreter.
kapitsa_python() {
  uv run --no-project --python 3.12 "${KAPITSA_DIR}/runtime.py" "$@"
}
