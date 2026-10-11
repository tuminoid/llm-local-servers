#!/usr/bin/env bash
# Sourced by the root Makefile's entry points; no global installation used.
set -euo pipefail

SPLASH_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SPLASH_DATA_DIR="${SPLASH_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/splash}"
SPLASH_STATE_DIR="${SPLASH_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/splash}"
SPLASH_VERSION="${SPLASH_VERSION:-1.3.1}"
SPLASH_RUNTIME="${SPLASH_DATA_DIR}/runtime/${SPLASH_VERSION}"
export SPLASH_DATA_DIR SPLASH_STATE_DIR SPLASH_VERSION SPLASH_RUNTIME
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false

splash_python() {
  if [[ ! -x "${SPLASH_RUNTIME}/python/bin/python3" ]]; then
    echo 'error: Splash is not installed; run make splash-install' >&2
    return 1
  fi
  uv run --no-project --python "${SPLASH_RUNTIME}/python/bin/python3" \
    "${SPLASH_DIR}/runtime.py" "$@"
}
