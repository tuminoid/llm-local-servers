#!/usr/bin/env bash
#
# Run the vLLM-Metal OpenAI-compatible server in the foreground.
#
# Usage: start.sh <model-config-name>
#
# Reads models/<name>.conf. Environment variables win over the config file,
# since every conf value uses ${VAR:-default}.
#
# Prefer run.sh for anything but debugging: it detaches the server so terminal
# signals cannot reach it.
#
# shellcheck disable=SC2154  # VLLM_METAL_* paths come from sourced lib.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    vllm_metal_list_models >&2
    exit 1
fi
MODEL_CONF="$1"
CONF_FILE="${SCRIPT_DIR}/models/${MODEL_CONF}.conf"

if [[ ! -f "${CONF_FILE}" ]]; then
    printf 'error: no such model config: %s\n' "${CONF_FILE}" >&2
    printf 'available:\n' >&2
    vllm_metal_list_models >&2
    exit 1
fi

# Declared before sourcing so a conf that omits a key fails validation below
# rather than expanding to nothing, and so env overrides survive the conf's
# ${VAR:-default} expansion.
VLLM_MODEL_REPO="${VLLM_MODEL_REPO:-}"
VLLM_MODEL_REVISION="${VLLM_MODEL_REVISION:-}"
VLLM_SERVED_NAME="${VLLM_SERVED_NAME:-}"
VLLM_MAX_LEN="${VLLM_MAX_LEN:-}"
VLLM_REASONING_PARSER="${VLLM_REASONING_PARSER:-}"
VLLM_TOOL_PARSER="${VLLM_TOOL_PARSER:-}"
VLLM_KV_BYTES_PER_TOKEN="${VLLM_KV_BYTES_PER_TOKEN:-}"
VLLM_KV_BYTES_PER_TOKEN_APC="${VLLM_KV_BYTES_PER_TOKEN_APC:-}"
VLLM_HF_OVERRIDES="${VLLM_HF_OVERRIDES:-}"
VLLM_STRUCTURED_OUTPUTS_CONFIG="${VLLM_STRUCTURED_OUTPUTS_CONFIG:-}"
VLLM_CHAT_TEMPLATE="${VLLM_CHAT_TEMPLATE:-}"

# shellcheck source=models/ornith1.5-35b-a3b-4bit.conf disable=SC1091
source "${CONF_FILE}"

for var in VLLM_MODEL_REPO VLLM_MODEL_REVISION VLLM_SERVED_NAME VLLM_MAX_LEN; do
    if [[ -z "${!var}" ]]; then
        printf 'error: %s is empty; check %s\n' "${var}" "${CONF_FILE}" >&2
        exit 1
    fi
done

# Weights are served from the explicit pull.sh directory, never from an
# implicit HF cache download at startup. The HF cache stays read-only.
MODEL_DIR="${VLLM_METAL_MODELS_DIR}/${MODEL_CONF}"
if [[ ! -f "${MODEL_DIR}/config.json" ]]; then
    printf 'error: model weights not present at %s\n' "${MODEL_DIR}" >&2
    printf 'run: make vllm-metal-pull MODEL=%s\n' "${MODEL_CONF}" >&2
    exit 1
fi

# Everything below is host policy, not model facts (AGENTS.md).
#
# Loopback only; 8021 is this runtime's reserved port, distinct from
# Ollama's 11434 and the CUDA vLLM tunnel's 8001.
VLLM_HOST="${VLLM_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8021}"

