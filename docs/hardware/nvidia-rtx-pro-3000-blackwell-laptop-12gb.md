# NVIDIA RTX PRO 3000 Blackwell laptop GPU, 12 GB

Measured on a laptop with the RTX PRO 3000 Blackwell Generation Laptop GPU
(sm_120, 12,227 MiB VRAM), an Intel Core Ultra 9 285H and 62 GiB RAM. The
12 GB of VRAM decides what fits: every profile here runs entirely on the
GPU, ahead of context length, because a model with experts on the CPU is
several times slower.

The tables are rendered from
[nvidia-rtx-pro-3000-blackwell-laptop-12gb.json](nvidia-rtx-pro-3000-blackwell-laptop-12gb.json),
which `make results-import` fills from the retained harness JSON; never edit
a table by hand.

## Audit ranking

Canonical [AuditBench v3](https://github.com/tuminoid/llm-audit-bench)
`session` profile on Ollama 0.40.6, Flash Attention, one slot
(llm-audit-bench 3.0.0), run 2026-11-24 at each
conf's declared sampling: 16 tool steps at 262,144 configured context, 13 at
163,840 and 9 at 131,072. A later Ollama pin is not measured here. The
laptop also ran four virtual machines and was on its balanced power profile,
the GPU capped by software power limits: against the 2026-10-17
llm-audit-bench 2.1.0 rows (in git history) every profile prefilled 13-17%
slower and REAP-48 and Saluki decoded their reports 20-31% slower, so these
rates are a floor.

A ranked row passes Capability Check v3 compatibility and publishes its
optimal operating point: the fastest measured stream count whose sessions
all completed. Complete counts sessions whose report ended on its own and
named at least 7/8 of its findings. KV pool is Ollama's allocation,
configured context times slots, not a measured pool. pp512/tg128 is the
llama-bench-method reference (one stream, greedy, depth ~0), not a serving
result; Ollama has no `ignore_eos`, so it is unavailable where the model
stopped before 128 tokens. The OWASP vuln score is Capability Check v3's
audit aptitude: true-positive minus false-positive rate on 28 OWASP
BenchmarkPython cases (+1 perfect, 0 chance) with its 95% interval; the
intervals span about +-0.3, so rows stay ranked by rate.

<!-- results:audit -->

| Rank | Profile | Runtime | Engine | Tier | Context | Slots | KV pool | Best sessions/h | Other stream counts | Complete | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | pp512 / tg128 | OWASP vuln score [95% CI] | Publishable | Session JSON |
| --: | -- | -- | -- | -- | --: | --: | --: | --: | -- | -- | --: | --: | --: | -- | -- | -- | -- |
| 1 | `qwen3.6-35b-a3b-reap48` | Ollama | llama.cpp | MoE | 262,144 | 1 | 262,144 allocated | 5.74 @1x | -- | 3/3 | 5,464 | 830.3 | 15.4 | unavailable | +0.07 [-0.14, +0.26] | yes | `20261124T205015.123622+0000_ollama_qwen3-6-35b-a3b-reap48_session.json` |
| 2 | `saluki-27b` | Ollama | llama.cpp | dense | 163,840 | 1 | 163,840 allocated | 3.62 @1x | -- | 2/2 | 3,828 | 253.6 | 7.9 | unavailable | +0.29 [-0.09, +0.59] | yes | `20261124T212700.242161+0000_ollama_saluki-27b_session.json` |

<!-- /results:audit -->

- `qwen3.6-35b-a3b-reap48` runs its 16 steps with all 10.78 GiB on the GPU (6.74
  sessions/h on llm-audit-bench 2.1.0, 7.37 on Ollama 0.40.3). Turn decode falls
  from 51.5 to 20.0 tok/s across the session. q8_0 KV fits entirely only up to
  163,840 (196,608 puts 0.7 GB of experts on the CPU); an exploratory Ollama
  0.40.3 run there measured 11.68 sessions/h over 13 steps. Both KV types
  completed every session with no truncated tool call and every finding recalled
  on 0.40.3, so the model card's warning against sub-bf16 KV did not reproduce,
  and the profile keeps 262,144 with q4_0. Its sessions skip reasoning on most
  tool calls (37 of 51 unreasoned); the count never gates.
- `saluki-27b` runs its 13 steps with all 65 layers and its 10.92 GiB on the
  GPU (4.56 sessions/h on llm-audit-bench 2.1.0, 3.26 on Ollama 0.40.3). Turn
  decode falls from 12.7 to 8.1 tok/s across the session.

## Interactive profiles

<!-- results:interactive -->

| Profile | Runtime | Engine | Tier | Context | Slots | KV pool | Sessions/h by streams | Complete | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | pp512 / tg128 | Publishable | Session JSON |
| -- | -- | -- | -- | --: | --: | --: | -- | -- | --: | --: | --: | -- | -- | -- |
| `lfm2.5-24b-a2b` | Ollama | llama.cpp | MoE | 131,072 | 1 | 131,072 allocated | 1x 8.51 | 3/3 | 14,759 | 1,061.2 | 38.3 | 1,554 / 102.1 | yes | `20261124T221221.273338+0000_ollama_lfm2-5-24b-a2b_session.json` |

<!-- /results:interactive -->

- `lfm2.5-24b-a2b` fails Capability Check v3. Every session completed this
  time (one of two hit the output cap on llm-audit-bench 2.1.0). Its output
  tokens per session are 2.7x REAP-48's at half the steps, and every call
  counts as unreasoned, its reasoning reaching the client unseparated.

## Capability Check

Capability Check v3 (llm-audit-bench 3.0.0), run 2026-11-21 on Ollama
0.40.6. The protocol and the column mapping are
in llm-audit-bench `docs/CAPABILITY.md`, the campaign runbook in
[CAPABILITIES.md](../../CAPABILITIES.md). Campaign marks the profiles this
hardware's campaigns run. Model identity shows the first 12 characters of the
digest; every row's live identity matched the digest pinned in its model config.
An audit row's score is in the audit ranking.

<!-- results:capability -->

| Runtime | Profile | Campaign | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Clean samples | Compatibility | Audit aptitude | Model identity | Artifact |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Ollama | `qwen3.6-35b-a3b-reap48` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `a738d78e39f3` | `20261121T113025.392154+0000_ollama_qwen3-6-35b-a3b-reap48.json` |
| Ollama | `saluki-27b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 33 of 36 (92%); fitness 8 of 8 | passed | sound 6 of 8 | `4868fcc0efd9` | `20261121T143918.523126+0000_ollama_saluki-27b.json` |
| Ollama | `lfm2.5-24b-a2b` | yes | passed | passed | untested | supported | supported | supported | supported | valid | enforced (supported) | 4 of 8 (50%); fitness 4 of 8 | failed (fitness_clean, clean_rate) | not scored | `d4220f26c6dd` | `20261121T145211.214731+0000_ollama_lfm2-5-24b-a2b.json` |

<!-- /results:capability -->

- REAP-48 (+0.07) and Saluki (+0.29) pass; their intervals overlap.
- `lfm2.5-24b-a2b` fails fitness, 4 of 8 clean: three workflow runs wrote
  `audit/findings.json` with literal `\n` escapes, so it is not bare JSON, and
  one selection answer is an object instead of an array. Its card documents no
  thinking control, so thinking-off is untested.
