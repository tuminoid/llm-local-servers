.PHONY: help status lint shellcheck markdownlint pycompile test clean all opencode-config
.PHONY: audit-bench-check
.PHONY: ollama-model-check ollama-install ollama-start ollama-pull
.PHONY: ollama-stop ollama-status ollama-logs ollama-bench ollama-capability
.PHONY: ollama-remote-deploy ollama-remote-check ollama-remote-stopped-check
.PHONY: ollama-remote-bootstrap ollama-remote-start ollama-remote-pull
.PHONY: ollama-remote-stop ollama-remote-status ollama-remote-logs
.PHONY: ollama-remote-bench ollama-remote-capability ollama-remote-tunnel
.PHONY: vllm-model-check vllm-start vllm-stop vllm-status vllm-logs vllm-bench vllm-capability
.PHONY: vllm-remote-deploy vllm-remote-check vllm-remote-bootstrap vllm-remote-start
.PHONY: vllm-remote-stop vllm-remote-status vllm-remote-logs vllm-remote-bench vllm-remote-capability
.PHONY: vllm-remote-tunnel
.PHONY: vllm-metal-model-check vllm-metal-install vllm-metal-pull
.PHONY: vllm-metal-start vllm-metal-stop vllm-metal-status vllm-metal-logs
.PHONY: vllm-metal-bench vllm-metal-capability
.PHONY: splash-model-check splash-install splash-pull splash-start splash-stop
.PHONY: splash-status splash-logs splash-bench splash-capability
.PHONY: lmstudio-model-check lmstudio-install lmstudio-pull lmstudio-start
.PHONY: lmstudio-stop lmstudio-status lmstudio-logs lmstudio-bench lmstudio-capability

# Every target here is phony, so GNU Make's built-in rules can only do harm.
# Left on, a mistyped target matches the built-in `%: %.sh` rule and silently
# writes an executable copy of a script instead of failing; `make stop` in
# vllm/ once produced a stale copy of stop.sh that stopped nothing. .DEFAULT
# then makes a mistyped target an error plus the target list.
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

.DEFAULT:
	@echo "error: unknown target '$@'" >&2; \
	echo >&2; \
	$(MAKE) --no-print-directory help >&2; \
	exit 1

# The AuditBench v1 and Capability Check v1 harnesses live in the sibling
# llm-audit-bench repository. Local bench, capability, and test targets import
# them via PYTHONPATH; deploy targets rsync the two modules next to the
# adapters on remote hosts, where they import as adjacent files.
AUDIT_BENCH_DIR ?= $(abspath ../llm-audit-bench)
AUDIT_BENCH_SRC := $(AUDIT_BENCH_DIR)/src

VLLM_DIR := vllm
# No default model. Ollama and vLLM start, pull, and benchmark targets require
# MODEL to name a config in that server's models directory. A silent default
# launched the wrong vLLM model remotely in a way run.sh could not see, costing
# a full readiness timeout before it gave up.
MODEL           ?=
# vLLM 0.29.0 (Model Runner V2). Transformers 5.15.1: 0.29.0 needs >= 5.10.4
# and 5.15 carries the Gemma 4 per-layer head-dim handling (vllm#49797).
# ninja is a runtime dependency: the DFlash draft head is torch.compiled at
# engine init and inductor shells out to it. Canonical rows in
# vllm/BENCHMARKS.md are 0.28.0 measurements until re-run at this pin.
VLLM_VERSION    ?= 0.29.0
VLLM_TRANSFORMERS_VERSION ?= 5.15.1
VLLM_REMOTE_DIR ?= tmp/vllm
VLLM_REMOTE_PORT ?= 8000
VLLM_TUNNEL_PORT ?= 8001
# Remote GPU host. Deliberately no committed default: the ssh alias is a
# personal setting, supplied by the environment (copy .envrc.example to .envrc
# and `direnv allow`, or pass HOST=<ssh-host> per invocation). Remote targets
# fail fast when it is unset.
HOST ?=

# AuditBench v1 canonical settings. Override streams with 1,2,3,4,5,6,7,8
# while locating a host's decode knee; publish the canonical 1/2/4/8 run.
AUDIT_BENCH_STREAMS ?= 1,2,4,8
AUDIT_BENCH_DEEP_STREAMS ?= 1,2,4
AUDIT_BENCH_PROFILE ?= full
AUDIT_BENCH_SAMPLES ?= 3
AUDIT_BENCH_OUTPUT_TOKENS ?= 1024
AUDIT_BENCH_DEEP_OUTPUT_TOKENS ?= 256
AUDIT_BENCH_TARGET_TOLERANCE ?= 0.02
AUDIT_BENCH_TIMEOUT ?= 7200
AUDIT_BENCH_DRY_RUN ?= 0
AUDIT_BENCH_ACTIVE_SLOTS ?=
AUDIT_BENCH_KV_TOKENS ?=
# Empty means the harness default state directory on the executing host.
AUDIT_BENCH_OUTPUT_DIR ?=
AUDIT_BENCH_REPO_COMMIT ?= $(shell git rev-parse --verify HEAD 2>/dev/null)
AUDIT_BENCH_REPO_DIRTY ?= $(shell if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then if test -z "$$(git status --porcelain)"; then echo 0; else echo 1; fi; else echo unknown; fi)
AUDIT_BENCH_VARS := AUDIT_BENCH_STREAMS AUDIT_BENCH_DEEP_STREAMS \
	AUDIT_BENCH_PROFILE \
	AUDIT_BENCH_SAMPLES AUDIT_BENCH_OUTPUT_TOKENS \
	AUDIT_BENCH_DEEP_OUTPUT_TOKENS AUDIT_BENCH_TARGET_TOLERANCE \
	AUDIT_BENCH_TIMEOUT AUDIT_BENCH_DRY_RUN AUDIT_BENCH_ACTIVE_SLOTS \
	AUDIT_BENCH_KV_TOKENS AUDIT_BENCH_OUTPUT_DIR \
	AUDIT_BENCH_REPO_COMMIT AUDIT_BENCH_REPO_DIRTY
AUDIT_BENCH_ENV = $(strip $(foreach v,$(AUDIT_BENCH_VARS),$(v)=$($(v))))

CAPABILITY_TIMEOUT ?= 600
CAPABILITY_REASONING_TOKENS ?= 2048
# Empty means the harness default state directory on the executing host.
CAPABILITY_OUTPUT_DIR ?=
CAPABILITY_ENV = CAPABILITY_TIMEOUT=$(CAPABILITY_TIMEOUT) \
	CAPABILITY_REASONING_TOKENS=$(CAPABILITY_REASONING_TOKENS) \
	CAPABILITY_OUTPUT_DIR=$(CAPABILITY_OUTPUT_DIR)

