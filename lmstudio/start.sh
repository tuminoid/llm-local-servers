#!/usr/bin/env bash
#
# Bring up the LM Studio OpenAI-compatible server and load the configured model.
#
# Usage: start.sh <model-config-name>
#
# Reads models/<name>.conf. Environment variables win over the config file,
# since every conf value uses ${VAR:-default}.
#
# Unlike the other runtimes in this tree, the served model is owned by the
# long-running LM Studio service, not by a process group this script forks. So
# this launcher is a synchronous sequence of `lms` commands -- ensure the server
# is up, then load the model with the configured context and offload -- and
# returns once the model is loaded. `lms load` blocks until the weights are
# resident, so there is no detached process to supervise and no pidfile to hold;
# run.sh calls this and then confirms the OpenAI endpoint answers. stop.sh tears
# the model and service down explicitly. See lmstudio/AGENTS.md for this
# accepted deviation from the pidfile/process-group convention.
#
# shellcheck disable=SC2154  # LMSTUDIO_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    lmstudio_list_models >&2
    exit 1
fi
MODEL_CONF="$1"
CONF_FILE="${SCRIPT_DIR}/models/${MODEL_CONF}.conf"

if [[ ! -f "${CONF_FILE}" ]]; then
    printf 'error: no such model config: %s\n' "${CONF_FILE}" >&2
    printf 'available:\n' >&2
    lmstudio_list_models >&2
    exit 1
fi

# Declared before sourcing so a conf that omits a key fails validation rather
# than expanding to nothing, and so env overrides survive ${VAR:-default}.
LMSTUDIO_MODEL_KEY="${LMSTUDIO_MODEL_KEY:-}"
LMSTUDIO_SERVED_NAME="${LMSTUDIO_SERVED_NAME:-}"
LMSTUDIO_FORMAT="${LMSTUDIO_FORMAT:-}"
LMSTUDIO_CONTEXT_LENGTH="${LMSTUDIO_CONTEXT_LENGTH:-}"
LMSTUDIO_MIN_VERSION="${LMSTUDIO_MIN_VERSION:-0.4.0}"

# shellcheck source=models/qwen3.8-27b-gguf.conf disable=SC1091
source "${CONF_FILE}"

for var in LMSTUDIO_MODEL_KEY LMSTUDIO_SERVED_NAME LMSTUDIO_FORMAT LMSTUDIO_CONTEXT_LENGTH; do
    if [[ -z "${!var}" ]]; then
        printf 'error: %s is empty; check %s\n' "${var}" "${CONF_FILE}" >&2
        exit 1
    fi
done
if [[ ! "${LMSTUDIO_CONTEXT_LENGTH}" =~ ^[1-9][0-9]*$ ]]; then
    printf 'error: LMSTUDIO_CONTEXT_LENGTH must be a positive integer\n' >&2
    exit 1
fi

case "${LMSTUDIO_FORMAT}" in
    gguf) ;;
    mlx)
        if [[ "$(uname -s)/$(uname -m)" != "Darwin/arm64" ]]; then
            printf 'error: the MLX runtime requires macOS on Apple Silicon\n' >&2
            printf 'this config (%s) is Darwin/arm64 only\n' "${MODEL_CONF}" >&2
            exit 1
        fi
        ;;
    *)
        printf 'error: unsupported LMSTUDIO_FORMAT: %s (want gguf or mlx)\n' \
            "${LMSTUDIO_FORMAT}" >&2
        exit 1
        ;;
esac

# Host policy, not model facts (AGENTS.md): loopback bind and offload. GPU
# offload defaults to max (offload all layers); override with LMSTUDIO_GPU
# (0-1, off, max). max matches the other runtimes' "fill the accelerator"
# default and lets LM Studio's own guardrails refuse an unfittable load.
LMSTUDIO_GPU="${LMSTUDIO_GPU:-max}"

LMSTUDIO_EXE="$(lmstudio_bin)"
if [[ -z "${LMSTUDIO_EXE}" ]]; then
    printf 'error: lms not found; run make lmstudio-install\n' >&2
    exit 1
fi
# A parseable semver is enforced against the floor; an unparseable one (some
# lms builds print only a commit hash) defers to the v1 API check install.sh
# describes, rather than blocking a working service.
actual_version="$(lmstudio_version "${LMSTUDIO_EXE}")"
if [[ -n "${actual_version}" ]] \
    && ! lmstudio_version_at_least "${actual_version}" "${LMSTUDIO_MIN_VERSION}"; then
    printf 'error: %s needs lms >= %s; found %s at %s\n' \
        "${LMSTUDIO_SERVED_NAME}" "${LMSTUDIO_MIN_VERSION}" \
        "${actual_version}" "${LMSTUDIO_EXE}" >&2
    printf 'run: make lmstudio-install\n' >&2
    exit 1
fi
actual_version="${actual_version:-unknown}"

base="$(lmstudio_api_base)"

# Refuse to compete with a model already loaded in the service: on a shared
# desktop the operator may have loaded something in the GUI, and this launcher
# would otherwise silently load a second model. A clean managed start expects an
# idle service.
read -r server_state server_port < <(lmstudio_server_status "${LMSTUDIO_EXE}")
if [[ "${server_state}" == "running" ]]; then
    loaded_count="$("${LMSTUDIO_EXE}" ps --json 2> /dev/null | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    print(0)
    sys.exit(0)
