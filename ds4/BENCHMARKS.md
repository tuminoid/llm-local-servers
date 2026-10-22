# ds4 measurements

ds4 serves models too large for any fleet host to run audit campaigns on,
so these are interactive-use measurements, not audit-throughput rankings.
They never enter the root README's ranked tables.

All rows: Apple M5 Max (128 GB, macOS 27.0), ds4 `0aaea5a`, the pinned
GGUFs in `models/`, 262,144 configured context, one slot and one stream,
each config's declared sampling. Measured 2026-09-30 to 2026-10-02 with the
pre-commit form of this directory (dirty tree), so every JSON is
`publishable: false`; most rows are one sample. Retained under
`~/.local/state/auditbench/trials/2026-09-30-ds4/`. The
`deepseek-v4.1-flash-q2` column is the 1017 checkpoint, measured 2026-10-19
(session) and 2026-10-20 (capability) at the 1017 card sampling, under
`~/.local/state/auditbench/trials/2026-10-19-m5-night/ds4/` and
`.../2026-10-20-m5-night/ds4/`.

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
| Audit fitness (passed of 12) | pass, 12/12 | pass, 11/12 (failed: invented 1) | pass, 11/12 (failed: no reasoning 1) | pass, 11/12 (failed: no reasoning 1) |

JSON in `results/`: `20260930T133325.585430+0000_ds4_qwen3-8-flash-next-q4.json`,
`20260930T104359.910549+0000_ds4_deepseek-v4-flash-q2.json`,
`20260930T120743.672386+0000_ds4_glm5-3-flash-q2.json`; V4.1 Flash 1017
`20261020T164000.412430+0000_ds4_deepseek-v4-1-flash-q2.json` in its trial
directory.

- `json_schema` fails on every model because ds4 has no structured output:
  `ds4_server.c` never parses `response_format`. Each model writes a valid
  document when the schema is stated in words. The check is advisory since
  llm-audit-bench 2.3.0, so Flash Next, V4 Flash and V4.1 Flash pass
  Capability Check v2; GLM fails on its tool calls.
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
| Turn decode, mid session | 69.3 tok/s | 33.4 tok/s | 54.2 tok/s | 14.7 tok/s |
| Report decode, ~160k deep | 60.9 tok/s | 27.2 tok/s | 26.9 tok/s | 14.2 tok/s |
| tg128 / pp512, depth ~0 | 54.4 / 848 (no MTP) | 45.6 / 481 | 35.1 / 362 | 14.6 / 30 |
| Session prefill | 1,277 tok/s | 420 tok/s | 364 tok/s | 629 tok/s |
| 245,760-token cold prompt | 200 s | 657 s | 717 s | 296 s |
| AuditBench session, diagnostic | 10.83/h (7.99 canonical median without MTP) | 4.80/h | 4.56/h | 2.68/h |
| Interactive agentic use | yes, the pick | yes, slower, larger model | no: string-typed tool arguments | yes, slow (SSD streaming) |

