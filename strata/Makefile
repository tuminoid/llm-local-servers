# No targets here: prevent GNU Make's built-in script-copy rule.
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

.DEFAULT:
	@echo 'error: run make strata-{install,pull,start,status,logs,bench,capability,stop} or strata-remote-* from the repository root' >&2
	@exit 1