# Prefix caching. Every model conf pins its decided default explicitly
# (dense: 1, their measured engine default; hybrids that passed the align
# gate: 1, align-mode APC adopted at plugin dev20260826100011 on the
# since-dropped qwen3.6 (2026-08-26) and qwen3.8 (2026-08-27) profiles) so a
# core bump cannot silently flip the resolved mode -- vLLM main resolves
# supported hybrids to align-mode APC ON, unlike the 0.27.1 pin's
# hybrid-off default. Environment wins over the conf; empty (a conf
# without a pin) falls back to the engine default. Opting a hybrid in changes its
# numerics (the align kernel path diverges from the default path at the
# first generated token) and adds GDN state to its per-token pool cost
# (about 2x on plugin 0.29.0, 1-3% on 0.30.0's shared cache); both the divergent-conversation correctness gate and the cost math for
# that are in README.md. A hybrid conf that supports the opt-in declares
# VLLM_KV_BYTES_PER_TOKEN_APC so the budget below stays honest.
VLLM_PREFIX_CACHING="${VLLM_PREFIX_CACHING:-}"

# Memory budget. On unified memory this fraction is the engine's whole
# footprint budget, resolved by the plugin against Metal's recommended
# working-set limit (~106 GB on a 128 GB host), and the paged-KV planner
# sizes the pool from it up front (--gpu-memory-utilization is wired on the
# Metal paged path since plugin PR #514). That up-front bound is the
# property whose absence in the Ollama MLX runner hard-reset this host.
#
# 0.91 is the measured four-full-context operating point for the retired
# qwen3.8 8-bit checkpoint on the 128 GB M5 Max: 1,061,760-token pool (4.05x a native 262,144
# sequence), 98 GB planned footprint, ~28 GB left for everything else,
# smoke-tested under load. The budget buys KV capacity only -- prefill and
# decode rates measured identical at 0.60, 0.80, and this point. The
# engine refuses to start when a full-length sequence does not fit, so a
# too-high fraction fails loudly at startup instead of taking the host
# down mid-prefill.
#
# seqs 5 is the measured decode sweet spot on that pool: aggregate tok/s
# by admitted streams ran 65.9 (4) / 76-79 (5) / 66-72 (6, consistently
# below 5 across repeats) / 84.7 (8, at ~10.6 per stream). Five jobs keep
# ~15-16 tok/s each, and five stay preemption-free while they average
# under ~212k tokens; four full 262k sequences fit outright.
MEM_GIB="$(vllm_metal_mem_gib)"
if ((MEM_GIB >= 96)); then
    VLLM_MAX_SEQS="${VLLM_MAX_SEQS:-5}"
    VLLM_MAX_BATCHED="${VLLM_MAX_BATCHED:-8192}"
    UTIL_CAP="0.91"
else
    # Smaller unified-memory hosts keep a larger proportional reserve and
    # less concurrency; both are starting points, not measured optima.
    VLLM_MAX_SEQS="${VLLM_MAX_SEQS:-2}"
    VLLM_MAX_BATCHED="${VLLM_MAX_BATCHED:-4096}"
    UTIL_CAP="0.50"
fi

# When the config declares the model's paged-KV cost, size the budget to
# exactly what VLLM_MAX_SEQS full-native-context requests need instead of
# defaulting to the cap. The engine's own breakdown (cache_policy.py) is
#   usable = fraction * metal_limit
#   kv_budget = usable - weights - overhead - GDN reserve
# inverted here with weights measured from the pulled directory, the Metal
# recommended working-set limit queried from MLX, and a flat 5 GB standing
# in for the engine's measured ~4.3 GB overhead plus GDN reserve. The
# result is rounded up to the next 0.01 and clamped to the host cap, so a
# KV-cheap model (hybrid MoE at 20 KiB/token) gets a low bound and a
# KV-expensive one lands back on the cap. Verified against the planner on
# the since-dropped profiles: qwen3.6-35b-a3b-4bit (align APC, plugin
# 0.30.0) computed 0.46 -> 1,403,241-token pool >= 5 x 262,144, the pool
# ornith1.5-35b-a3b-4bit plans too, while qwen3.8-27b-4bit computed past
# the cap and kept 0.91.
if [[ -z "${VLLM_GPU_UTIL:-}" && -n "${VLLM_KV_BYTES_PER_TOKEN}" ]]; then
    # Align-mode prefix caching makes every pool block carry GDN state
    # besides its KV pages, so the effective per-token cost is the conf's
    # APC figure, not the plain paged-KV one.
    KV_BYTES_EFFECTIVE="${VLLM_KV_BYTES_PER_TOKEN}"
    if [[ "${VLLM_PREFIX_CACHING}" == "1" && -n "${VLLM_KV_BYTES_PER_TOKEN_APC}" ]]; then
        KV_BYTES_EFFECTIVE="${VLLM_KV_BYTES_PER_TOKEN_APC}"
    fi
    METAL_LIMIT="$("$(dirname "$(vllm_metal_bin)")/python" - << 'EOF' 2> /dev/null || true
