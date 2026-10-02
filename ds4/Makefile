# No targets are defined here. ds4 is driven from the repository root so a
# misplaced `make start` cannot trigger GNU Make's built-in script-copy rule.
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

.DEFAULT:
	@echo "error: run ds4 targets from the repository root:" >&2
	@echo "  make ds4-install" >&2
	@echo "  make ds4-pull MODEL=<name>" >&2
	@echo "  make ds4-start MODEL=<name>" >&2
	@echo "  make ds4-status" >&2
	@echo "  make ds4-logs" >&2
	@echo "  make ds4-capability MODEL=<name>" >&2
	@echo "  make ds4-bench MODEL=<name>" >&2
	@echo "  make ds4-stop" >&2
	@exit 1
