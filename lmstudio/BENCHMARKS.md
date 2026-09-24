# LM Studio benchmark results

Apple M5 Max, 128 GB, macOS 27.0, 140 W adapter behind the standard battery
gate, 2026-09-24. LM Studio 0.4.25+1 with the Splash engine 0.0.5 (Splash
1.0.2 source) and mlx-llm 1.11.0 (NAX build), 262,144 configured context.
Checkpoints and revisions are those of the native `splash/` and `vllm-metal/`
profiles.

## Decode smoke

AuditBench v1 `decode` profile: 1,024 output tokens, short prompt, median
aggregate output tok/s. A tuning aid, not a serving result: the profile is
`canonical: false` and so unpublishable. The runs are from a clean `2bbfce7`
tree on llm-audit-bench `382760d`.

| Config | Admitted streams | Decode 1 / 2 / 4 tok/s | Native reference |
| -- | --: | -- | -- |
| `qwen3.6-35b-a3b-splash` | 1 | 302.9 | Splash 1.0: 301.1 / 375.1 / 515.4 |
| `qwen3.8-27b-splash` | 1 | 79.6 | Splash 1.0: 67.3 / 119.6 / 152.0 |
| `qwen3.6-35b-a3b-mlx` | 4 | 134.5 / 212.6 / 307.5 | vLLM-Metal APC: 102.0 / 174.3 / 265.0 |
| `qwen3.8-27b-mlx` | 4 | 33.1 / 54.6 / 80.8 | vLLM-Metal APC: 28.8 / 52.8 / 82.6 |

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