import mlx.core as mx
print(mx.device_info()["max_recommended_working_set_size"])
EOF
    )"
    WEIGHTS_KIB="$(du -sk "${MODEL_DIR}" | cut -f1)"
    if [[ "${METAL_LIMIT}" =~ ^[0-9]+$ ]]; then
        VLLM_GPU_UTIL="$(awk -v limit="${METAL_LIMIT}" -v wkib="${WEIGHTS_KIB}" \
            -v kv="${KV_BYTES_EFFECTIVE}" -v seqs="${VLLM_MAX_SEQS}" \
            -v len="${VLLM_MAX_LEN}" -v cap="${UTIL_CAP}" 'BEGIN {
                need = wkib * 1024 + 5e9 + seqs * len * kv
                frac = int(need / limit * 100 + 1) / 100
                printf "%.2f", (frac < cap) ? frac : cap
            }')"
    fi
fi
VLLM_GPU_UTIL="${VLLM_GPU_UTIL:-${UTIL_CAP}}"

VLLM_EXE="$(vllm_metal_bin)"
if [[ -z "${VLLM_EXE}" ]]; then
    printf 'error: vllm-metal venv not found at %s\n' "${VLLM_METAL_VENV}" >&2
    printf 'run: make vllm-metal-install\n' >&2
    exit 1
