# LM Studio benchmark results

Apple M5 Max, 128 GB, macOS 27.0, 140 W adapter behind the standard battery
gate, 2026-09-24. LM Studio 0.4.25+1 with the Splash engine 0.0.5 (Splash
1.0.2 source) and mlx-llm 1.11.0 (NAX build), 262,144 configured context.
Checkpoints and revisions were those of the native `splash/` and
`vllm-metal/` profiles; the vLLM-Metal comparison rows are in
`vllm-metal/BENCHMARKS.md` at `a7e8f3f`.

## AuditBench v2: Apple M5 Max

LM Studio 0.4.25+1, Splash engine 0.0.5 (one request at a time) and mlx-llm
1.11.0. Canonical AuditBench v2 `session` profile (llm-audit-bench v2.0.0
plus the amendments released as v2.1.0; each JSON records its harness hash),
run 2026-09-27 to 2026-09-29 on the M5 Max (128 GB, macOS 27.0) from fleet
commit `bee4a24` at each conf's declared sampling. The harness measured 1
stream and the largest of 2/4/8 that fits admission and the KV pool: tool
steps from 32k evidence, 16 at 262,144 configured context and 9 at 131,072,
report at depth. Sessions/h is the median over 2-3 samples; complete counts
sessions whose report ended on its own and named at least 7/8 of its
findings. pp512/tg128 is the llama-bench-method reference (one stream,
greedy, depth ~0), not a serving result. JSON files are retained under
`~/.local/state/auditbench/trials/2026-09-27-v2-canonical/m5/`. Every later
section of this file is AuditBench v1 or older, never comparable with v2.
Their top-level retained JSON on the M5 and A100 was removed on 2026-09-30;
trial-directory copies remain, and the figures stay here and in git history.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| LM Studio `qwen3.6-35b-a3b-splash` | 262,144 | 1 | 262,144 | 1x 18.70 | 6,648 | - | 177.0 | 2/2 | 3,778 / 333.7 | fail | yes | `20260929T150023.857701+0000_lmstudio_qwen3-6-35b-a3b-splash_session.json` |
| LM Studio `qwen3.6-35b-a3b-mlx` | 262,144 | 4 | 1,048,576 | 1x 11.02 / 4x 9.15 | 5,622 | - | 64.1 | 9/10 | 1,868 / 141.3 | fail | no | `20260929T151009.883116+0000_lmstudio_qwen3-6-35b-a3b-mlx_session.json` |
| LM Studio `qwen3.8-27b-splash` | 262,144 | 1 | 262,144 | 1x 8.12 | 6,547 | - | 53.5 | 3/3 | unavailable | pass | yes | `20260928T040933.905525+0000_lmstudio_qwen3-8-27b-splash_session.json` |

- `qwen3.8-27b-splash` passes Capability Check v2 and is publishable at
  8.12 sessions/h, beside native Splash's 7.70.
- The MLX-engine profiles declare the protocol's off-by-one token
  allowance, so their runs are `canonical: false` by design; both fail
  Capability Check v2 on schema enforcement. `qwen3.8-27b-mlx`'s bench was
  stopped to give the campaign's time to canonical runs.
- `qwen3.6-35b-a3b-splash` publishes 18.70 sessions/h but fails audit
  fitness (3/12).

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
  `finish_reason` `length`.

Retained JSON, `~/.local/state/auditbench/`:

```text
20260924T082155.198028+0000_lmstudio_qwen3-6-35b-a3b-splash_decode.json
20260924T082102.844517+0000_lmstudio_qwen3-8-27b-splash_decode.json
20260924T083010.124185+0000_lmstudio_qwen3-6-35b-a3b-mlx_decode.json
20260924T082510.123755+0000_lmstudio_qwen3-8-27b-mlx_decode.json
20260924T053333.279091+0000_lmstudio_qwen3-8-27b-splash_decode.json
```

The last file is the four-stream trial run behind the admission finding.
Capability results are in [../CAPABILITIES.md](../CAPABILITIES.md).
