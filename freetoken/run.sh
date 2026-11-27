#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=freetoken/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
freetoken_python start "$@"
