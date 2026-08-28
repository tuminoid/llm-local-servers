# No targets are defined here. Ollama is driven from the repository root so a
# misplaced `make start` cannot trigger GNU Make's built-in script-copy rule.
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

.DEFAULT:
	@echo "error: run Ollama targets from the repository root:" >&2
	@echo "  make ollama-install" >&2
	@echo "  make ollama-start MODEL=<name>" >&2
	@echo "  make ollama-pull MODEL=<name>" >&2
	@echo "  make ollama-status" >&2
	@echo "  make ollama-bench MODEL=<name>" >&2
	@echo "  make ollama-stop" >&2
	@exit 1
