#!/usr/bin/env bash
#
# Shared paths and helpers for the LM Studio server scripts. Sourced, not run.
#
# LM Studio differs from the other runtimes in this tree: the served model is
# owned by a long-running background service (the LM Studio daemon), not by a
# process group this launcher forks. So there is no pidfile to signal -- the
# lifecycle is expressed through the `lms` CLI (`lms server start/stop`,
# `lms load/unload`, `lms ps`) and the OpenAI-compatible HTTP endpoint. State we
# do own -- a baseline GPU reading and the log we capture -- still lives outside
# the repository under the state dir. See lmstudio/AGENTS.md for the two
# accepted deviations (daemon-owned process, identity-by-path-not-digest).

LMSTUDIO_STATE_DIR="${LMSTUDIO_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/lmstudio}"
LMSTUDIO_LOG="${LMSTUDIO_LOG:-${LMSTUDIO_STATE_DIR}/server.log}"
LMSTUDIO_BASELINE_GPU_FILE="${LMSTUDIO_BASELINE_GPU_FILE:-${LMSTUDIO_STATE_DIR}/gpu-baseline-mib}"

# Host policy: loopback and a runtime-specific port distinct from the other
# servers in this tree (Ollama 11434, CUDA vLLM 8000/8001, vLLM-Metal 8021).
LMSTUDIO_HOST="${LMSTUDIO_HOST:-127.0.0.1}"
LMSTUDIO_PORT="${LMSTUDIO_PORT:-1234}"

# Path to the lms CLI, or empty. Only the override and a PATH lms are accepted;
# unlike the pinned-tarball runtimes there is no managed install location,
# because lms ships inside the desktop application (see install.sh).
lmstudio_bin() {
    if [[ -n "${LMSTUDIO_BIN:-}" ]]; then
        [[ -x "${LMSTUDIO_BIN}" ]] && printf '%s\n' "${LMSTUDIO_BIN}"
        return 0
    fi
    command -v lms 2> /dev/null || true
}

# lms CLI version (x.y.z), or empty. `lms version` output varies by build: some
# print a semver banner (v0.0.47), others only a CLI commit hash. Empty here is
# not fatal -- install.sh falls back to probing the v1 REST API for the real
# capability gate, since the version floor is about the LM Studio app's API, not
# the CLI build string.
lmstudio_version() {
    local exe="$1"
    { "${exe}" version 2>&1 |
        sed 's/\x1b\[[0-9;]*m//g' |
        grep -oE '[0-9]+\.[0-9]+\.[0-9]+' |
        head -1; } || true
}

lmstudio_version_at_least() {
    local actual="$1"
    local required="$2"
    [[ "$(printf '%s\n%s\n' "${required}" "${actual}" | sort -V | head -1)" == "${required}" ]]
}

# True when the v1 REST API endpoint responds, proving the LM Studio app is new
# enough regardless of the CLI's version string. Used as the capability gate
# when lmstudio_version cannot parse a semver from the CLI banner.
lmstudio_api_v1_ready() {
    local base
    base="$(lmstudio_api_base)"
    curl -sf --max-time 5 "${base}/api/v1/models" > /dev/null 2>&1
}

# Base URL of the OpenAI-compatible endpoint the desktop server exposes.
lmstudio_api_base() {
    local host="${LMSTUDIO_HOST}"
    case "${host}" in
        http://* | https://*) printf '%s\n' "${host%/}" ;;
        *) printf 'http://%s:%s\n' "${host}" "${LMSTUDIO_PORT}" ;;
    esac
}

# "running"/"stopped" from `lms server status --json`, plus the port it reports.
# Prints "<state> <port>". A daemon that is not up prints "stopped 0".
lmstudio_server_status() {
    local exe="$1"
    local json
    if ! json="$("${exe}" server status --json --quiet 2> /dev/null)"; then
        printf 'stopped 0\n'
        return 0
    fi
    printf '%s' "${json}" | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    print("stopped 0")
    sys.exit(0)
running = bool(data.get("running"))
port = int(data.get("port") or 0)
state = "running" if running else "stopped"
print(state, port)
'
}

# LM Link routes model resolution across devices on the network. When a remote
# peer is set as the preferred device, `lms load` resolves there instead of
# this machine -- the model runs on someone else's GPU. This tree serves models
# locally, so the launcher must refuse a remote-routed load by default.
#
# Prints one of:
#   local              LM Link off, or preferred device is this machine
#   remote <name>      preferred device is a connected peer (load would route away)
#   unknown            status could not be read (treat as non-fatal, warn only)
# Reads `lms link status --json`: deviceIdentifier is this host,
# preferredDeviceIdentifier is where an unqualified load resolves.
lmstudio_link_target() {
    local exe="$1"
    local json
    if ! json="$("${exe}" link status --json 2> /dev/null)"; then
        printf 'unknown\n'
        return 0
    fi
    printf '%s' "${json}" | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    print("unknown")
    sys.exit(0)

local_id = data.get("deviceIdentifier") or ""
preferred = data.get("preferredDeviceIdentifier") or ""
peers = data.get("peers") or []

# No preference, or it points at this device: an unqualified load stays local.
if not preferred or preferred == local_id:
    print("local")
    sys.exit(0)

# Preferred is a peer. Name it if we can, so the refusal is actionable.
name = preferred
for peer in peers:
    if peer.get("deviceIdentifier") == preferred:
        name = peer.get("deviceName") or preferred
        break
print("remote", name)
'
}

# Aggregate NVIDIA VRAM in MiB, or nothing on hosts without nvidia-smi. Apple
# Silicon has no separate VRAM counter, so callers fall back to process
# footprint there, matching the ollama and vllm-metal helpers.
lmstudio_gpu_mib() {
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2> /dev/null |
        awk '{sum += $1} END {print sum + 0}' || true
}

# Unified-memory total in GiB on Apple Silicon; 0 elsewhere.
lmstudio_mem_gib() {
    local bytes
    bytes="$(sysctl -n hw.memsize 2> /dev/null || printf '0')"
    printf '%s\n' "$((bytes / 1073741824))"
}

# Model config names available under models/.
lmstudio_list_models() {
    local dir="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/models}"
    local conf
    for conf in "${dir}"/*.conf; do
        [[ -e "${conf}" ]] || continue
        printf '  %s\n' "$(basename "${conf}" .conf)"
    done
}