Qwen3.8 Flash Next and V4 Flash now serve 524,288; their deep-context
runs are in [524,288 context](#524288-context).

Speed JSON: Qwen `night/results/20261001T215057.822889+0000_ds4_qwen3-8-flash-next-q4_session.json`
(MTP) and `night/results/20261001T200439.042603+0000_ds4_qwen3-8-flash-next-q4_session.json`
(canonical, three samples); V4.1 Flash 1017
`20261019T204308.331989+0000_ds4_deepseek-v4-1-flash-q2_session.json` (12 of
17 calls streamed no reasoning); the others in `results-diskkv/`; cold-prompt
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
- **SSD streaming runs V4.1 on 128 GB** at about half of V4 Flash's decode;
  its tables read from the GGUF on every token, so speed depends on the
  SSD.

## 524,288 context

The tables above ran at 262,144. The Qwen and V4 Flash configs now serve
524,288, rechecked 2026-10-13 on the same host and pin from uncommitted
changes (`publishable: false`, one sample each). Deep sessions are
exploratory `AUDIT_BENCH_CONV_MAX_STEPS=50` at one stream. Retained under
`~/.local/state/auditbench/trials/2026-10-13-ds4-512k/`.

### Qwen3.8 Flash Next, static YaRN factor 2

- **Capability Check v2:** as at 262,144; audit fitness pass, 12/12, and
  `json_schema` fails (`ignored`).
  `results/20261013T174602.562772+0000_ds4_qwen3-8-flash-next-q4-512k.json`.
- **Deep session:** complete, the report decoded from 444,683 prompt tokens to its
  own stop, recalled 50 of 50 findings, no truncated or unreasoned calls;
  4.18 sessions/h, prefill 1,196 tok/s, turn decode 63.2/58.6/62.0, report
  57.0 tok/s, cached 0.935. A 491,538-token cold prompt took 427 s.
  `results/20261013T175206.079488+0000_ds4_qwen3-8-flash-next-q4-512k_session.json`.
- **Memory:** KV 16.66 GiB (raw 13.01 + compressed 3.66) + buffers
  15.24 GiB + model 69.73 GiB = 101.63 GiB planned; pressure stayed normal.

### DeepSeek V4 Flash and GLM 5.3 Flash

Both are trained to 1,048,576, so they need no YaRN. Above 393,216 ds4
stops downgrading `reasoning_effort` max to high; traced requests rendered
V4's max-effort prefix and GLM's "Reasoning Effort: Max".

- **V4 Flash capability:** audit fitness fail, 10/12 (selection: invented
  2), against 11/12 at 262,144; its prompts are far below either context,
  so this is sampling at the gate. `json_schema` fails (`ignored`).
  `results/20261013T191613.651852+0000_ds4_deepseek-v4-flash-q2.json`.
- **V4 Flash deep session,** twice: both complete, the report from 447,366
  prompt tokens recalling 50 of 50 findings.

  | Checkpoint budget | Wall | Sessions/h | Cached | Report: restored from, first token | Prefill | Turn decode first/mid/last | Report decode |
  | --: | --: | --: | --: | -- | --: | -- | --: |
  | 32 GiB (2026-10-13) | 5.0 h | 0.20 | 0.594 | 102,400, 1,478 s | 280 tok/s | 38.0/24.9/18.6 | 17.7 |
  | 128 GiB (2026-10-14, the config) | 2.2 h | 0.45 | 0.854 | 245,760, 1,018 s | 232 tok/s | 38.9/25.0/18.6 | 17.6 |

  The budget sets how deep the waypoints survive, not whether they do.
  V4's live state misses every step (the renderer keeps reasoning that
  clients drop), ds4 saves each diverged live state as an `evict`
  checkpoint (38 in the second run, 4.8-5.8 GiB each at depth), and its
  eviction score doubles for such anchors, so a full budget evicts the
  mid-prompt waypoints first. From about 245k every step restored the
  245,760 waypoint. The 491,518-token cold prompt that precedes the
  session filled part of the budget both times (1,953 s, 252 tok/s).
  `results/20261013T191613.869606+0000_ds4_deepseek-v4-flash-q2_session.json`,
  and from a clean tree (the JSON records `8200c38`, the merged config
  before a rebase) `results/20261014T090808.397409+0000_ds4_deepseek-v4-flash-q2_session.json`
  under `~/.local/state/auditbench/trials/2026-10-14-m5-day/`.
- **GLM 5.3 deep session:** incomplete; the report from 445,103 prompt
  tokens recalled 0 of 50 findings in 1,989 characters, and 48 of 51 calls
  streamed no reasoning, at cached 0.963. Its capability check matched
  262,144 (audit fitness 11/12, string-typed tool arguments). GLM stays at
  262,144, where the 16-step session recalled 16 of 16.
  `results/20261014T012312.788040+0000_ds4_glm5-3-flash-q2_session.json`.
- **Memory planned at 524,288:** V4 Flash 89.13 GiB (85.13 at 262,144),
  GLM 98.88 GiB (95.96).
