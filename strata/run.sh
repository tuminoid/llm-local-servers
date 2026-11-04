#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=strata/lib.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
strata_python start "$@"
