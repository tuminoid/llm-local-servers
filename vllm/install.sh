#!/usr/bin/env bash
#
# Create or update the managed vLLM venv at the Makefile pins.
#
# Usage: install.sh
#
# The same script installs locally and, deployed, on a remote host. uv is the
# one tool the host must provide; it fetches the pinned Python as well. An
# existing venv is upgraded in place; recreate it by removing VLLM_VENV first.
#
# shellcheck disable=SC2154  # VLLM_* paths are defined in lib.sh, which the
# lint wrapper cannot follow (it runs without -x), so it sees them as unassigned.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ "$(uname -s)" != "Linux" ]]; then
    printf 'error: vllm/ serves CUDA vLLM on Linux; this host is %s\n' "$(uname -s)" >&2
    exit 1
fi

for var in VLLM_VERSION VLLM_TRANSFORMERS_VERSION VLLM_NINJA_VERSION; do
    if [[ -z "${!var:-}" ]]; then
        printf 'error: %s is unset; install through make vllm-install\n' "${var}" >&2
        exit 1
    fi
done

running_pid="$(vllm_pid)"
if [[ -n "${running_pid}" ]]; then
    printf 'error: vLLM is running (pid %s); stop it before reinstalling\n' "${running_pid}" >&2
    exit 1
fi

UV="$(vllm_uv)"
if [[ -z "${UV}" ]]; then
    printf 'error: uv is required to create the pinned venv\n' >&2
    exit 1
fi

[[ -x "${VLLM_VENV}/bin/python" ]] || "${UV}" venv --python 3.12 "${VLLM_VENV}"
# ninja is on the list because vLLM's kernel JIT shells out to it; the
# launcher puts the venv's bin on PATH for that reason.
"${UV}" pip install --python "${VLLM_VENV}/bin/python" --quiet \
    "vllm==${VLLM_VERSION}" \
    "transformers==${VLLM_TRANSFORMERS_VERSION}" \
    "ninja==${VLLM_NINJA_VERSION}"
"${VLLM_VENV}/bin/python" -c \
    'import transformers, vllm; print("vllm", vllm.__version__, "transformers", transformers.__version__)'
printf 'installed at %s\n' "${VLLM_VENV}"
