# Kapitsa benchmarks

## AuditBench v2: Apple M5 Max

Kapitsa 0.2.24 (release archive), the engine's own slot and memory plan
(four slots at 262,144 on this host), in-memory prefix reuse, SSD prefix
cache off. Clover decodes self-speculatively (`NI_CLOVER_DECODE=spec`,
threshold acceptance, the checkpoint's own penalties and ramps). Canonical
AuditBench v2 `session` profile at the conf's declared sampling on the M5
Max (128 GB, macOS 27.0.1), llm-audit-bench 2.4.0, from the clean fleet
commit `2457685`, 2026-10-28. The harness measured 1 stream and the
largest of 2/4/8 that fits admission and the KV pool: tool steps from 32k
evidence, 16 at 262,144 configured context, report at depth. Sessions/h is
the median over 3 samples; complete counts sessions whose report ended on
its own and named at least 7/8 of its findings. pp512/tg128 is the
llama-bench-method reference, not a serving result. JSON files are under
`~/.local/state/auditbench/`.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| Kapitsa `clover-35b-a3b` | 262,144 | 4 | 4,367,951 | 1x 25.44 / 4x 25.04 | 4,499 | 1,695.7 | 86.7 | 15/15 | unavailable | pass | yes | `20261028T182655.889811+0000_kapitsa_clover-35b-a3b_session.json` |

- Capability Check v2 passes 12 of 12. One stream is the optimal
  operating point; four streams hold the rate (0.98x) while per-stream
  decode falls to 5-32 tok/s.
- The KV pool is the KV room Kapitsa plans at load, shared by the slots'
  conversations (about 20 KB per token). The near-context phase
  (245,760-token prompt) read 1,191 tok/s at one stream.
- Kapitsa ends a response at EOS rather than at `max_tokens`, so the
  reference measurement is unavailable; it is a diagnostic only.

### Clover decode modes

Exploratory runs of 2026-10-28 on a source build of the same release
(`b46d9e5`), two slots, `AUDIT_BENCH_STREAMS=1,2` (non-canonical), under
`~/.local/state/auditbench/trials/2026-10-28-clover/m5/`. Capability Check
v2 audit fitness, then sessions/h:

| Mode | Fitness | Sessions/h 1x / 2x |
| -- | -- | -- |
| self-speculative, threshold (the conf) | 12/12 | 24.88 / 24.45 |
| self-speculative, `dllm_length_penalty` 0 | 12/12 | -- |
| self-speculative, `NI_CLOVER_ACCEPT=exact` | 8/12: triage format 3, selection invented 1 | -- |
| 35B DFlash2 drafter (`NI_CLOVER_DECODE=dflash`) | 8/12: workflow runaway 3, triage format 1 | 25.63 (2/3 complete) / 24.73 |

Exact acceptance decodes the causal pathway greedily with presence 0.9
counted on every reply token, reasoning included, and the triage answers
lose the array's brackets. The drafter mode decodes the same pathway at
the request's sampling without the model's `</think>` ramp, and the
workflow task never closes its thinking. Retest when a release changes
Clover's decode modes.
