# LM Studio benchmark results

Apple M5 Max, 128 GB, macOS 27.0, 140 W adapter behind the standard battery
gate, 2026-09-24. LM Studio 0.4.25+1 with the Splash engine 0.0.5 (Splash
1.0.2 source) and mlx-llm 1.11.0 (NAX build), 262,144 configured context.
Checkpoints and revisions were those of the native `splash/` and
`vllm-metal/` profiles; the vLLM-Metal comparison rows are in
`vllm-metal/BENCHMARKS.md` at `a7e8f3f`.

## AuditBench v3: Apple M5 Max

LM Studio 0.4.25+1, Splash engine 1.3.0 (one request at a time) and mlx-llm
1.14.0. Canonical AuditBench v3 `session` profile (llm-audit-bench 3.0.0;
each JSON records its harness hash), run 2026-11-25 on the M5 Max (128 GB,
macOS 27.0.1) at each conf's declared sampling, the Splash-engine profiles
from fleet commit `5a7c007` (the engine 1.3.0 pin) and `qwen3.6-35b-a3b-mlx`
from `8ab4e09`. The harness climbs 1, 2, 4, 8 streams within admission while
each rung completes every session and gains 10%: tool
steps from 32k evidence, 16 at 262,144 configured context and 9 at 131,072,
report at depth. Sessions/h is the median over 2-3 samples; complete counts
sessions whose report ended on its own and named at least 7/8 of its
findings. pp512/tg128 is the llama-bench-method reference (one stream,
greedy, depth ~0), not a serving result. JSON files are retained under
`~/.local/state/auditbench/trials/2026-11-24-v3-sessions/`, in `m5-lmstudio/`
and `m5/`; the llm-audit-bench 2.0.0 rows (2026-09-27/29, fleet `bee4a24`,
Splash engine 0.0.5, mlx-llm 1.11.0) are in git history. Every later section
of this file is AuditBench v1 or older, never comparable with v3.
Their top-level retained JSON on the M5 and A100 was removed on 2026-09-30;
trial-directory copies remain, and the figures stay here and in git history.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v3 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| LM Studio `qwen3.6-35b-a3b-splash` | 262,144 | 1 | 262,144 | 1x 19.59 | 5,552 | - | 196.2 | 3/3 | 3,784 / 411.5 | pass | yes | `20261125T051059.051941+0000_lmstudio_qwen3-6-35b-a3b-splash_session.json` |
| LM Studio `qwen3.6-35b-a3b-mlx` | 262,144 | 4 | 1,048,576 | 1x 16.05 / 2x 11.05, incomplete | 4,440 | - | 71.6 | 5/6 | 2,754 / 148.8 | pass | no | `20261125T013213.017922+0000_lmstudio_qwen3-6-35b-a3b-mlx_session.json` |
| LM Studio `qwen3.8-27b-splash` | 262,144 | 1 | 262,144 | 1x 9.42 | 3,967 | - | 56.3 | 3/3 | unavailable | pass | yes | `20261125T054544.743268+0000_lmstudio_qwen3-8-27b-splash_session.json` |

- Capability Check v3 (llm-audit-bench 3.0.0, 2026-11-20, fleet `a21fd8a`;
  rows in [CAPABILITIES.md](../CAPABILITIES.md)) passes every profile but
  `qwen3.8-27b-mlx`, whose mlx-llm 1.14.0 engine crashed on a Metal
  resource limit mid-check. The two Splash-engine profiles were re-checked
  on engine 1.3.0 (2026-11-25, `5a7c007`) and pass again.
- `qwen3.8-27b-splash` passes and is publishable at 9.42 sessions/h,
  beside native Splash's 9.16 on the mlx-community target
  ([../splash/BENCHMARKS.md](../splash/BENCHMARKS.md)).
- The MLX-engine profiles declare the protocol's off-by-one token
  allowance, so their runs are `canonical: false` by design. They ignore
  the schema, which never gates. `qwen3.8-27b-mlx`'s bench was
  stopped to give the campaign's time to canonical runs.
  `qwen3.6-35b-a3b-mlx` re-ran on mlx-llm 1.14.0: one of four 2x sessions
  was incomplete, so one stream is its operating point.
- `qwen3.6-35b-a3b-splash` publishes 19.59 sessions/h and passes.

## Decode smoke

AuditBench v1 `decode` profile: 1,024 output tokens, short prompt, median
aggregate output tok/s. A tuning aid, not a serving result: the profile is
`canonical: false` and so unpublishable. The runs are from a clean `2bbfce7`
tree on llm-audit-bench `382760d`.

| Config | Admitted streams | Decode 1 / 2 / 4 tok/s | Native reference |
| -- | --: | -- | -- |
| `qwen3.6-35b-a3b-splash` | 1 | 302.9 | Splash 1.0: 301.1 / 375.1 / 515.4 |
| `qwen3.8-27b-splash` | 1 | 79.6 | Splash 1.0: 67.3 / 119.6 / 152.0 |
| `qwen3.6-35b-a3b-mlx` | 4 | 134.5 / 212.6 / 307.5 | vLLM-Metal APC: 102.0 / 174.3 / 265.0 (dropped profile) |
| `qwen3.8-27b-mlx` | 4 | 33.1 / 54.6 / 80.8 | vLLM-Metal APC: 28.8 / 52.8 / 82.6 (dropped profile) |

- LM Studio serves Splash one request at a time and ignores `--parallel`.
  A trial run from the uncommitted tree admitted four qwen3.8 streams and
  measured 80.1 / 83.7 / 81.2 tok/s, with the 4-stream wall at 3.9x the
  1-stream wall, so Splash configs admit one stream. Native Splash runs four
  lanes.
- The MLX rows ran with `AUDIT_BENCH_TOLERATE_OFF_BY_ONE=1`: mlx-llm 1.11.0
  reported every length-capped response one token short, exactly, with
  `finish_reason` `length`; 1.13.1 still does (2026-10-14).

JSON names, removed from `~/.local/state/auditbench/` with the other v1
results on 2026-09-30 (no trial-directory copies):

```text
20260924T082155.198028+0000_lmstudio_qwen3-6-35b-a3b-splash_decode.json
20260924T082102.844517+0000_lmstudio_qwen3-8-27b-splash_decode.json
20260924T083010.124185+0000_lmstudio_qwen3-6-35b-a3b-mlx_decode.json
20260924T082510.123755+0000_lmstudio_qwen3-8-27b-mlx_decode.json
20260924T053333.279091+0000_lmstudio_qwen3-8-27b-splash_decode.json
```

The last file is the four-stream trial run behind the admission finding.
Capability results are in [../CAPABILITIES.md](../CAPABILITIES.md).