VLLM_METAL_DIR := vllm-metal
# vLLM-Metal runs on Apple Silicon only. Plugin 0.29.0 paired with the
# prebuilt vLLM 0.29.0 macOS arm64 wheel; the plugin wheel pins mlx==0.32.1
# (ABI-locked) and an mlx-lm git SHA. Digests match the GitHub release
# assets and are verified by install.sh. 0.29.0 loads the HF processor at
# startup, so confs pin processor-compatible revisions. Canonical rows in
# vllm-metal/BENCHMARKS.md are 0.28.0 measurements until re-run at this pin.
VLLM_METAL_VERSION ?= 0.29.0
VLLM_METAL_WHEEL_SHA256 ?= 0d03dcc2be9a4286a19c5e53e1355d2e47acdbf2be6f9de9cbb48cc4b880f393
VLLM_METAL_VLLM_VERSION ?= 0.29.0
VLLM_METAL_VLLM_WHEEL_SHA256 ?= 7133cb494664c502b07b114fe915847f0e71296d502f67f6fa76172ba46978df

SPLASH_DIR := splash
SPLASH_VERSION ?= 1.0
SPLASH_ARCHIVE_SHA256 ?= dc752f0aab8419c46fe2803a0e7059c1515e5df48def11b9d517bbbf1fb2dddc
export SPLASH_VERSION SPLASH_ARCHIVE_SHA256
SPLASH_MODEL_CONF ?= $(SPLASH_DIR)/models/$(MODEL).conf

LMSTUDIO_DIR := lmstudio
# The operator installs and updates the desktop app and its engines, so the pins
# name the release measured here: bench and capability refuse any other, while
# install and start report the drift and serve it.
LMSTUDIO_VERSION ?= 0.4.25+1
LMSTUDIO_SPLASH_ENGINE_VERSION ?= 0.0.5
LMSTUDIO_MLX_ENGINE_VERSION ?= 1.11.0
export LMSTUDIO_VERSION LMSTUDIO_SPLASH_ENGINE_VERSION LMSTUDIO_MLX_ENGINE_VERSION

OLLAMA_DIR := ollama
# Two managed Ollama runtimes, both reviewed releases with per-platform
# archive digests from the release's sha256sum.txt (OLLAMA_ARCHIVE_SHA256 is
# ollama-linux-amd64.tar.zst for the A100, _LINUX_ARM64 the arm64 build,
# _DARWIN the universal ollama-darwin.tgz); ollama-install refuses an
# unverified archive.
# Default 0.32.14: the only release whose MLX runner survives the
# post-prefill commit memory runaway on safetensors profiles (0.33.2,
# 0.33.3 and 0.34.2 each fail harder; 0.34.2 hard-reset the M5 inside the
# first conversation). Retest only on a release whose notes name the MLX
# runner's post-prefill commit or trie memory bound.
OLLAMA_VERSION ?= 0.32.14
OLLAMA_ARCHIVE_SHA256 ?= c620917a71e146ab3a7f893084f066069c4c65d144ef8379a91c3cbe8b27de8f
OLLAMA_ARCHIVE_SHA256_LINUX_ARM64 ?= 7802b739fbdc74df556600f1619f86457b69dce913301cf2d91f7f9d7f7a41b8
OLLAMA_ARCHIVE_SHA256_DARWIN ?= c7e8b91485943785bc6d295d96551e971ec94c6829d0d6b3500366942dc50cd1
# GGUF runtime 0.34.2 (llama.cpp b10969), selected per profile through
# OLLAMA_RUNTIME_VERSION in the conf; GGUF never dispatches to the MLX
# runner. Profiles on it: qwen3.8-27b, qwen3.8-27b-native, both flash-next
# GGUF confs. Not qwen3.6-35b-a3b or qwen3-coder-30b (protocol regressions
# at 0.34.2: coder emits duplicate streaming tool calls, qwen3.6 drops out
# of the conversation profile). Install with
#   make ollama-install OLLAMA_VERSION=0.34.2 \
#     OLLAMA_ARCHIVE_SHA256_DARWIN=f33b2a5aa59bc6c961ed3ec23ba9dc646ca6d99ced8d2a0d46eb3a522167dd3f \
#     OLLAMA_ARCHIVE_SHA256=e155b83589986d2c581fdbf1381ea3ebdb16549883679cd5a0627f7cdc05b12b \
#     OLLAMA_ARCHIVE_SHA256_LINUX_ARM64=8edcfe99eb7546d9422cfa8297d341dcd50e090e192ce1a8092a6ab6d182867b
# Expected active runner slots; must match the OLLAMA_NUM_PARALLEL used at start.
OLLAMA_BENCH_JOBS ?= 1
OLLAMA_BENCH_LOAD_ONLY ?= 0
# Remote Ollama is deliberately separate from both a host's normal Ollama
# installation and this machine's local server. Its guards are causal, not
# ceremonial: start requires an idle GPU and an unclaimed port (preflight),
# pull/bench/capability require the pidfile-owned managed server (preflight),
# bootstrap refuses while that server is running, and stop signals only the
# pidfile-owned process group.
OLLAMA_REMOTE_DIR ?= tmp/ollama
OLLAMA_REMOTE_PORT ?= 11435
OLLAMA_TUNNEL_PORT ?= 11436
OLLAMA_REMOTE_ALLOW_KEY_CREATE ?= 0

