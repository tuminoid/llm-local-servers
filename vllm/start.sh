#!/usr/bin/env bash
#
# Run a vLLM OpenAI-compatible server in the foreground.
#
# Usage: start.sh <model-config-name>
#
# Reads models/<name>.conf. Environment variables win over the config file,
# since every conf value uses ${VAR:-default}.
#
# Prefer run.sh for anything but debugging: it detaches the server so terminal
# signals cannot reach it.
#
# shellcheck disable=SC2154  # VLLM_* paths are defined in lib.sh, which the
# lint wrapper cannot follow (it runs without -x), so it sees them as unassigned.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

if [[ -z "${1:-}" ]]; then
    printf 'usage: %s <model-config-name>\n' "$(basename "$0")" >&2
    printf 'available:\n' >&2
    vllm_list_models >&2
    exit 1
fi
MODEL_CONF="$1"
CONF_FILE="${SCRIPT_DIR}/models/${MODEL_CONF}.conf"

if [[ ! -f "${CONF_FILE}" ]]; then
    printf 'error: no such model config: %s\n' "${CONF_FILE}" >&2
    printf 'available:\n' >&2
    vllm_list_models >&2
    exit 1
fi

# Declared before sourcing so shellcheck can see them and so a conf file that
# omits a key fails the validation below rather than expanding to nothing.
#
# Each keeps any value already in the environment, because a bare VAR="" would
# clobber the export before the conf's ${VAR:-default} ever sees it, silently
# reducing every documented env override to the file default. Unset still
# becomes empty, so the validation below is unaffected.
VLLM_MODEL="${VLLM_MODEL:-}"
VLLM_MODEL_REVISION="${VLLM_MODEL_REVISION:-}"
VLLM_SERVED_NAME="${VLLM_SERVED_NAME:-}"
VLLM_MAX_LEN="${VLLM_MAX_LEN:-}"
VLLM_HF_OVERRIDES="${VLLM_HF_OVERRIDES:-}"
VLLM_ALLOW_LONG_MAX_MODEL_LEN="${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-}"
VLLM_KV_DTYPE="${VLLM_KV_DTYPE:-}"
# Prefix caching: every model conf pins its proven value explicitly
# (regular attention: 1, matching the 0.27.1 engine default its
# benchmarked state was measured under; hybrid GDN/Mamba: 0) because
# vLLM main resolves supported hybrids to align-mode APC ON, unlike the
# 0.27.1 pin's hybrid-off default, and an unset knob would flip silently
# on a core bump. Environment wins over the conf; empty passes no flag
# and keeps the engine default.
VLLM_PREFIX_CACHING="${VLLM_PREFIX_CACHING:-}"
VLLM_SPECULATIVE_CONFIG="${VLLM_SPECULATIVE_CONFIG:-}"
VLLM_ATTN_AUTO="${VLLM_ATTN_AUTO:-}"
VLLM_MLA="${VLLM_MLA:-}"
VLLM_MAX_SEQS="${VLLM_MAX_SEQS:-}"
VLLM_MAX_BATCHED="${VLLM_MAX_BATCHED:-}"
VLLM_GPU_UTIL="${VLLM_GPU_UTIL:-}"
VLLM_VRAM_RESERVE_MIB="${VLLM_VRAM_RESERVE_MIB:-}"
VLLM_REASONING_PARSER="${VLLM_REASONING_PARSER:-}"
VLLM_REASONING_PLUGIN="${VLLM_REASONING_PLUGIN:-}"
VLLM_TOOL_PARSER="${VLLM_TOOL_PARSER:-}"
VLLM_TOOL_PLUGIN="${VLLM_TOOL_PLUGIN:-}"

# shellcheck source=models/qwen3.5-4b-awq.conf disable=SC1091
source "${CONF_FILE}"

# Not in the model conf: everything below describes the host, not the model.
# A model conf must stay portable between machines (AGENTS.md), so the
# launcher derives these and the environment still wins over both.

