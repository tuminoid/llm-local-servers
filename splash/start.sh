#!/usr/bin/env bash
# Foreground child of run.sh, in the session owned by server.json.
set -euo pipefail
# shellcheck source=splash/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
# Resolve with uv, then exec: the recorded PID stays the server's session
# leader instead of a supervising uv process.
SPLASH_PYTHON="$(uv python find --no-project --no-python-downloads "${SPLASH_RUNTIME}/python/bin/python3")"
# Pin guard: the runtime directory is named by SPLASH_VERSION; refuse when the
# release manifest inside it says otherwise, so a mis-populated runtime never
# serves under the documented rates.
release_version="$("${SPLASH_PYTHON}" -c \
    'import json, sys; print(json.load(open(sys.argv[1]))["version"])' \
    "${SPLASH_RUNTIME}/release.json" 2> /dev/null || true)"
if [[ "${release_version}" != "${SPLASH_VERSION}" ]]; then
    printf 'error: %s holds Splash release %s, the pin is %s; run make splash-install\n' \
        "${SPLASH_RUNTIME}" "${release_version:-unknown}" "${SPLASH_VERSION}" >&2
    exit 1
fi
exec "${SPLASH_PYTHON}" "${SPLASH_DIR}/runtime.py" serve "$@"
