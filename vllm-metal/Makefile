# No targets are defined here. vLLM-Metal is driven from the repository root
# so a misplaced `make start` cannot trigger GNU Make's built-in
# script-copy rule.
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

.DEFAULT:
	@echo "error: run vLLM-Metal targets from the repository root:" >&2
	@echo "  make vllm-metal-install" >&2
	@echo "  make vllm-metal-pull MODEL=<name>" >&2
	@echo "  make vllm-metal-start MODEL=<name>" >&2
	@echo "  make vllm-metal-status" >&2
	@echo "  make vllm-metal-bench MODEL=<name>" >&2
	@echo "  make vllm-metal-stop" >&2
	@exit 1