VLLM_CAP="$(vllm_compute_cap)"
# Overridable so both memory profiles can be exercised on one machine: the
# profile split is on this number, so faking it is the only way to see the
# branch this host does not take. Detection is otherwise unchanged.
VLLM_VRAM_MIB="${VLLM_VRAM_MIB:-$(vllm_gpu_total_mib)}"

# fp8 KV needs SM89+ silicon. The model conf states a *preference*, because on a
# small card fp8 may be the only way its context fits; on older hardware there is
# no fp8 path at all and we degrade rather than fail (AGENTS.md).
# Measured refusals on A100 (sm_80), both backends, so this is hardware and not
# a backend choice:
#   FLASH_ATTN : "not valid for this configuration ... kv_cache_dtype not supported"
#   TRITON_ATTN: "FP8 KV cache is not supported ... native FP8 (fp8e4nv) requires SM89+"
if [[ "${VLLM_KV_DTYPE}" == fp8* ]] && ((VLLM_CAP > 0 && VLLM_CAP < 89)); then
    printf 'note: fp8 KV unsupported below sm_89 (this GPU is sm_%s); using bf16 KV\n' \
        "${VLLM_CAP}" >&2
    printf 'note: context may not fit -- vLLM needs KV for one whole max-model-len sequence\n' >&2
    VLLM_KV_DTYPE="auto"
fi

# Attention backend follows from the KV dtype, which is why these are one
# decision and not two.
#
# With fp8 KV, FlashAttention has no code path, leaving FlashInfer (JIT, needs
# nvcc) or Triton (own LLVM toolchain, no toolkit, roughly half the prefill
# throughput). With bf16 KV, FlashAttention is prebuilt and fastest, so prefer
# it and avoid JIT entirely.
#
# FlashInfer is additionally gated on sm_89+: its kernels fail to compile for
# sm_80 even with a working nvcc, erroring inside libcudacxx/cooperative_groups
# while building the arch-80 variant.
# Some models must not be given a backend at all. Which backends are legal
# depends on the model's architecture as well as the host -- attention family,
# head size, multimodal prefix attention, attention sinks -- and the launcher
# deliberately does not read config.json to find out (see Known limits in
# AGENTS.md). Such a model conf sets VLLM_ATTN_AUTO=1 and vLLM's own
# capability-aware priority list picks instead, which it does correctly.
#
# This is not a preference. validate_configuration *raises* on a backend named
# explicitly where it would merely skip one it chose itself, so a wrong guess
# aborts engine init rather than degrading. Both live configs hit it:
#
#   glm4.7-flash-awq (MLA, a disjoint backend family):
#     ValueError: Selected backend AttentionBackendEnum.FLASH_ATTN is not valid
#     for this configuration. Reason: ['MLA not supported']
#
#   gemma4-26b-a4b-awq (multimodal PrefixLM bidirectional attention):
#     Reason: ['partial multimodal token full attention not supported',
#     'mm_prefix (PrefixLM bidirectional attention) requires FlashAttention v4,
#     which does not resolve for this head_size']
#
# In the second case the fallback exists and is found automatically:
# TRITON_ATTN supports mm_prefix unconditionally where FLASH_ATTN needs FA v4.
#
# MLA implies it, because an MLA model can never take a dense backend.
if [[ -n "${VLLM_MLA}" ]]; then
    VLLM_ATTN_AUTO=1
fi

if [[ -z "${VLLM_ATTN_BACKEND:-}" && -z "${VLLM_ATTN_AUTO}" ]]; then
    if [[ "${VLLM_KV_DTYPE}" == fp8* ]]; then
        if ((VLLM_CAP >= 89)) \
            && { [[ -x "${CUDA_HOME:-/usr/local/cuda}/bin/nvcc" ]] || command -v nvcc > /dev/null 2>&1; }; then
            VLLM_ATTN_BACKEND="FLASHINFER"
        else
            VLLM_ATTN_BACKEND="TRITON_ATTN"
        fi
    else
        VLLM_ATTN_BACKEND="FLASH_ATTN"
    fi
