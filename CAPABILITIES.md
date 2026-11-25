# Capability Check campaigns

Capability Check is the gate for models in the serving inventory. Its
verdict is the compatibility of the engine and model combination: the
response semantics agents need, and audit-shaped work finished without engine
failures at the declared sampling. Audit aptitude is scored beside it, never
a verdict. AuditBench separately measures serving performance and
capacity. The protocol -- fixed checks, model expectations, and the mapping
from the retained JSON report to the tables below -- is defined in
[llm-audit-bench](https://github.com/tuminoid/llm-audit-bench)
(`docs/CAPABILITY.md`); this file holds the campaign runbook. Each hardware's
campaign inventory and results are on its page under
[docs/hardware/](docs/hardware/), linked from the [README](README.md#results-by-hardware).

Capability results never rank model quality or serving performance.

Schema enforcement is recorded and never gates: no audit client depends on
constrained decoding yet, and its failures are engine gaps.

## Running a campaign

Follow the campaign procedure in the protocol document, driving the servers with
this repository's targets. Run only the profiles marked Campaign on that
hardware's page; model configs for other hardware are not an implied campaign.
Import each retained JSON report into the hardware record with
`make results-import` and render with `make results`, never from the verdict the
check prints; record failures as failures, and never convert manual evidence
into a Capability Check pass. `uv run capability-check --list` (in the
llm-audit-bench checkout) names every retained report and
`uv run capability-check --show FILE` re-prints one.

Fitness samples at the model config's `<PREFIX>_SAMPLING`, so the config
must declare it.
`CAPABILITY_FITNESS_SAMPLES=0` makes an API-only run, which cannot promote a
model. `CAPABILITY_TIME_LIMIT=<minutes>` stops starting samples on a slow
host; the report keeps what ran and, unless a check already failed, reads
`undecided`, as does a local run stopped with one SIGINT or SIGTERM (a
second aborts it). Remote targets run over ssh without a tty, so a Ctrl-C
there leaves the remote check running: bound remote runs with the time
limit, or stop the process on the host. A host row follows the protocol
document's projection table.

Local lifecycle:

```bash
make vllm-start MODEL=<profile>
make vllm-capability MODEL=<profile>
make vllm-stop

make ollama-start MODEL=<profile>
make ollama-pull MODEL=<profile>
make ollama-capability MODEL=<profile>
make ollama-stop

make vllm-metal-start MODEL=<profile>
make vllm-metal-capability MODEL=<profile>
make vllm-metal-stop

make splash-start MODEL=<profile>
make splash-capability MODEL=<profile>
make splash-stop

make lmstudio-start MODEL=<profile>
make lmstudio-capability MODEL=<profile>
make lmstudio-stop

make kapitsa-start MODEL=<profile>
make kapitsa-capability MODEL=<profile>
make kapitsa-stop
```

Remote lifecycle:

```bash
make vllm-remote-status HOST=<host>
make vllm-remote-start HOST=<host> MODEL=<profile>
make vllm-remote-capability HOST=<host> MODEL=<profile>
make vllm-remote-stop HOST=<host>

make ollama-remote-status HOST=<host>
make ollama-remote-start HOST=<host> MODEL=<profile>
make ollama-remote-pull HOST=<host> MODEL=<profile>
make ollama-remote-capability HOST=<host> MODEL=<profile>
make ollama-remote-stop HOST=<host>

make strata-remote-status HOST=<host>
make strata-remote-start HOST=<host> MODEL=<profile>
make strata-remote-capability HOST=<host> MODEL=<profile>
make strata-remote-stop HOST=<host>
```

Always stop the server afterward and confirm resource release, including
after a failed check.

### Identity drift

A digest mismatch distinguishes two cases, and only one is drift. The
Ollama adapters consult the registry's manifest header (a few KB, no
download) before deciding:

- **Stale local store**: the registry still serves the pinned digest --
  the local tag simply predates an upstream tag move. The adapter pulls
  through the managed server automatically, landing exactly the
  already-reviewed artifact, and validates again. No pin changes, no
  human decision consumed. (This recovered the A100 store twice
  and blocked the RTX campaign, all manually, before it was
  automated.)
- **True drift**: the registry serves something other than the pin. The
  refusal stands and names all three digests (registry, pin, local).
  Drift is never permission to update a pin: retain the failed
  artifact, inspect the replacement manifest or Hugging Face revision,
  verify format, quantization, architecture, native context, and
  capabilities, then run one explicit identity override. Repin only
  after that artifact passes. If a benchmarked artifact changed, keep
  its performance numbers historical until the replacement is
  benchmarked -- and remember depth proofs are per digest.

An unreachable registry keeps the plain refusal: recovery is only
automatic when it is provably safe.

### Promotion rule

A model intended for agent workloads is promoted by the protocol
document's promotion rule: compatibility `passed`, never `undecided`, at the
default sample count, with tools declared in its model config. Its
reasoning result must match the model-config expectation. A throughput
result cannot override a capability failure.

Both tool-call checks offer the tools with automatic choice, so they exercise
the model's own tool syntax and the server's configured parser. A named choice
can satisfy the fixture through guided decoding without either being correct,
which is why tool-call evidence recorded before protocol SCHEMA_VERSION 4
proves nothing about parser compatibility.