help:
	@echo "llm-local-servers - Managed local inference serving fleet"
	@echo ""
	@echo "  make status      - Show every local server's status (not the remote ones)"
	@echo "  make lint        - Run all linters (shellcheck + markdownlint + pycompile)"
	@echo "  make test        - Run the unit tests (needs the llm-audit-bench checkout)"
	@echo "  make opencode-config - Regenerate opencode/*/opencode.json from the model configs"
	@echo "  make all         - Run lint and test"
	@echo "  make clean       - Remove Python bytecode and editor droppings"
	@echo ""
	@echo "  AuditBench v1 and Capability Check v1 run from the sibling"
	@echo "  llm-audit-bench checkout: AUDIT_BENCH_DIR=$(AUDIT_BENCH_DIR)"
	@echo ""
	@echo "  Local Ollama:"
	@echo "  make ollama-install - Install pinned Ollama to the user runtime"
	@echo "  make ollama-start   - Start Ollama detached (needs MODEL=<name>)"
	@echo "  make ollama-pull    - Pull the selected model into the running server"
	@echo "  make ollama-status  - Show process, CPU/GPU split, context, and memory"
	@echo "  make ollama-logs    - Follow the Ollama server log"
	@echo "  make ollama-bench   - Run AuditBench v1"
	@echo "  make ollama-capability - Check reasoning, tools, and structured output"
	@echo "  make ollama-stop    - Stop Ollama and verify GPU release"
	@echo ""
	@echo "  Local vLLM (CUDA):"
	@echo "  make vllm-start  - Start vLLM detached (needs MODEL=<name>)"
	@echo "  make vllm-stop   - Stop vLLM and verify the GPU was released"
	@echo "  make vllm-status - Show process, GPU use, backend, KV cache sizing"
	@echo "  make vllm-logs   - Follow the vLLM server log"
	@echo "  make vllm-bench  - Run AuditBench v1"
	@echo "  make vllm-capability - Check reasoning, tools, and structured output"
	@echo ""
	@echo "  vLLM-Metal on Apple Silicon (port 8021, needs MODEL=<name>):"
	@echo "  make vllm-metal-install - Install the pinned plugin venv"
	@echo "  make vllm-metal-pull    - Download the model's pinned revision"
	@echo "  make vllm-metal-start   - Start vLLM-Metal detached"
	@echo "  make vllm-metal-status  - Show process, KV sizing, NAX, memory"
	@echo "  make vllm-metal-logs    - Follow the vLLM-Metal server log"
	@echo "  make vllm-metal-bench   - Run AuditBench v1"
	@echo "  make vllm-metal-capability - Check reasoning, tools, and structured output"
	@echo "  make vllm-metal-stop    - Stop and verify process-group release"
	@echo ""
	@echo "  Splash on Apple Silicon M3+ (port 8022, needs MODEL=<name>):"
	@echo "  make splash-install    - Install the checksum-pinned standalone runtime"
	@echo "  make splash-pull       - Verify and link the model's pinned HF snapshot"
	@echo "  make splash-start      - Start detached with DFlash 2 and caching"
	@echo "  make splash-status     - Show identity, context, sparse KV and memory plan"
	@echo "  make splash-logs       - Follow the server log"
	@echo "  make splash-bench      - Run AuditBench v1"
	@echo "  make splash-capability - Check reasoning, tools, and structured output"
	@echo "  make splash-stop       - Stop and verify process-group and port release"
	@echo "  Models: $(patsubst $(SPLASH_DIR)/models/%.conf,%,$(wildcard $(SPLASH_DIR)/models/*.conf))"
	@echo ""
	@echo "  LM Studio (port 1234, needs MODEL=<name>):"
	@echo "  make lmstudio-install    - Check the app, engines and hf CLI; report pin drift"
	@echo "  make lmstudio-pull       - Download the model's pinned revision into LM Studio"
	@echo "  make lmstudio-start      - Start the server and load the model"
	@echo "  make lmstudio-status     - Show the managed record and loaded models"
	@echo "  make lmstudio-logs       - Follow the launch log"
	@echo "  make lmstudio-bench      - Run AuditBench v1"
	@echo "  make lmstudio-capability - Check reasoning, tools, and structured output"
	@echo "  make lmstudio-stop       - Unload, stop the server and verify release"
	@echo "  Models: $(patsubst $(LMSTUDIO_DIR)/models/%.conf,%,$(wildcard $(LMSTUDIO_DIR)/models/*.conf))"
	@echo ""
	@echo "  Remote vLLM host (HOST=<ssh-host> required, needs MODEL=<name>):"
	@echo "  make vllm-remote-bootstrap - Create the remote venv and install vllm"
	@echo "  make vllm-remote-start     - Start on the remote host (syncs scripts first)"
	@echo "  make vllm-remote-stop      - Stop on the remote host"
	@echo "  make vllm-remote-status    - Status of the remote server"
	@echo "  make vllm-remote-logs      - Follow the remote server log"
	@echo "  make vllm-remote-bench     - Run AuditBench v1 on the remote host"
	@echo "  make vllm-remote-capability - Check model API capabilities"
	@echo "  make vllm-remote-tunnel    - Forward localhost:$(VLLM_TUNNEL_PORT) to the host"
	@echo ""
	@echo "  Isolated remote Ollama (HOST=<ssh-host> required, needs MODEL=<name>):"
	@echo "  make ollama-remote-bootstrap - Install pinned Ollama under $(OLLAMA_REMOTE_DIR) (server stopped)"
	@echo "  make ollama-remote-start     - Start only when the remote GPU is idle (syncs scripts first)"
	@echo "  make ollama-remote-pull      - Pull through the owned remote server"
	@echo "  make ollama-remote-stop      - Stop only the isolated pidfile-owned server"
	@echo "  make ollama-remote-status    - Read isolated remote status"
	@echo "  make ollama-remote-logs      - Follow the isolated remote log"
	@echo "  make ollama-remote-bench     - Run AuditBench v1 against the owned remote server"
	@echo "  make ollama-remote-capability - Check model API capabilities"
	@echo "  make ollama-remote-tunnel    - Forward localhost:$(OLLAMA_TUNNEL_PORT) to remote $(OLLAMA_REMOTE_PORT)"
	@echo ""
	@echo "  Select the vLLM model with MODEL=<name> ($(VLLM_DIR)/models/<name>.conf):"
	@echo "  $(patsubst $(VLLM_DIR)/models/%.conf,%,$(wildcard $(VLLM_DIR)/models/*.conf))"
	@echo ""
	@echo "  Select the Ollama model with MODEL=<name> ($(OLLAMA_DIR)/models/<name>.conf):"
	@echo "  $(patsubst $(OLLAMA_DIR)/models/%.conf,%,$(wildcard $(OLLAMA_DIR)/models/*.conf))"
	@echo ""
	@echo "  Select the vLLM-Metal model with MODEL=<name> ($(VLLM_METAL_DIR)/models/<name>.conf):"
	@echo "  $(patsubst $(VLLM_METAL_DIR)/models/%.conf,%,$(wildcard $(VLLM_METAL_DIR)/models/*.conf))"
	@echo ""

# Every local runtime's server and model lines, one after another; a failing
# one does not hide the rest, but fails the target.
status:
	@rc=0; for r in vllm vllm-metal splash lmstudio ollama; do \
		echo "== $$r"; out="$$($(MAKE) --no-print-directory $$r-status)" || rc=1; \
		printf '%s\n' "$$out" | grep -E '^(server|model): '; \
	done; exit $$rc

