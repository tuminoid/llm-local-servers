# No targets are defined here. LM Studio is driven from the repository root so a
# misplaced `make start` cannot trigger GNU Make's built-in script-copy rule.
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

.DEFAULT:
	@echo "error: run LM Studio targets from the repository root:" >&2
	@echo "  make lmstudio-install" >&2
	@echo "  make lmstudio-pull MODEL=<name>" >&2
	@echo "  make lmstudio-start MODEL=<name>" >&2
	@echo "  make lmstudio-status" >&2
	@echo "  make lmstudio-bench MODEL=<name>" >&2
	@echo "  make lmstudio-stop" >&2
	@exit 1
