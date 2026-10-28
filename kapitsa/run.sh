#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=kapitsa/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
kapitsa_python start "$@"