# --- llm-audit-bench checkout guard ---

audit-bench-check:
	@test -f "$(AUDIT_BENCH_SRC)/audit_bench.py" \
		-a -f "$(AUDIT_BENCH_SRC)/capability_check.py" || { \
		echo "error: llm-audit-bench checkout not found at $(AUDIT_BENCH_DIR)" >&2; \
		echo "clone https://github.com/tuminoid/llm-audit-bench beside this repo," >&2; \
		echo "or point AUDIT_BENCH_DIR=<path> at an existing checkout" >&2; \
		exit 1; }

# --- Linting ---

SHELLCHECK_STRICT := -s bash -S style -o all -e SC2310,SC2311,SC2312
SHELL_SOURCES = $(shell find . -name '*.sh' -type f -not -path './.git/*' | sort)

lint: shellcheck markdownlint pycompile

shellcheck:
	shellcheck $(SHELLCHECK_STRICT) $(SHELL_SOURCES)

markdownlint:
	markdownlint-cli2

pycompile:
	@python3 -m compileall -q $(OLLAMA_DIR) $(VLLM_DIR) $(VLLM_METAL_DIR) $(SPLASH_DIR) \
		$(LMSTUDIO_DIR) opencode tests

# --- Test ---

test: audit-bench-check
	@PYTHONPATH="$(AUDIT_BENCH_SRC)" python3 -m unittest discover -s tests -p 'test_*.py'

# --- opencode ---

# opencode/*/opencode.json are committed and generated; make test fails when stale.
opencode-config: audit-bench-check
	@PYTHONPATH="$(AUDIT_BENCH_SRC)" python3 ./opencode/generate.py

# --- Clean ---

clean:
	@find . -type d -name '__pycache__' -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type f \( -name '*~' -o -name '*.tmp' \) -not -path './.git/*' -delete 2>/dev/null || true

# --- Local Ollama ---

# Ollama is installed under the user's data directory rather than replacing
# /usr/local/bin/ollama. The latter is root-owned on some hosts, and using a
# versioned runtime also keeps this path independent of systemd.
ollama-model-check:
	@test -n "$(MODEL)" || { \
		echo "error: set MODEL=<name>" >&2; \
		echo "available:" >&2; \
		echo "  $(patsubst $(OLLAMA_DIR)/models/%.conf,%,$(wildcard $(OLLAMA_DIR)/models/*.conf))" >&2; \
		exit 1; }
	@test -f "$(OLLAMA_DIR)/models/$(MODEL).conf" || { \
		echo "error: no such Ollama model config: $(MODEL)" >&2; \
		echo "MODEL names models/<name>.conf, not the Ollama registry tag" >&2; \
		echo "available:" >&2; \
		echo "  $(patsubst $(OLLAMA_DIR)/models/%.conf,%,$(wildcard $(OLLAMA_DIR)/models/*.conf))" >&2; \
		exit 1; }

ollama-install:
	@OLLAMA_VERSION=$(OLLAMA_VERSION) \
		OLLAMA_ARCHIVE_SHA256=$(OLLAMA_ARCHIVE_SHA256) \
		OLLAMA_ARCHIVE_SHA256_LINUX_ARM64=$(OLLAMA_ARCHIVE_SHA256_LINUX_ARM64) \
		OLLAMA_ARCHIVE_SHA256_DARWIN=$(OLLAMA_ARCHIVE_SHA256_DARWIN) \
		./$(OLLAMA_DIR)/install.sh

ollama-start: ollama-model-check
	@OLLAMA_VERSION=$(OLLAMA_VERSION) ./$(OLLAMA_DIR)/run.sh $(MODEL)

ollama-pull: ollama-model-check
	@OLLAMA_VERSION=$(OLLAMA_VERSION) ./$(OLLAMA_DIR)/pull.sh $(MODEL)

ollama-stop:
	@OLLAMA_VERSION=$(OLLAMA_VERSION) ./$(OLLAMA_DIR)/stop.sh

ollama-status:
	@OLLAMA_VERSION=$(OLLAMA_VERSION) ./$(OLLAMA_DIR)/status.sh

ollama-logs:
	@tail -f "$${XDG_STATE_HOME:-$${HOME}/.local/state}/ollama/server.log"

ollama-bench: ollama-model-check audit-bench-check
	@OLLAMA_VERSION=$(OLLAMA_VERSION) \
		OLLAMA_BENCH_JOBS=$(OLLAMA_BENCH_JOBS) \
		OLLAMA_BENCH_LOAD_ONLY=$(OLLAMA_BENCH_LOAD_ONLY) \
		$(AUDIT_BENCH_ENV) \
		PYTHONPATH="$(AUDIT_BENCH_SRC)" \
		./$(OLLAMA_DIR)/bench.py $(MODEL)