if isinstance(data, dict):
    data = data.get("models") or data.get("data") or []
print(len(data))
' || printf '0')"
    if [[ "${loaded_count}" != "0" ]]; then
        printf 'error: the LM Studio service already has %s model(s) loaded\n' \
            "${loaded_count}" >&2
        printf 'unload them first: make lmstudio-stop (or lms unload --all)\n' >&2
        exit 1
    fi
    if [[ -n "${server_port}" && "${server_port}" != "0" \
        && "${server_port}" != "${LMSTUDIO_PORT}" ]]; then
        printf 'error: LM Studio server already running on port %s, wanted %s\n' \
            "${server_port}" "${LMSTUDIO_PORT}" >&2
        printf 'stop it first (make lmstudio-stop) or set LMSTUDIO_PORT=%s\n' \
            "${server_port}" >&2
        exit 1
    fi
fi

mkdir -p "${LMSTUDIO_STATE_DIR}"
lmstudio_gpu_mib > "${LMSTUDIO_BASELINE_GPU_FILE}"

# A parseable launch profile, mirroring the other runtimes' `config:`/`host:`
# lines so bench.py can verify the live operating point against the conf.
printf 'config: model=%s served=%s format=%s context=%s\n' \
    "${LMSTUDIO_MODEL_KEY}" "${LMSTUDIO_SERVED_NAME}" \
    "${LMSTUDIO_FORMAT}" "${LMSTUDIO_CONTEXT_LENGTH}"
printf 'host: bind=%s port=%s gpu=%s version=%s\n' \
    "${LMSTUDIO_HOST}" "${LMSTUDIO_PORT}" "${LMSTUDIO_GPU}" "${actual_version}"

# Start the server on the configured loopback port. Idempotent: a no-op if it is
# already up on this port. No --cors, no non-loopback bind (bind-to-loopback
# invariant); LM Studio's endpoint has no authentication by default.
printf 'starting LM Studio server on %s:%s\n' "${LMSTUDIO_HOST}" "${LMSTUDIO_PORT}"
"${LMSTUDIO_EXE}" server start --port "${LMSTUDIO_PORT}"

# Guard against LM Link routing the load to a networked device. When a remote
# peer is the preferred device, `lms load` resolves the model there and it runs
# on that machine's GPU, not this one -- which silently defeats a local serving
# benchmark. This tree serves locally, so refuse by default; set
# LMSTUDIO_ALLOW_REMOTE_DEVICE=1 to opt into a remote-routed load deliberately.
link_target="$(lmstudio_link_target "${LMSTUDIO_EXE}")"
case "${link_target}" in
    remote*)
        remote_name="${link_target#remote }"
        if [[ "${LMSTUDIO_ALLOW_REMOTE_DEVICE:-0}" != "1" ]]; then
            printf 'error: LM Link preferred device is remote (%s)\n' "${remote_name}" >&2
            printf 'lms load would run the model on that device, not this host\n' >&2
            printf 'make it local: lms link set-preferred-device <this-device-id>\n' >&2
            printf '  (or: lms link disable), then retry\n' >&2
            printf 'to load on the remote device on purpose: LMSTUDIO_ALLOW_REMOTE_DEVICE=1\n' >&2
            exit 1
        fi
        printf 'warning: LMSTUDIO_ALLOW_REMOTE_DEVICE=1; loading on remote device %s\n' \
            "${remote_name}" >&2
        ;;
    unknown)
        printf 'warning: could not read LM Link status; assuming local load\n' >&2
        ;;
    *)
        # "local": LM Link off or preferred device is this host. Proceed.
        ;;
esac

# Load the configured artifact with the pinned context and offload, assigning
# the served identifier so /v1/models and lms ps report a stable name.
printf 'loading %s as "%s" (context %s, gpu %s)\n' \
    "${LMSTUDIO_MODEL_KEY}" "${LMSTUDIO_SERVED_NAME}" \
    "${LMSTUDIO_CONTEXT_LENGTH}" "${LMSTUDIO_GPU}"
# --yes is mandatory, not a convenience: `lms load` has no per-format key
# (the @quant suffix is a `lms get` download filter only, and neither the
# store path nor indexedModelIdentifier is a loadable key), so when a repo
# key resolves to more than one artifact -- e.g. an MLX build local and a
# GGUF build reachable over LM Link -- an interactive `lms load` blocks on a
# TTY model picker forever under a non-interactive launcher. --yes resolves
# it to the preferred/local device's match; a wrong pick is then caught by
# the post-load identity check (bench.py _model_identity), never by a hang.
"${LMSTUDIO_EXE}" load "${LMSTUDIO_MODEL_KEY}" \
    --context-length "${LMSTUDIO_CONTEXT_LENGTH}" \
    --gpu "${LMSTUDIO_GPU}" \
    --identifier "${LMSTUDIO_SERVED_NAME}" \
    --yes

printf 'loaded; api %s (OpenAI-compatible at %s/v1)\n' "${base}" "${base}"