fi

# The sampler is a separate FlashInfer entry point from the attention backend
# and is JIT-only, so it fails on hosts where FlashInfer cannot build even when
# attention uses another backend. That aborts engine init for no benefit.
if ((VLLM_CAP > 0 && VLLM_CAP < 89)); then
    export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
fi

# Host memory policy. Two profiles, both measured rather than guessed. A
# dedicated 80 GB datacentre card wants the surplus KV turned into concurrent
# sequences; a 12 GB desktop card has to be told how much of itself to use,
# because the answer is "nearly all of it" only when the display is elsewhere.
# Budget is footprint, so the utilization figure sets total memory use either
# way.
#
# MLA is the exception to "budget is footprint", so record whether the caller
# pinned utilization before the profile defaults overwrite the variable.
VLLM_GPU_UTIL_SET="${VLLM_GPU_UTIL:+1}"

if ((VLLM_VRAM_MIB >= 24576)); then
    VLLM_GPU_UTIL="${VLLM_GPU_UTIL:-0.98}"
    VLLM_MAX_SEQS="${VLLM_MAX_SEQS:-8}"
    VLLM_MAX_BATCHED="${VLLM_MAX_BATCHED:-8192}"
else
    # Small cards get an absolute reserve rather than a fixed fraction, because
    # what has to be left behind is a fixed quantity -- the display, the
    # compositor, another process -- not a proportion of the card. A fraction
    # tuned on 12 GB is wrong on 10 GB and wrong again on 16 GB; a reserve is
    # right on all three. 1024 MiB resolves to 0.916 on a 12227 MiB card, 0.900
    # on 10240 MiB, 0.938 on 16384 MiB.
    #
    # This replaced a flat 0.80, which had no measured refusal behind it.
    # Measured on sm_120 with qwen3.5-4b-awq, whose native 262144 needs 4.06 GiB
    # of KV: 0.80 offers 3.17 GiB and refuses to start, 0.92 offers 4.55 GiB and
    # serves it. 0.80 also cannot hold 131072 at two sequences (needs 2.0x pool,
    # gets 1.53x), so the old profile could not have both full context and
    # concurrency; 0.916 has 2.20x. Benchmarked clean at 0.92 and at 0.958, no
    # OOM, throughput unchanged, peak resident 9684 and 10142 MiB of 12227.
    #
    # Raise the reserve on a host whose display lives on this GPU. The machine
    # this was tuned on runs its desktop on the CPU's integrated graphics, so
    # the card idles at 14 MiB and 1 GiB is generous; a card driving a 4K
    # desktop needs appreciably more.
    VLLM_VRAM_RESERVE_MIB="${VLLM_VRAM_RESERVE_MIB:-1024}"
    if [[ -z "${VLLM_GPU_UTIL}" ]] && ((VLLM_VRAM_MIB > VLLM_VRAM_RESERVE_MIB)); then
        VLLM_GPU_UTIL="$(awk \
            "BEGIN{printf \"%.3f\", (${VLLM_VRAM_MIB} - ${VLLM_VRAM_RESERVE_MIB}) / ${VLLM_VRAM_MIB}}")"
    fi
    VLLM_GPU_UTIL="${VLLM_GPU_UTIL:-0.80}"

    # Two sequences, not one. Measured on sm_120 with qwen3.5-4b-awq: two
    # concurrent streams give 1.92x aggregate decode (15.88 against 8.27 tok/s),
    # and four give the same 1.92x, so the cap was what bound and not the card.
    # At max-num-seqs 1 both 2 and 4 streams flatten to exactly 1.00x by
    # queueing. The cost is per-sequence rather than per-token state -- for that
    # model 48 MiB of GatedDeltaNet recurrent state per sequence -- so it scales
    # with this number and not with context.
    VLLM_MAX_SEQS="${VLLM_MAX_SEQS:-2}"
    VLLM_MAX_BATCHED="${VLLM_MAX_BATCHED:-2048}"
    # Reduces allocator fragmentation on a card with little slack. Deliberately
    # NOT set on the large-card profile: at 0.98 utilization the expandable
    # reservation overshoots and the run dies in _allocate_kv_cache_tensors with
    # ~1.6 GiB "reserved but unallocated", even though memory profiling had just
    # sized the KV cache successfully. Measured on A100: 0.98 works without it
    # and OOMs with it. It is safe at the small-card utilizations above: 0.916,
    # 0.92 and 0.958 all started and benchmarked clean on sm_120 with it set.
    export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
