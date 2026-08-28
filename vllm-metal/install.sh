#!/usr/bin/env bash
#
# Install the pinned vLLM-Metal runtime into the managed venv.
#
# Everything is pinned: the vLLM-Metal wheel and the prebuilt vLLM macOS wheel
# are downloaded from their GitHub releases and checksum-verified before
# installation. Transitive pins (mlx==0.32.0, the mlx-lm git SHA) are declared
# by the vLLM-Metal wheel itself, whose prebuilt _paged_ops.so is ABI-locked
# to that exact MLX.
#
# Deliberately not upstream's `curl | bash` installer: that writes a mutable
# user-global ~/.venv-vllm-metal with unpinned latest versions. This venv is
# the server runtime, owned by this Makefile target, recreated from pins.
#
# shellcheck disable=SC2154  # VLLM_METAL_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ "$(uname -s)/$(uname -m)" != "Darwin/arm64" ]]; then
    printf 'error: vLLM-Metal requires macOS on Apple Silicon\n' >&2
    exit 1
fi
command -v uv > /dev/null 2>&1 || {
    printf 'error: uv is required to create the pinned venv\n' >&2
    exit 1
}

plugin_version="${VLLM_METAL_VERSION:?set by the Makefile}"
plugin_sha="${VLLM_METAL_WHEEL_SHA256:?set by the Makefile}"
vllm_version="${VLLM_METAL_VLLM_VERSION:?set by the Makefile}"
vllm_sha="${VLLM_METAL_VLLM_WHEEL_SHA256:?set by the Makefile}"

for sha in "${plugin_sha}" "${vllm_sha}"; do
    if [[ ! "${sha}" =~ ^[0-9a-f]{64}$ ]]; then
        printf 'error: wheel digests must be reviewed sha256 hex values\n' >&2
        exit 1
    fi
done

plugin_wheel="vllm_metal-${plugin_version}-cp312-cp312-macosx_15_0_arm64.whl"
plugin_url="https://github.com/vllm-project/vllm-metal/releases/download/v${plugin_version}/${plugin_wheel}"
# The + in the local version segment is URL-encoded in the asset path.
vllm_wheel="vllm-${vllm_version}+cpu-cp312-cp312-macosx_11_0_arm64.whl"
vllm_url="https://github.com/vllm-project/vllm/releases/download/v${vllm_version}/vllm-${vllm_version}%2Bcpu-cp312-cp312-macosx_11_0_arm64.whl"

stamp="${VLLM_METAL_VENV}/.pins"
want="vllm-metal=${plugin_version} vllm=${vllm_version}"
if [[ -x "${VLLM_METAL_VENV}/bin/vllm" ]] \
    && [[ -f "${stamp}" ]] && [[ "$(cat "${stamp}")" == "${want}" ]]; then
    printf 'vllm-metal %s already installed at %s\n' \
        "${plugin_version}" "${VLLM_METAL_VENV}"
    exit 0
fi

download_dir="${VLLM_METAL_DATA_DIR}/downloads"
mkdir -p "${download_dir}"

fetch() {
    local url="$1" out="$2" expected="$3" actual
    # A verified install truncates its wheels to zero bytes; treat one as
    # absent so a manual venv removal can reinstall the same pins.
    [[ -f "${out}" && ! -s "${out}" ]] && rm -f "${out}"
    if [[ ! -f "${out}" ]]; then
        printf 'downloading %s\n' "$(basename "${out}")"
        curl --fail --location --retry 3 --show-error --progress-bar \
            --output "${out}" "${url}"
    fi
    actual="$(shasum -a 256 "${out}" | awk '{print $1}')"
    if [[ "${actual}" != "${expected}" ]]; then
        printf 'error: checksum mismatch for %s\n' "$(basename "${out}")" >&2
        printf 'expected: %s\nactual:   %s\n' "${expected}" "${actual}" >&2
        exit 1
    fi
}

fetch "${vllm_url}" "${download_dir}/${vllm_wheel}" "${vllm_sha}"
fetch "${plugin_url}" "${download_dir}/${plugin_wheel}" "${plugin_sha}"

# Recreate the venv from scratch so stale versions cannot survive a pin bump.
# The plugin requires native arm64 CPython >=3.12,<3.14; uv resolves 3.12
# from the host (Homebrew) or its own managed store.
rm -rf "${VLLM_METAL_VENV}"
uv venv --python 3.12 "${VLLM_METAL_VENV}"

# One resolution for both wheels: the plugin's dependencies (exact mlx, the
# mlx-lm git SHA, tokenizers) install alongside, and the local vllm wheel
# satisfies the plugin's vllm requirement instead of a PyPI download.
uv pip install --python "${VLLM_METAL_VENV}/bin/python" \
    "${download_dir}/${vllm_wheel}" "${download_dir}/${plugin_wheel}"

if [[ ! -x "${VLLM_METAL_VENV}/bin/vllm" ]]; then
    printf 'error: install completed but %s/bin/vllm is missing\n' \
        "${VLLM_METAL_VENV}" >&2
    exit 1
fi

printf '%s\n' "${want}" > "${stamp}"
# Keep resumable failed downloads, but not two verified multi-MB wheels.
: > "${download_dir}/${vllm_wheel}"
: > "${download_dir}/${plugin_wheel}"
printf 'installed vllm-metal %s (vllm %s) at %s\n' \
    "${plugin_version}" "${vllm_version}" "${VLLM_METAL_VENV}"
