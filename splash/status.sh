#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=splash/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
exec uv run --no-project --python 3.12 "${SPLASH_DIR}/runtime.py" status