ollama-capability: ollama-model-check audit-bench-check
	@$(CAPABILITY_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" \
		python3 ./$(OLLAMA_DIR)/capability.py $(MODEL)

# --- Isolated remote Ollama ---
#
# The remote tree owns its binary, model cache, state, and API port. Explicitly
# naming OLLAMA_BIN prevents lib.sh from falling back to a host Ollama install
# when bootstrap has not been run. The fixed values are excluded from
# OLLAMA_ENV so caller environment cannot redirect a remote operation into the
# system installation or another server.
override OLLAMA_REMOTE_RUNTIME_ROOT = $(OLLAMA_REMOTE_DIR)/runtime
override OLLAMA_REMOTE_MODEL_CACHE = $(OLLAMA_REMOTE_DIR)/model-cache
override OLLAMA_REMOTE_STATE_DIR = $(OLLAMA_REMOTE_DIR)/state
override OLLAMA_REMOTE_BIN = $(OLLAMA_REMOTE_RUNTIME_ROOT)/v$(OLLAMA_VERSION)/bin/ollama
override OLLAMA_REMOTE_FIXED_ENV = \
	OLLAMA_VERSION=$(OLLAMA_VERSION) \
	OLLAMA_RUNTIME_ROOT=$(OLLAMA_REMOTE_RUNTIME_ROOT) \
	OLLAMA_BIN=$(OLLAMA_REMOTE_BIN) \
	OLLAMA_MODELS=$(OLLAMA_REMOTE_MODEL_CACHE) \
	OLLAMA_STATE_DIR=$(OLLAMA_REMOTE_STATE_DIR) \
	OLLAMA_LOG=$(OLLAMA_REMOTE_STATE_DIR)/server.log \
	OLLAMA_HOST=127.0.0.1:$(OLLAMA_REMOTE_PORT) \
	OLLAMA_NO_CLOUD=1 \
	OLLAMA_REQUIRE_EXISTING_KEY=$(if $(filter 1,$(OLLAMA_REMOTE_ALLOW_KEY_CREATE)),0,1)

override OLLAMA_REMOTE_RESERVED := OLLAMA_REMOTE_% \
	OLLAMA_DIR OLLAMA_VERSION OLLAMA_ARCHIVE_SHA256 OLLAMA_ARCHIVE_SHA256_% \
	OLLAMA_REMOTE_RUNTIME_ROOT \
	OLLAMA_REMOTE_MODEL_CACHE OLLAMA_REMOTE_STATE_DIR OLLAMA_REMOTE_BIN \
	OLLAMA_REMOTE_FIXED_ENV OLLAMA_REMOTE_RESERVED OLLAMA_ENV \
	OLLAMA_RUNTIME_ROOT OLLAMA_BIN OLLAMA_MODELS OLLAMA_STATE_DIR \
	OLLAMA_PIDFILE OLLAMA_LOG OLLAMA_BASELINE_GPU_FILE OLLAMA_HOST \
	OLLAMA_NO_CLOUD OLLAMA_REQUIRE_EXISTING_KEY OLLAMA_BENCH_BASE
override OLLAMA_ENV = $(strip $(foreach v, \
	$(filter-out $(OLLAMA_REMOTE_RESERVED),$(filter OLLAMA_%,$(.VARIABLES))), \
	$(if $(filter environment% command line,$(origin $(v))),$(v)=$($(v)))))

ollama-remote-check:
	@test -n "$(HOST)" || { \
		echo "error: set HOST=<ssh-host> (see .envrc.example)" >&2; \
		exit 1; }
	@test "$(OLLAMA_REMOTE_DIR)" = "tmp/ollama" || { \
		echo "error: OLLAMA_REMOTE_DIR is fixed at tmp/ollama" >&2; \
		exit 1; }
	@test "$(OLLAMA_REMOTE_DIR)" != "$(VLLM_REMOTE_DIR)" || { \
		echo "error: Ollama and vLLM remote directories must differ" >&2; \
		exit 1; }
	@case "$(OLLAMA_REMOTE_PORT)" in \
		"" | *[!0-9]*) echo "error: invalid OLLAMA_REMOTE_PORT" >&2; exit 1 ;; \
	esac
	@case "$(OLLAMA_TUNNEL_PORT)" in \
		"" | *[!0-9]*) echo "error: invalid OLLAMA_TUNNEL_PORT" >&2; exit 1 ;; \
	esac
	@case "$(OLLAMA_REMOTE_ALLOW_KEY_CREATE)" in \
		0 | 1) ;; \
		*) echo "error: OLLAMA_REMOTE_ALLOW_KEY_CREATE must be 0 or 1" >&2; exit 1 ;; \
	esac
	@test "$(OLLAMA_REMOTE_PORT)" -ge 1 \
		-a "$(OLLAMA_REMOTE_PORT)" -le 65535 || { \
		echo "error: OLLAMA_REMOTE_PORT is outside 1-65535" >&2; \
		exit 1; }
	@test "$(OLLAMA_TUNNEL_PORT)" -ge 1 \
		-a "$(OLLAMA_TUNNEL_PORT)" -le 65535 || { \
		echo "error: OLLAMA_TUNNEL_PORT is outside 1-65535" >&2; \
		exit 1; }
	@test "$(OLLAMA_REMOTE_PORT)" != "11434" || { \
		echo "error: remote port 11434 is reserved for the host's normal Ollama" >&2; \
		exit 1; }
	@test "$(OLLAMA_REMOTE_PORT)" != "$(VLLM_REMOTE_PORT)" || { \
		echo "error: remote port $(VLLM_REMOTE_PORT) is reserved for vLLM" >&2; \
		exit 1; }
	@test "$(OLLAMA_TUNNEL_PORT)" != "11434" || { \
		echo "error: local port 11434 is reserved for local Ollama" >&2; \
		exit 1; }
	@test "$(OLLAMA_TUNNEL_PORT)" != "$(VLLM_TUNNEL_PORT)" || { \
		echo "error: local port $(VLLM_TUNNEL_PORT) is reserved for the vLLM tunnel" >&2; \
		exit 1; }
	@test "$(OLLAMA_TUNNEL_PORT)" != "$(VLLM_REMOTE_PORT)" || { \
		echo "error: local port $(VLLM_REMOTE_PORT) is reserved for local vLLM" >&2; \
		exit 1; }
	@test "$(OLLAMA_TUNNEL_PORT)" != "$(OLLAMA_REMOTE_PORT)" || { \
		echo "error: use distinct local and remote Ollama ports" >&2; \
		exit 1; }

# Bootstrap replaces the managed runtime, and doing that under a live server
# is the one remote mutation the deployed preflight cannot gate (it may not
# be deployed yet), so this reads the isolated pidfile directly over ssh. A
# fresh host has no pidfile and passes; a stale pidfile (dead pid) passes.
ollama-remote-stopped-check: ollama-remote-check
	@ssh $(HOST) 'pid=$$(cat $(OLLAMA_REMOTE_STATE_DIR)/server.pid 2>/dev/null || true); \
		if [ -n "$$pid" ] && kill -0 "$$pid" 2>/dev/null; then \
			echo "error: managed remote Ollama is running (pid $$pid); stop it first:" >&2; \
			echo "  make ollama-remote-stop HOST=$(HOST)" >&2; \
			exit 1; \
		fi'

# runtime/, model-cache/, and state/ are remote-owned. rsync excludes preserve
# them while --delete removes stale deployed scripts and model profiles. The
# harness modules are synced from the llm-audit-bench checkout so the deployed
# tree is self-contained: bench.py and capability.py import them as adjacent
# files, no PYTHONPATH on the remote host.
#
# Deploying is legal while the server runs: the excludes keep it away from
# everything the live process owns, scripts are read per invocation, and
# pull/bench/capability need current scripts against the running server.
ollama-remote-deploy: ollama-remote-check audit-bench-check
	@rsync -a --delete \
		--exclude runtime --exclude model-cache --exclude state \
		--exclude __pycache__ \
		./$(OLLAMA_DIR)/ $(HOST):$(OLLAMA_REMOTE_DIR)/
	@rsync -a "$(AUDIT_BENCH_SRC)/audit_bench.py" \
		$(HOST):$(OLLAMA_REMOTE_DIR)/audit_bench.py
	@rsync -a "$(AUDIT_BENCH_SRC)/capability_check.py" \
		$(HOST):$(OLLAMA_REMOTE_DIR)/capability_check.py
	@ssh $(HOST) 'chmod +x $(OLLAMA_REMOTE_DIR)/*.sh $(OLLAMA_REMOTE_DIR)/*.py'
	@echo "deployed scripts to $(HOST):$(OLLAMA_REMOTE_DIR)"