fi

# MLA breaks the assumption that startup profiling sees every large allocation.
# Its chunked-prefill context path allocates a workspace *lazily*, on the first
# prefill long enough to need chunking, and vLLM sizes that for up to 64k tokens
# -- its own comment in determine_chunked_prefill_workspace_size puts the
# up-projected context at gigabytes. None of it is reserved at startup, so the
# KV cache is free to consume the space it will later need.
#
# The failure is therefore not at startup but at the first long prompt, and it
# kills the engine rather than failing the request. Measured on A100 with
# glm4.7-flash-awq at 0.98: a ~47k-token prefill dies with
#   torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 342.00 MiB.
#   GPU 0 has a total capacity of 79.25 GiB of which 237.88 MiB is free.
# followed by EngineDeadError, while an ~11k prefill had already succeeded.
#
# 0.92 is measured to survive the same benchmark. It costs nothing real: the
# canonical A100 run still held 1,050,624 tokens, 5.18x a full-length
# sequence, so the space given back was never addressable anyway.
if [[ -n "${VLLM_MLA}" && -z "${VLLM_GPU_UTIL_SET}" ]] \
    && awk "BEGIN{exit !(${VLLM_GPU_UTIL} > 0.92)}"; then
    VLLM_GPU_UTIL="0.92"
fi

# Loopback only. vLLM defaults to 0.0.0.0 with NO authentication, which would
# expose an unauthenticated inference endpoint to the whole network. Override
# deliberately, and pair with --api-key if you do.
VLLM_HOST="${VLLM_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8000}"

for var in VLLM_MODEL VLLM_MODEL_REVISION VLLM_SERVED_NAME VLLM_MAX_LEN VLLM_GPU_UTIL; do
    if [[ -z "${!var}" ]]; then
        printf 'error: %s is empty; check %s\n' "${var}" "${CONF_FILE}" >&2
        exit 1
    fi
done
if [[ ! "${VLLM_MODEL_REVISION}" =~ ^[0-9a-f]{40}$ ]]; then
    printf 'error: VLLM_MODEL_REVISION must be a 40-character commit SHA\n' >&2
    exit 1
fi

VLLM_EXE="$(vllm_bin)"
if [[ -z "${VLLM_EXE}" ]]; then
    printf 'error: vllm not found. Expected one of:\n' >&2
    printf '  the VLLM_BIN override, %s/venv/bin/vllm, or vllm on PATH\n' "${SCRIPT_DIR}" >&2
    exit 1
fi

