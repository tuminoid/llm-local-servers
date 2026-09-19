#!/usr/bin/env bash
# Foreground child of run.sh, in the session owned by server.json.
set -euo pipefail
# shellcheck source=splash/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
# Resolve with uv, then exec: the recorded PID stays the server's session
# leader instead of a supervising uv process.
SPLASH_PYTHON="$(uv python find --no-project --no-python-downloads "${SPLASH_RUNTIME}/python/bin/python3")"
exec "${SPLASH_PYTHON}" "${SPLASH_DIR}/runtime.py" serve "$@"