ollama-remote-bootstrap: ollama-remote-stopped-check ollama-remote-deploy
	@ssh $(HOST) '$(OLLAMA_REMOTE_FIXED_ENV) \
		OLLAMA_ARCHIVE_SHA256=$(OLLAMA_ARCHIVE_SHA256) \
		$(OLLAMA_REMOTE_DIR)/install.sh'

# start/pull/bench/capability deploy because they execute current repo files.
# stop/status/logs/tunnel never deploy: inspection and teardown must not mutate
# the remote tree as a side effect.
ollama-remote-start: ollama-remote-check ollama-model-check ollama-remote-deploy
	@ssh $(HOST) '$(OLLAMA_REMOTE_FIXED_ENV) \
		$(OLLAMA_REMOTE_DIR)/preflight.sh idle && \
		$(OLLAMA_ENV) $(OLLAMA_REMOTE_FIXED_ENV) \
		$(OLLAMA_REMOTE_DIR)/run.sh $(MODEL)'

ollama-remote-pull: ollama-remote-check ollama-model-check ollama-remote-deploy
	@ssh $(HOST) '$(OLLAMA_REMOTE_FIXED_ENV) \
		$(OLLAMA_REMOTE_DIR)/preflight.sh managed && \
		$(OLLAMA_ENV) $(OLLAMA_REMOTE_FIXED_ENV) \
		$(OLLAMA_REMOTE_DIR)/pull.sh $(MODEL)'

ollama-remote-stop: ollama-remote-check
	@ssh $(HOST) '$(OLLAMA_REMOTE_FIXED_ENV) $(OLLAMA_REMOTE_DIR)/stop.sh'

ollama-remote-status: ollama-remote-check
	@ssh $(HOST) '$(OLLAMA_REMOTE_FIXED_ENV) $(OLLAMA_REMOTE_DIR)/status.sh'

ollama-remote-logs: ollama-remote-check
	@ssh $(HOST) 'tail -f $(OLLAMA_REMOTE_STATE_DIR)/server.log'

ollama-remote-bench: ollama-remote-check ollama-model-check ollama-remote-deploy
	@ssh $(HOST) '$(OLLAMA_REMOTE_FIXED_ENV) \
		$(OLLAMA_REMOTE_DIR)/preflight.sh managed && \
		$(OLLAMA_ENV) $(AUDIT_BENCH_ENV) $(OLLAMA_REMOTE_FIXED_ENV) \
		python3 $(OLLAMA_REMOTE_DIR)/bench.py $(MODEL)'

ollama-remote-capability: ollama-remote-check ollama-model-check ollama-remote-deploy
	@ssh $(HOST) '$(OLLAMA_ENV) $(CAPABILITY_ENV) $(OLLAMA_REMOTE_FIXED_ENV) \
		python3 $(OLLAMA_REMOTE_DIR)/capability.py $(MODEL)'

# The ports cannot collide with local Ollama (11434) or the vLLM tunnel (8001).
# ExitOnForwardFailure prevents a misleading live ssh process when bind fails.
ollama-remote-tunnel: ollama-remote-check
	@echo "forwarding localhost:$(OLLAMA_TUNNEL_PORT) -> $(HOST):$(OLLAMA_REMOTE_PORT) (Ctrl-C to stop)"
	@ssh -o ExitOnForwardFailure=yes -N \
		-L 127.0.0.1:$(OLLAMA_TUNNEL_PORT):127.0.0.1:$(OLLAMA_REMOTE_PORT) \
		$(HOST)

# --- Local vLLM (CUDA) ---

# Model selection is mandatory: there is no default model, so start, bench, and
# capability fail fast rather than acting on an arbitrary model.
vllm-model-check:
	@test -n "$(MODEL)" || { \
		echo "error: set MODEL=<name>" >&2; \
		echo "available:" >&2; \
		echo "  $(patsubst $(VLLM_DIR)/models/%.conf,%,$(wildcard $(VLLM_DIR)/models/*.conf))" >&2; \
		exit 1; }
	@test -f "$(VLLM_DIR)/models/$(MODEL).conf" || { \
		echo "error: no such vLLM model config: $(MODEL)" >&2; \
		echo "MODEL names models/<name>.conf, not the served model ID" >&2; \
		echo "available:" >&2; \
		echo "  $(patsubst $(VLLM_DIR)/models/%.conf,%,$(wildcard $(VLLM_DIR)/models/*.conf))" >&2; \
		exit 1; }

vllm-start: vllm-model-check
	@VLLM_VERSION=$(VLLM_VERSION) ./$(VLLM_DIR)/run.sh $(MODEL)

vllm-stop:
	@./$(VLLM_DIR)/stop.sh

vllm-status:
	@./$(VLLM_DIR)/status.sh

vllm-logs:
	@tail -f "$${XDG_STATE_HOME:-$${HOME}/.local/state}/vllm/server.log"