# Pin guard. Start never installs: the venv moves only through the bootstrap
# target, so a venv that drifted from the Makefile pin would otherwise serve a
# retired release and every documented rate for the profile would be off.
# VLLM_VERSION is the pin make passes; a manual start without it skips the
# check. The interpreter beside the entry point answers without importing
# torch; `vllm --version` is the slow fallback for a PATH install.
if [[ -n "${VLLM_VERSION:-}" ]]; then
    VLLM_PY="$(dirname "${VLLM_EXE}")/python"
    if [[ -x "${VLLM_PY}" ]]; then
        VLLM_INSTALLED="$("${VLLM_PY}" -c \
            'from importlib.metadata import version; print(version("vllm"))')"
    else
        VLLM_INSTALLED="$("${VLLM_EXE}" --version | tail -1)"
    fi
    if [[ "${VLLM_INSTALLED}" != "${VLLM_VERSION}" ]]; then
        printf 'error: %s is vllm %s, the pin is %s; run the bootstrap (remote) or\n' \
            "${VLLM_EXE}" "${VLLM_INSTALLED}" "${VLLM_VERSION}" >&2
        printf '  reinstall the venv to the pin before starting\n' >&2
        exit 1
    fi
fi

# When running from a venv, its bin must be on PATH and not merely used to
# locate the entry point: vLLM JIT-compiles kernels in a subprocess and shells
# out to `ninja`, which pip installs into the venv's bin. Without this the
# engine dies with "FileNotFoundError: 'ninja'".
case "${VLLM_EXE}" in
    */venv/bin/vllm)
        VLLM_EXE_DIR="$(dirname "${VLLM_EXE}")"
        export PATH="${VLLM_EXE_DIR}:${PATH}"
        ;;
    *) : ;;
esac

args=(
    serve "${VLLM_MODEL}"
    --revision "${VLLM_MODEL_REVISION}"
    --served-model-name "${VLLM_SERVED_NAME}"
    --max-model-len "${VLLM_MAX_LEN}"
    --max-num-seqs "${VLLM_MAX_SEQS}"
    --max-num-batched-tokens "${VLLM_MAX_BATCHED}"
    --gpu-memory-utilization "${VLLM_GPU_UTIL}"
    --host "${VLLM_HOST}"
    --port "${VLLM_PORT}"
)

# Extended-context profiles carry model-specific nested config rather than
# teaching the launcher how to reconstruct each architecture's RoPE fields.
# Keep the JSON as one argv element; vLLM validates its shape.
if [[ -n "${VLLM_HF_OVERRIDES}" ]]; then
    args+=(--hf-overrides "${VLLM_HF_OVERRIDES}")
fi
if [[ -n "${VLLM_ALLOW_LONG_MAX_MODEL_LEN}" ]]; then
    export VLLM_ALLOW_LONG_MAX_MODEL_LEN
fi
[[ -n "${VLLM_ATTN_BACKEND:-}" ]] && args+=(--attention-backend "${VLLM_ATTN_BACKEND}")
[[ -n "${VLLM_KV_DTYPE}" ]] && args+=(--kv-cache-dtype "${VLLM_KV_DTYPE}")
if [[ "${VLLM_PREFIX_CACHING}" == "1" ]]; then
    # Cached-token counts in usage (prompt_tokens_details) are off by
    # default; the conversation benchmark measures cache reuse from them.
    args+=(--enable-prefix-caching --enable-prompt-tokens-details)
elif [[ "${VLLM_PREFIX_CACHING}" == "0" ]]; then
    args+=(--no-enable-prefix-caching)
fi
# Speculative decoding is a model fact: a drafter is trained for one exact
# target checkpoint, so the JSON (draft model, its pinned revision,
# num_speculative_tokens) lives in the model conf and travels with it. Keep
# it one argv element; vLLM validates the shape. num_speculative_tokens is
# mandatory when a draft model is named -- nothing derives it from the
# drafter's block size.
if [[ -n "${VLLM_SPECULATIVE_CONFIG}" ]]; then
    args+=(--speculative-config "${VLLM_SPECULATIVE_CONFIG}")
