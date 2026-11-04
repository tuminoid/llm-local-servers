#!/usr/bin/env bash
# Foreground child of run.sh, in the session owned by server.json: it waits
# for the registration handshake, then execs Strata's server.
set -euo pipefail
# shellcheck source=strata/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
exec python3 -I "${STRATA_DIR}/runtime.py" serve "$@"
