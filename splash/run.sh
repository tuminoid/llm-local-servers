#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=splash/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
splash_python start "$@"
