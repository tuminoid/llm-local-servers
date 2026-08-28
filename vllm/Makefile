# No targets are defined here on purpose. The server is driven entirely from
# the repo root, per AGENTS.md ("Makefile-driven"), so this file exists
# only to fail loudly instead of letting GNU Make improvise.
#
# Without it, make finds no makefile in this directory, falls back to its
# built-in rules, and matches `%: %.sh` against the scripts sitting here:
#
#     $ make stop
#     cat stop.sh >stop
#     chmod a+x stop
#
# That stops nothing. It writes an executable, untracked, silently stale copy
# of stop.sh -- the worst kind of file to leave in a tree where a pidfile is the
# only handle on a running server. `make start`, `make status`, `make run` and
# `make bench` all did the same.
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

.DEFAULT:
	@echo "error: no make targets in vllm/; run these from the repo root:" >&2
	@echo >&2
	@echo "  make vllm-start   - Start detached, wait until serving" >&2
	@echo "  make vllm-stop    - Stop, verify the GPU was released" >&2
	@echo "  make vllm-status  - Process, GPU use, backend, KV cache sizing" >&2
	@echo "  make vllm-logs    - Follow the server log" >&2
	@echo "  make vllm-bench   - Run AuditBench v1 (from llm-audit-bench)" >&2
	@echo >&2
	@echo "  Remote host (HOST=<ssh-host> required):" >&2
	@echo "  make vllm-remote-{bootstrap,start,stop,status,logs,bench,tunnel}" >&2
	@echo >&2
	@echo "  Model selection: MODEL=<name> (models/<name>.conf)" >&2
	@exit 1
