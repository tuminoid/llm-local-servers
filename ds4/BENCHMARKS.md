# ds4 measurements

ds4 serves models too large for any fleet host to run audit campaigns on,
so these are interactive-use measurements, not audit-throughput rankings.
They never enter the root README's ranked tables.

All rows: Apple M5 Max (128 GB, macOS 27.0), ds4 `0aaea5a`, the pinned
GGUFs in `models/`, 262,144 configured context, one slot and one stream,
each config's declared sampling. Measured 2026-09-30 to 2026-10-02 with the
pre-commit form of this directory (dirty tree), so every JSON is
`publishable: false`; most rows are one sample. Retained under
`~/.local/state/auditbench/trials/2026-09-30-ds4/`.

## Capability Check v2

| Check | `qwen3.8-flash-next-q4` | `deepseek-v4-flash-q2` | `glm5.3-flash-q2` | `deepseek-v4.1-flash-q2` |
| -- | -- | -- | -- | -- |
| Streaming reasoning | pass | pass | pass | pass |
| Thinking disabled | pass | pass | pass | pass |
| Tool call / streaming | pass / pass | pass / pass | fail / fail | pass / pass |
| Tool round trip | pass | pass | skipped | pass |
| Structured JSON | pass | pass | pass | pass |
| `json_schema` | fail (`ignored`) | fail (`ignored`) | fail (`ignored`) | fail (`ignored`) |
| Unaided document | valid | valid | valid | valid |
| Audit fitness | pass, 0/12 failed | pass, 1/12 (invented 1) | pass, 1/12 (no reasoning 1) | fail, 5/12 (runaway 4, no reasoning 1) |

JSON in `results/`: `20260930T133325.585430+0000_ds4_qwen3-8-flash-next-q4.json`,
`20260930T104359.910549+0000_ds4_deepseek-v4-flash-q2.json`,
`20260930T120743.672386+0000_ds4_glm5-3-flash-q2.json`,
`20260930T173650.093690+0000_ds4_deepseek-v4-1-flash-q2.json`.

- `json_schema` fails on every model because ds4 has no structured output:
  `ds4_server.c` never parses `response_format`. Each model writes a valid
  document when the schema is stated in words. Retest when it does.
- GLM's tool parser emits every argument as a JSON string
  (`tool_call_json_args_add(..., "true")` in its `<arg_value>` parser), so
  `{"issue_number": 42}` arrives as `"42"`. GLM's tool format carries no
  types and ds4 does not consult the request's schema; DeepSeek's DSML has
  a per-parameter `string=` attribute and is unaffected.

## Speed

The launcher defaults: disk KV checkpoints on, MTP at exact sampling on
Qwen only.

| | `qwen3.8-flash-next-q4` | `deepseek-v4-flash-q2` | `glm5.3-flash-q2` | `deepseek-v4.1-flash-q2` |
| -- | --: | --: | --: | --: |
| Residency | resident | resident | resident | SSD streaming |
| Planned memory | 89.30 GiB | 85.13 GiB | 95.96 GiB | 9.37 GiB locked + 83.00 GiB expert cache |
| KV at 262,144 | 8.33 GiB | 2.36 GiB | 2.92 GiB | in 10.4 GiB static buffers |
| Turn decode, mid session | 69.3 tok/s | 33.4 tok/s | 54.2 tok/s | 21.8 tok/s |
| Report decode, ~160k deep | 60.9 tok/s | 27.2 tok/s | 26.9 tok/s | 13.4 tok/s |
| tg128 / pp512, depth ~0 | 54.4 / 848 (no MTP) | 45.6 / 481 | 35.1 / 362 | 15.6 / 30 |
| Session prefill | 1,277 tok/s | 420 tok/s | 364 tok/s | 544 tok/s |
| 245,760-token cold prompt | 200 s | 657 s | 717 s | 298 s |
| AuditBench session, diagnostic | 10.83/h (7.99 canonical median without MTP) | 4.80/h | 4.56/h | 3.36/h |
| Interactive agentic use | yes, the pick | yes, slower, larger model | no: string-typed tool arguments | no: slow, fails audit fitness |

Speed JSON: Qwen `night/results/20261001T215057.822889+0000_ds4_qwen3-8-flash-next-q4_session.json`
(MTP) and `night/results/20261001T200439.042603+0000_ds4_qwen3-8-flash-next-q4_session.json`
(canonical, three samples); the others in `results-diskkv/`; cold-prompt
times from the `results/` session runs, which ran before disk KV.

## What the measurements established

- **Disk KV checkpoints are required.** ds4 cannot rewind its live state
  to a common prefix, and its DeepSeek renderer keeps tool-turn reasoning
  that clients drop, so without checkpoints every V4 Flash step
  re-prefilled the whole conversation: 1.21 sessions/h, cached fraction
  0.14, against 4.80 and 0.83 with them. Qwen gains less (7.19 to 10.28,
  one sample each) because ds4 keeps a Qwen-only end-of-prompt
  checkpoint.
- **Qwen's checkpoint misses by one token on early steps.** The prompt ends
  with `<think>` + `\n` (token 198); the resent history renders that turn
  as `<think>\n\n</think>`, tokenized `<think>` + `\n\n` (token 271), so
  the shared prefix stops one token short of the checkpoint. Disk
  checkpoints cover it.
- **One slot.** With two sessions active, ds4 slices one session's prefill
  into 128-token chunks between the other's decode steps: per-stream
  decode fell to 2-4 tok/s and prefill halved. Qwen 7.99 sessions/h at one
  stream against 4.94 at two; V4 Flash 1.67 against 1.51 aggregate.
  `DS4_SLOTS` stays for larger hosts.
- **MTP at exact sampling helps Qwen only.** Qwen: decode +28% mid
  session, +17% at the report. GLM: tool-request decode fell to about
  11 tok/s from 54. V4 Flash with DSpark: every decode stall (0.01-0.9
  tok/s, one 55-token tool call took 899 s) was inside a DSML tool-call
  block; 0.31 sessions/h.
- **Compressed attention keeps deep context cheap:** 2.4-8.3 GiB of KV at
  262,144 tokens beside 70-90 GiB of weights.
- **SSD streaming runs V4.1 on 128 GB** at a third of V4 Flash's decode;
  its tables read from the GGUF on every token, so speed depends on the
  SSD.