fi
# Pin guard. Start never installs; the venv moves only through install.sh, so
# a venv that drifted from the Makefile pins would otherwise serve a retired
# release under the documented rates. make passes both pins; a manual start
# without them skips the check. The local version segment (+cpu) is not part
# of the pin.
if [[ -n "${VLLM_METAL_VERSION:-}" || -n "${VLLM_METAL_VLLM_VERSION:-}" ]]; then
    read -r INSTALLED_PLUGIN INSTALLED_VLLM < <("$(dirname "${VLLM_EXE}")/python" -c \
        'from importlib.metadata import version
print(version("vllm-metal"), version("vllm").split("+")[0])')
    if [[ -n "${VLLM_METAL_VERSION:-}" && "${INSTALLED_PLUGIN}" != "${VLLM_METAL_VERSION}" ]] \
        || [[ -n "${VLLM_METAL_VLLM_VERSION:-}" && "${INSTALLED_VLLM}" != "${VLLM_METAL_VLLM_VERSION}" ]]; then
        printf 'error: %s holds vllm-metal %s / vllm %s, the pins are %s / %s\n' \
            "${VLLM_METAL_VENV}" "${INSTALLED_PLUGIN}" "${INSTALLED_VLLM}" \
            "${VLLM_METAL_VERSION:-any}" "${VLLM_METAL_VLLM_VERSION:-any}" >&2
        printf 'run: make vllm-metal-install\n' >&2
        exit 1
    fi
fi
# The venv's bin must be on PATH, not merely used to locate the entry point.
PATH="$(dirname "${VLLM_EXE}"):${PATH}"
export PATH

args=(
    serve "${MODEL_DIR}"
    --served-model-name "${VLLM_SERVED_NAME}"
    --max-model-len "${VLLM_MAX_LEN}"
    --max-num-seqs "${VLLM_MAX_SEQS}"
    --max-num-batched-tokens "${VLLM_MAX_BATCHED}"
    --gpu-memory-utilization "${VLLM_GPU_UTIL}"
    --host "${VLLM_HOST}"
    --port "${VLLM_PORT}"
)
# Text only: the fleet's clients send no images, video or audio. The flag
# zeroes every modality limit of a multimodal checkpoint, so vLLM builds
# no HF image processor at startup (whose files some conversions ship
# broken or not at all) and skips the vision tower where the model class
# allows it. Text-only architectures ignore it.
args+=(--language-model-only)
if [[ -n "${VLLM_REASONING_PARSER}" ]]; then
    args+=(--reasoning-parser "${VLLM_REASONING_PARSER}")
fi
if [[ -n "${VLLM_TOOL_PARSER}" ]]; then
    args+=(--enable-auto-tool-choice --tool-call-parser "${VLLM_TOOL_PARSER}")
fi
if [[ "${VLLM_PREFIX_CACHING}" == "1" ]]; then
    # Cached-token counts in usage (prompt_tokens_details) are off by
    # default; the conversation benchmark measures cache reuse from them.
    args+=(--enable-prefix-caching --enable-prompt-tokens-details)
elif [[ "${VLLM_PREFIX_CACHING}" == "0" ]]; then
    args+=(--no-enable-prefix-caching)
fi
if [[ -n "${VLLM_HF_OVERRIDES}" ]]; then
    # JSON config patch, e.g. a static YaRN rope_parameters block for a
    # context-extended profile (same shape as the CUDA 512k conf).
    args+=(--hf-overrides "${VLLM_HF_OVERRIDES}")
fi
# Structured-output grammar options, e.g.
# {"backend":"xgrammar","disable_any_whitespace":true} where a model fills
# the schema grammar's whitespace until the budget runs out. vLLM rejects
# disable_any_whitespace under the default "auto" backend at startup. One
# argv element; vLLM validates the shape.
if [[ -n "${VLLM_STRUCTURED_OUTPUTS_CONFIG}" ]]; then
    args+=(--structured-outputs-config "${VLLM_STRUCTURED_OUTPUTS_CONFIG}")
fi

# A chat template override, resolved beside these scripts. A model fact: the
# file is the checkpoint's template with the defect fixed.
if [[ -n "${VLLM_CHAT_TEMPLATE}" ]]; then
    if [[ ! -f "${SCRIPT_DIR}/${VLLM_CHAT_TEMPLATE}" ]]; then
        printf 'error: no such chat template: %s\n' "${SCRIPT_DIR}/${VLLM_CHAT_TEMPLATE}" >&2
        exit 1
    fi
    args+=(--chat-template "${SCRIPT_DIR}/${VLLM_CHAT_TEMPLATE}")
fi

mkdir -p "$(dirname "${VLLM_METAL_PIDFILE}")"

# Refuse to overwrite a live server's pidfile; it is stop.sh's only handle.
running_pid="$(vllm_metal_pid)"
if [[ -n "${running_pid}" ]]; then
    printf 'error: a server is already running (pid %s)\n' "${running_pid}" >&2
    printf 'stop it first, or set VLLM_METAL_PIDFILE for a separate handle\n' >&2
    exit 1
fi

printf '%s\n' "$$" > "${VLLM_METAL_PIDFILE}"

printf 'starting %s as "%s" on %s:%s\n' \
    "${MODEL_DIR}" "${VLLM_SERVED_NAME}" "${VLLM_HOST}" "${VLLM_PORT}"
printf 'host: %s GiB unified memory -> util %s, seqs %s, batched %s, max-len %s, NAX %s, prefix-caching %s\n' \
    "${MEM_GIB}" "${VLLM_GPU_UTIL}" "${VLLM_MAX_SEQS}" "${VLLM_MAX_BATCHED}" \
    "${VLLM_MAX_LEN}" "$([[ "${VLLM_METAL_DISABLE_NAX:-0}" == "1" ]] && echo disabled || echo auto)" \
    "${VLLM_PREFIX_CACHING:-default}"

exec "${VLLM_EXE}" "${args[@]}"