vllm-bench: vllm-model-check audit-bench-check
	@VLLM_VERSION=$(VLLM_VERSION) \
		VLLM_TRANSFORMERS_VERSION=$(VLLM_TRANSFORMERS_VERSION) \
		$(AUDIT_BENCH_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" \
		./$(VLLM_DIR)/bench.py $(MODEL)

vllm-capability: vllm-model-check audit-bench-check
	@$(CAPABILITY_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" \
		python3 ./$(VLLM_DIR)/capability.py $(MODEL)

# --- vLLM-Metal (Apple Silicon) ---
#
# The official vLLM plugin serving MLX-format models on Metal, loopback port
# 8021. Pinned release; see vllm-metal/AGENTS.md.
vllm-metal-model-check:
	@test -n "$(MODEL)" || { \
		echo "error: set MODEL=<name>" >&2; \
		echo "available:" >&2; \
		echo "  $(patsubst $(VLLM_METAL_DIR)/models/%.conf,%,$(wildcard $(VLLM_METAL_DIR)/models/*.conf))" >&2; \
		exit 1; }
	@test -f "$(VLLM_METAL_DIR)/models/$(MODEL).conf" || { \
		echo "error: no such vLLM-Metal model config: $(MODEL)" >&2; \
		echo "MODEL names models/<name>.conf, not the served model ID" >&2; \
		echo "available:" >&2; \
		echo "  $(patsubst $(VLLM_METAL_DIR)/models/%.conf,%,$(wildcard $(VLLM_METAL_DIR)/models/*.conf))" >&2; \
		exit 1; }

vllm-metal-install:
	@VLLM_METAL_VERSION=$(VLLM_METAL_VERSION) \
		VLLM_METAL_WHEEL_SHA256=$(VLLM_METAL_WHEEL_SHA256) \
		VLLM_METAL_VLLM_VERSION=$(VLLM_METAL_VLLM_VERSION) \
		VLLM_METAL_VLLM_WHEEL_SHA256=$(VLLM_METAL_VLLM_WHEEL_SHA256) \
		./$(VLLM_METAL_DIR)/install.sh

vllm-metal-pull: vllm-metal-model-check
	@./$(VLLM_METAL_DIR)/pull.sh $(MODEL)

vllm-metal-start: vllm-metal-model-check
	@VLLM_METAL_VERSION=$(VLLM_METAL_VERSION) \
		VLLM_METAL_VLLM_VERSION=$(VLLM_METAL_VLLM_VERSION) \
		./$(VLLM_METAL_DIR)/run.sh $(MODEL)

vllm-metal-stop:
	@./$(VLLM_METAL_DIR)/stop.sh

vllm-metal-status:
	@./$(VLLM_METAL_DIR)/status.sh

vllm-metal-logs:
	@tail -f "$${XDG_STATE_HOME:-$${HOME}/.local/state}/vllm-metal/server.log"

vllm-metal-bench: vllm-metal-model-check audit-bench-check
	@VLLM_METAL_VERSION=$(VLLM_METAL_VERSION) \
		VLLM_METAL_VLLM_VERSION=$(VLLM_METAL_VLLM_VERSION) \
		$(AUDIT_BENCH_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" \
		./$(VLLM_METAL_DIR)/bench.py $(MODEL)

vllm-metal-capability: vllm-metal-model-check audit-bench-check
	@$(CAPABILITY_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" \
		python3 ./$(VLLM_METAL_DIR)/capability.py $(MODEL)

# --- Splash (Apple Silicon M3+) ---

splash-model-check:
	@test -n "$(MODEL)" -a -f "$(SPLASH_MODEL_CONF)" || { \
		echo "error: set MODEL to a Splash config name:" >&2; \
		echo "  $(patsubst $(SPLASH_DIR)/models/%.conf,%,$(wildcard $(SPLASH_DIR)/models/*.conf))" >&2; \
		exit 1; }

splash-install:
	@./$(SPLASH_DIR)/install.sh

splash-pull: splash-model-check
	@SPLASH_MODEL_CONF="$(SPLASH_MODEL_CONF)" ./$(SPLASH_DIR)/pull.sh $(MODEL)

splash-start: splash-model-check
	@SPLASH_MODEL_CONF="$(SPLASH_MODEL_CONF)" ./$(SPLASH_DIR)/run.sh $(MODEL)

splash-stop:
	@./$(SPLASH_DIR)/stop.sh

splash-status:
	@./$(SPLASH_DIR)/status.sh

splash-logs:
	@tail -f "$${SPLASH_STATE_DIR:-$${XDG_STATE_HOME:-$${HOME}/.local/state}/splash}/server.log"

splash-bench: splash-model-check audit-bench-check
	@SPLASH_MODEL_CONF="$(SPLASH_MODEL_CONF)" $(AUDIT_BENCH_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" \
		bash -c 'source splash/lib.sh; exec uv run --no-project --python "$${SPLASH_RUNTIME}/python/bin/python3" splash/bench.py "$$1"' bash $(MODEL)

splash-capability: splash-model-check audit-bench-check
	@SPLASH_MODEL_CONF="$(SPLASH_MODEL_CONF)" $(CAPABILITY_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" \
		bash -c 'source splash/lib.sh; exec uv run --no-project --python "$${SPLASH_RUNTIME}/python/bin/python3" splash/capability.py "$$1"' bash $(MODEL)

# --- LM Studio ---

lmstudio-model-check:
	@test -n "$(MODEL)" -a -f "$(LMSTUDIO_DIR)/models/$(MODEL).conf" || { \
		echo "error: set MODEL to an LM Studio config name:" >&2; \
		echo "  $(patsubst $(LMSTUDIO_DIR)/models/%.conf,%,$(wildcard $(LMSTUDIO_DIR)/models/*.conf))" >&2; \
		exit 1; }

lmstudio-install:
	@python3 ./$(LMSTUDIO_DIR)/runtime.py install

lmstudio-pull: lmstudio-model-check
	@python3 ./$(LMSTUDIO_DIR)/runtime.py pull $(MODEL)

lmstudio-start: lmstudio-model-check
	@python3 ./$(LMSTUDIO_DIR)/runtime.py start $(MODEL)

lmstudio-stop:
	@python3 ./$(LMSTUDIO_DIR)/runtime.py stop

lmstudio-status:
	@python3 ./$(LMSTUDIO_DIR)/runtime.py status

lmstudio-logs:
	@tail -f "$${LMSTUDIO_STATE_DIR:-$${XDG_STATE_HOME:-$${HOME}/.local/state}/lmstudio}/server.log"

lmstudio-bench: lmstudio-model-check audit-bench-check
	@$(AUDIT_BENCH_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" python3 ./$(LMSTUDIO_DIR)/bench.py $(MODEL)

lmstudio-capability: lmstudio-model-check audit-bench-check
	@$(CAPABILITY_ENV) PYTHONPATH="$(AUDIT_BENCH_SRC)" python3 ./$(LMSTUDIO_DIR)/capability.py $(MODEL)

# --- Remote vLLM host ---
#
# The same scripts, executed on another machine. They are host-adaptive, so the
# remote copy needs no edits: the launcher derives backend, KV dtype and memory
# policy from that machine's GPU.
#
# venv/ is never synced. It holds gigabytes of platform-specific CUDA wheels
# and belongs to the remote host; vllm-remote-bootstrap creates it there.
#
# VLLM_ENV forwards the caller's VLLM_* overrides across the ssh boundary.
# ssh does not pass environment by default and sshd's AcceptEnv is restrictive,
# so without this every documented override (VLLM_MAX_LEN=... make vllm-...)
# silently does nothing remotely while working locally -- the remote server
# comes up on the config defaults and looks like it honoured the request.
#
# Only variables the caller actually set are forwarded, so an untouched one
# expands to nothing rather than to an empty assignment that would clobber the
# model config's ${VAR:-default}. The names below configure make itself rather
# than the launcher and are excluded: they are already interpolated into the
# recipes. MODEL is not a VLLM_* variable and is passed as run.sh's positional
# argument instead.
#
# Values are interpolated bare, inside the recipe's own single quotes. Every
# VLLM_* the launcher reads is a single shell token -- a number, an identifier,
# or a Hugging Face repo id -- so this holds; a value containing whitespace
# would need quoting that survives both shells and is not supported here.
VLLM_MAKE_VARS := VLLM_DIR VLLM_VERSION \
	VLLM_TRANSFORMERS_VERSION VLLM_REMOTE_DIR VLLM_REMOTE_PORT \
	VLLM_TUNNEL_PORT VLLM_ENV VLLM_MAKE_VARS
VLLM_ENV = $(strip $(foreach v, \
	$(filter-out $(VLLM_MAKE_VARS),$(filter VLLM_%,$(.VARIABLES))), \
	$(if $(filter environment% command line,$(origin $(v))),$(v)=$($(v)))))

vllm-remote-check:
	@test -n "$(HOST)" || { \
		echo "error: set HOST=<ssh-host> (see .envrc.example)" >&2; \
		exit 1; }

# The venv is created and populated with uv (falling back to the user
# install location when it is not on the non-interactive PATH). An existing
# venv is upgraded in place; recreate by removing it on the host first.
vllm-remote-bootstrap: vllm-remote-check
	@ssh $(HOST) 'set -e; mkdir -p $(VLLM_REMOTE_DIR); cd $(VLLM_REMOTE_DIR); \
		UV="$$(command -v uv || echo "$$HOME/.local/bin/uv")"; \
		test -x venv/bin/python || "$$UV" venv venv; \
		"$$UV" pip install --python venv/bin/python --quiet \
			vllm==$(VLLM_VERSION) \
			transformers==$(VLLM_TRANSFORMERS_VERSION) ninja; \
		./venv/bin/python -c "import transformers, vllm; \
			print(\"vllm\", vllm.__version__, \"transformers\", transformers.__version__)"'

vllm-remote-deploy: vllm-remote-check audit-bench-check
	@rsync -a --delete --exclude venv --exclude __pycache__ \
		./$(VLLM_DIR)/ $(HOST):$(VLLM_REMOTE_DIR)/
	@rsync -a "$(AUDIT_BENCH_SRC)/audit_bench.py" \
		$(HOST):$(VLLM_REMOTE_DIR)/audit_bench.py
	@rsync -a "$(AUDIT_BENCH_SRC)/capability_check.py" \
		$(HOST):$(VLLM_REMOTE_DIR)/capability_check.py
	@ssh $(HOST) 'chmod +x $(VLLM_REMOTE_DIR)/*.sh $(VLLM_REMOTE_DIR)/*.py'
	@echo "deployed to $(HOST):$(VLLM_REMOTE_DIR)"

# The internal vllm-remote-deploy step precedes targets that execute repo
# scripts the caller may have edited: start, bench, and capability. A stale
# remote copy is indistinguishable from a broken change, and the idempotent
# rsync is cheap insurance.
#
# The other remote verbs deliberately do NOT deploy. stop and status run against
# a server that on a shared host may not be the caller's, and deploy is
# rsync --delete: a teardown or a read-only status must not mutate the remote
# tree as a side effect. logs and tunnel run no repo script (tail, ssh -L), and
# bootstrap only builds the venv.
vllm-remote-start: vllm-remote-check vllm-model-check vllm-remote-deploy
	@ssh $(HOST) 'VLLM_VERSION=$(VLLM_VERSION) $(VLLM_ENV) $(VLLM_REMOTE_DIR)/run.sh $(MODEL)'

vllm-remote-stop: vllm-remote-check
	@ssh $(HOST) '$(VLLM_REMOTE_DIR)/stop.sh'

vllm-remote-status: vllm-remote-check
	@ssh $(HOST) '$(VLLM_REMOTE_DIR)/status.sh'

vllm-remote-logs: vllm-remote-check
	@ssh $(HOST) 'tail -f "$${XDG_STATE_HOME:-$$HOME/.local/state}/vllm/server.log"'

vllm-remote-bench: vllm-remote-check vllm-model-check vllm-remote-deploy
	@ssh $(HOST) 'VLLM_VERSION=$(VLLM_VERSION) \
		VLLM_TRANSFORMERS_VERSION=$(VLLM_TRANSFORMERS_VERSION) \
		$(VLLM_ENV) $(AUDIT_BENCH_ENV) \
		$(VLLM_REMOTE_DIR)/venv/bin/python $(VLLM_REMOTE_DIR)/bench.py $(MODEL)'

vllm-remote-capability: vllm-remote-check vllm-model-check vllm-remote-deploy
	@ssh $(HOST) '$(VLLM_ENV) $(CAPABILITY_ENV) \
		$(VLLM_REMOTE_DIR)/venv/bin/python \
		$(VLLM_REMOTE_DIR)/capability.py $(MODEL)'

# Forward the remote endpoint to this machine. Both ends bind loopback only, so
# a tunnel is the supported way to reach it -- the server has no authentication.
#
# The local side defaults to 8001, not 8000: a local vLLM server already owns
# 8000, and reusing it makes ssh fail with "bind: Address already in use".
# Override with VLLM_TUNNEL_PORT to forward somewhere else. SSH keepalives make
# a dead tunnel exit within about 90 seconds; this target does not reconnect.
vllm-remote-tunnel: vllm-remote-check
	@echo "forwarding localhost:$(VLLM_TUNNEL_PORT) -> $(HOST):$(VLLM_REMOTE_PORT) (Ctrl-C to stop)"
	@ssh -N -T \
		-o ExitOnForwardFailure=yes \
		-o ServerAliveInterval=30 \
		-o ServerAliveCountMax=3 \
		-o ConnectTimeout=10 \
		-L 127.0.0.1:$(VLLM_TUNNEL_PORT):127.0.0.1:$(VLLM_REMOTE_PORT) \
		$(HOST)

# --- All ---

all: lint test
