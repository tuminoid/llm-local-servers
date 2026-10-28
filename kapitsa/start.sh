#!/usr/bin/env bash
# Foreground child of run.sh, in the session owned by server.json.
set -euo pipefail
# shellcheck source=kapitsa/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
# Resolve with uv, then exec: the recorded PID stays the server's session
# leader instead of a supervising uv process.
KAPITSA_PYTHON="$(uv python find --no-project --no-python-downloads 3.12)"
exec "${KAPITSA_PYTHON}" "${KAPITSA_DIR}/runtime.py" serve "$@"