fi
if [[ -n "${VLLM_REASONING_PARSER}" ]]; then
    # The engine subprocess imports reasoning plugins independently. Loading
    # the same file as a tool plugin in the API process is not sufficient.
    if [[ -n "${VLLM_REASONING_PLUGIN}" ]]; then
        if [[ ! -f "${SCRIPT_DIR}/${VLLM_REASONING_PLUGIN}" ]]; then
            printf 'error: no such reasoning parser plugin: %s\n' \
                "${SCRIPT_DIR}/${VLLM_REASONING_PLUGIN}" >&2
            exit 1
        fi
        args+=(--reasoning-parser-plugin "${SCRIPT_DIR}/${VLLM_REASONING_PLUGIN}")
    fi
    args+=(--reasoning-parser "${VLLM_REASONING_PARSER}")
fi
if [[ -n "${VLLM_TOOL_PARSER}" ]]; then
    # A model whose tool dialect no bundled parser matches names a plugin file
    # here, resolved beside these scripts so it travels with them to a remote
    # host. This is a model fact, like VLLM_ATTN_AUTO: it says what the model
    # emits, not how the host should behave.
    if [[ -n "${VLLM_TOOL_PLUGIN}" ]]; then
        if [[ ! -f "${SCRIPT_DIR}/${VLLM_TOOL_PLUGIN}" ]]; then
            printf 'error: no such tool parser plugin: %s\n' \
                "${SCRIPT_DIR}/${VLLM_TOOL_PLUGIN}" >&2
            exit 1
        fi
        args+=(--tool-parser-plugin "${SCRIPT_DIR}/${VLLM_TOOL_PLUGIN}")
    fi
    args+=(--enable-auto-tool-choice --tool-call-parser "${VLLM_TOOL_PARSER}")
fi

# Reduces allocator fragmentation; set per host profile above, since it is
# actively harmful when running near the memory ceiling.

mkdir -p "$(dirname "${VLLM_PIDFILE}")"

# Refuse to overwrite a live server's pidfile. The pidfile is the only handle
# stop.sh has, so clobbering it strands the running server: it keeps the GPU,
# but stop.sh reads the new pid, finds it dead, and reports "not running".
# Recovery then means hunting the process by hand, which is exactly the
# pkill -f trap AGENTS.md forbids.
#
# Reachable two ways: starting twice by mistake, and running start.sh with
# VLLM_BIN pointed at a stub to inspect the resolved arguments -- the pidfile
# is written before the exec, so even a dry run takes the handle. Both were hit
# while adding the MLA support.
running_pid="$(vllm_pid)"
if [[ -n "${running_pid}" ]]; then
    printf 'error: a server is already running (pid %s, gpu %s MiB)\n' \
        "${running_pid}" "$(vllm_gpu_mib)" >&2
    printf 'stop it first, or set VLLM_PIDFILE to use a separate handle\n' >&2
    exit 1
fi

# exec replaces this shell without changing the pid, so the recorded pid is the
# server's. stop.sh targets that pid rather than a command-line pattern: pkill -f
# matches any shell whose command line mentions the pattern, including the one
# invoking it, and will kill the caller instead of the server.
printf '%s\n' "$$" > "${VLLM_PIDFILE}"

printf 'starting %s@%s as "%s" on %s:%s\n' \
    "${VLLM_MODEL}" "${VLLM_MODEL_REVISION}" "${VLLM_SERVED_NAME}" \
    "${VLLM_HOST}" "${VLLM_PORT}"
printf 'host: sm_%s, %s MiB VRAM -> backend %s, kv %s, util %s, seqs %s, batched %s\n' \
    "${VLLM_CAP}" "${VLLM_VRAM_MIB}" "${VLLM_ATTN_BACKEND:-vllm-selected}" "${VLLM_KV_DTYPE:-auto}" \
    "${VLLM_GPU_UTIL}" "${VLLM_MAX_SEQS}" "${VLLM_MAX_BATCHED}"
# A separate line: the host line's format is parsed by the bench harness.
if [[ -n "${VLLM_SPECULATIVE_CONFIG}" ]]; then
    printf 'speculative: %s\n' "${VLLM_SPECULATIVE_CONFIG}"
fi

exec "${VLLM_EXE}" "${args[@]}"
