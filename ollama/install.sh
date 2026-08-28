#!/usr/bin/env bash
#
# Install a pinned Ollama release into the configured runtime root.
#
# The official installer owns /usr/local and configures systemd. This server is
# deliberately process-managed, so it extracts the same release archive into
# a versioned local user runtime or an explicitly isolated remote tree instead.
#
# shellcheck disable=SC2154  # OLLAMA_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

version="${OLLAMA_VERSION}"

if [[ ! "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'error: invalid OLLAMA_VERSION: %s\n' "${version}" >&2
    exit 1
fi

# One reviewed digest per release archive, from the release's sha256sum.txt.
# The macOS archive is universal, so it carries no architecture suffix.
case "$(uname -s)" in
    Darwin)
        sha_var="OLLAMA_ARCHIVE_SHA256_DARWIN"
        asset="ollama-darwin.tgz"
        ;;
    Linux)
        case "$(uname -m)" in
            x86_64)
                sha_var="OLLAMA_ARCHIVE_SHA256"
                asset="ollama-linux-amd64.tar.zst"
                ;;
            aarch64 | arm64)
                sha_var="OLLAMA_ARCHIVE_SHA256_LINUX_ARM64"
                asset="ollama-linux-arm64.tar.zst"
                ;;
            *)
                printf 'error: unsupported architecture: %s\n' "$(uname -m)" >&2
                exit 1
                ;;
        esac
        ;;
    *)
        printf 'error: unsupported operating system: %s\n' "$(uname -s)" >&2
        exit 1
        ;;
esac

expected_sha="${!sha_var:-}"
if [[ ! "${expected_sha}" =~ ^[0-9a-f]{64}$ ]]; then
    printf 'error: %s must be the reviewed release digest for %s\n' \
        "${sha_var}" "${asset}" >&2
    exit 1
fi

archive_sha256() {
    if command -v sha256sum > /dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

destination="${OLLAMA_RUNTIME_ROOT}/v${version}"
executable="${destination}/bin/ollama"
download_dir="${OLLAMA_RUNTIME_ROOT}/downloads"
archive="${download_dir}/v${version}-${asset}"
url="https://github.com/ollama/ollama/releases/download/v${version}/${asset}"

if [[ -x "${executable}" ]] && [[ "$(ollama_version "${executable}")" == "${version}" ]]; then
    printf 'ollama %s already installed at %s\n' "${version}" "${executable}"
    exit 0
fi

if [[ "${asset}" == *.tar.zst ]]; then
    command -v zstd > /dev/null 2>&1 || {
        printf 'error: zstd is required to extract the Ollama release\n' >&2
        exit 1
    }
fi

mkdir -p "${destination}" "${download_dir}"
printf 'downloading Ollama %s (%s)\n' "${version}" "${asset}"
curl --fail --location --retry 3 --show-error --progress-bar \
    --output "${archive}" "${url}"

actual_sha="$(archive_sha256 "${archive}")"
if [[ "${actual_sha}" != "${expected_sha}" ]]; then
    printf 'error: archive checksum mismatch\n' >&2
    printf 'expected: %s\nactual:   %s\n' "${expected_sha}" "${actual_sha}" >&2
    exit 1
fi

if [[ "${asset}" == *.tar.zst ]]; then
    zstd --decompress --stdout "${archive}" | tar -xf - -C "${destination}"
else
    # The macOS archive is flat: the CLI, llama-server, llama-quantize, and
    # the MLX runtime directories all sit at its root. Recreate the Linux
    # bin/ + lib/ollama/ layout; the binary searches for its bundled
    # libraries in <exe dir>/../lib/ollama (ml/path.go), so a bare binary
    # would find no MLX runtime.
    mkdir -p "${destination}/bin" "${destination}/lib/ollama"
    tar -xzf "${archive}" -C "${destination}/lib/ollama"
    mv "${destination}/lib/ollama/ollama" "${executable}"
fi

if [[ ! -x "${executable}" ]]; then
    printf 'error: release did not contain %s\n' "${executable}" >&2
    exit 1
fi
actual_version="$(ollama_version "${executable}")"
if [[ "${actual_version}" != "${version}" ]]; then
    printf 'error: installed version is %s, expected %s\n' \
        "${actual_version}" "${version}" >&2
    exit 1
fi

# Keep the path for resumable failed downloads, but not a second 1.4 GB copy
# after a verified install.
: > "${archive}"
printf 'installed Ollama %s at %s\n' "${version}" "${executable}"
