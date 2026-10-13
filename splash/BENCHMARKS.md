# Splash benchmarks

## AuditBench v2: Apple M5 Max

Splash 1.3.1, 64 GiB native memory cap, four active slots, DFlash 2, Q8 KV,
state/prefix caching, the dense target's Neural Engine FFN split and idle
weight release at release defaults; mlx-community 4-bit targets with their
DFlash2 drafts pinned in the model configs. Canonical AuditBench v2
`session` profile (llm-audit-bench v2.1.0 plus the triage amendment
`c0dc34a`; each JSON records its harness hash), run 2026-10-11 to
2026-10-12 on the M5 Max (128 GB, macOS 27.0.1) from fleet commit `036bfd0`
at each conf's declared sampling. The harness measured 1 stream and the
largest of 2/4/8 that fits admission and the KV pool: tool steps from 32k
evidence, 16 at 262,144 configured context, report at depth. Sessions/h is
the median over 3 samples; complete counts sessions whose report ended on
its own and named at least 7/8 of its findings. pp512/tg128 is the
llama-bench-method reference (one stream, greedy, depth ~0), not a serving
result. JSON files are retained under
`~/.local/state/auditbench/trials/2026-10-11-splash-1.3.1/canonical/`.
Every later top-level section of this file is AuditBench v1 or older,
never comparable with v2. Their top-level retained JSON on the M5 and A100 was
removed on 2026-09-30; trial-directory copies remain, and the figures stay
here and in git history.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| Splash `qwen3.6-35b-a3b` | 262,144 | 4 | 4,358,144 | 1x 17.95 / 4x 16.88 | 4,309 | 1,652.2 | 185.2 | 13/15 | 4,199 / 370.7 | pass | no | `20261011T200744.932825+0000_splash_qwen3-6-35b-a3b_session.json` |
| Splash `qwen3.8-27b` | 262,144 | 4 | 1,437,696 | 1x 6.73 / 4x 7.47 | 9,764 | 470.0 | 50.5 | 15/15 | 750 / 101.2 | pass | yes | `20261011T212839.601051+0000_splash_qwen3-8-27b_session.json` |

- Both profiles pass Capability Check v2: `qwen3.6-35b-a3b` 11 of 12 (failed:
  invented 1), `qwen3.8-27b` 12 of 12. `qwen3.8-27b` is publishable at 6.73
  sessions/h; `qwen3.6-35b-a3b` leads the host at 17.95 but two of 15 sessions
  were incomplete.
- Four streams beat one on `qwen3.8-27b` (1.11x) and stay just below one
  on `qwen3.6-35b-a3b` (0.94x).

### Against Splash 1.0

- The 1.0 rows of 2026-09-27 served the Splash packages that 1.3.1 no
  longer loads (upstream #335), from fleet commit `bee4a24` on macOS 27.0
  (`20260927T233225.886443+0000_splash_qwen3-6-35b-a3b_session.json` and
  `20260928T005848.757558+0000_splash_qwen3-8-27b_session.json` under
  `~/.local/state/auditbench/trials/2026-09-27-v2-canonical/m5/`). Against
  them one stream fell on both models (qwen3.6 19.77 to 17.95, qwen3.8
  7.70 to 6.73), four streams held or rose (15.93 to 16.88, 7.53 to 7.47),
  and near-context input fell (qwen3.6 1,436 / 1,449 to 1,371 / 1,316
  tok/s at 1x / 4x, qwen3.8 405 / 405 to 376 / 375). The host moved from
  macOS 27.0 to 27.0.1 in between.
- For `qwen3.6-35b-a3b` that loss is the host on the day, not the
  release. A same-day 1.0 session from fleet commit `862ec7d`, run on
  2026-10-12 right after the 1.3.1 rows, measured 1x 16.79 / 4x 14.15
  sessions/h, near-context 1,321 / 1,297 tok/s and pp512 3,647, each below
  1.3.1 (`20261012T003601.579185+0000_splash_qwen3-6-35b-a3b_session.json`,
  in the trial's `ab-1.0/`). An earlier 1.3.1 trial session that day
  reached 1,434 tok/s near-context at 1x
  (`20261011T114855.523321+0000_splash_qwen3-6-35b-a3b_session.json`, in
  `results/`).
- The `qwen3.8-27b` drop is not attributed: its target (package to
  mlx-community 4-bit), the Neural Engine FFN split new in 1.3.0 and the
  OS all changed, and there is no same-day 1.0 qwen3.8 run. Its 1.3.1
  trial session measured 384 tok/s near-context at 1x.
- The Mac reached thermal state `fair` within two minutes of each
  canonical start; 1.0 does not report it.
- `qwen3.6-35b-a3b` sits at the audit-fitness limit on both releases: the
  same-day 1.0 checks passed only 9 and 10 of 12 (invented paths, one
  instruction miss, one runaway), and a 1.3.1 trial run failed at 10 of 12
  before the canonical 11-of-12 pass. Its gate result is a draw from that
  rate, not a release property.

### Growing conversation (2026-10-12)

The canonical `conversation` profile on 1.3.1, from fleet commit
`a0bd505` with the same harness: `qwen3.6-35b-a3b` complied in both
samples, reading all 16 files and recalling all 16 findings, at 96.0 s
per conversation (37.5 conversations/h), final prompts of 165,418 to
165,643 tokens and 90.2% of prompt tokens from cache. It is canonical and
publishable (`20261012T181255.410214+0000_splash_qwen3-6-35b-a3b_conversation.json`,
under `~/.local/state/auditbench/trials/2026-10-12-m5-night/results/`).
The 1.0 failure of one sample in two, below, was an AuditBench v1 run;
two compliant samples do not show that the failure rate fell.

### Qwen3.8 27B UD-Q4_K_M GGUF, exploratory (2026-10-11)

Splash 1.1.0 and later also serve `unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M`,
which upstream recommends over the uniform 4-bit MLX checkpoint for
thinking loops (upstream #326). An uncommitted profile at revision
`4ca72078` with the same DFlash2 draft and sampling ran two Capability
Check v2 runs and one session on 1.3.1. It was not kept:

- `json_schema` failed both runs with identical retained output (the
  first 8,000 of 17,721 characters; equal length): the check decodes
  greedily, and under the schema grammar the model invents a
  `sk_live_...` token in a finding's evidence string, then repeats a
  180-character alphanumeric cycle until the 16,384-token budget ends, so
  the document never closes. The unaided document is valid; audit fitness
  passed 12 of 12 both times. The MLX target passes the same check.
- Its session (1x 6.66 / 4x 7.20 sessions/h, prefill 448.9 tok/s 1x) is
  no faster than the MLX target, which ran 6.41 to 6.73 at 1x and 7.47 to
  7.65 at 4x on 1.3.1.
- Retest when a release changes grammar-constrained decoding or the GGUF
  target kernels: rerun Capability Check v2 first.

## Managed campaign, Apple M5 Max, 2026-09-19 to 2026-09-20

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 40 GPU
cores, 128 GiB unified memory, macOS 27.0 build 26A428. Both pinned
profiles completed `full`, `conversation`, `replay` and
`replay-concurrent` through the managed, uv-driven root Make targets.
All eight retained reports have `canonical: true`, `publishable: true`
and no publication reasons. Publication provenance and conversation
fixture compliance are separate: Qwen3.6 failed one conversation sample.
Both models passed all eight capability checks, including schema
enforcement; see [CAPABILITIES.md](../CAPABILITIES.md).

The operating point was 262,144 configured tokens, a 64 GiB native
memory cap, four active slots, DFlash 2, Q8 KV and state/prefix caching
at release defaults. `reasoning_effort` was unset and the request timeout
was 7,200 seconds. Release and package identities match the pinned
configs and the trials below. Canonical stream candidates remain
1/2/4/8; native admission excludes eight. No workload overrides were used.

Qwen3.6 `full` used clean fleet commit `9d2e99b`; the other seven
reports used clean `1e4a42f`, after fixes to teardown polling and the
adapter's shared conversation/replay transport hook. Runtime, model and
workload settings did not change. The shared `audit_bench.py` matches
commit `8b39ee2`, SHA-256
`ee10944f7b1287bbe382708aee70804731731d0bb92ca93754427057bbf2c98b`.
Every report retains exact adapter/config hashes, fully checked model
identity and the live memory plan.

### Full profile

Medians from the retained JSON. Decode is aggregate end-to-end output
tok/s; audit rates are aggregate completed calls/hour.

| Profile | Decode 1/2/4 tok/s | Audit 32k 1/2/4 /h | Audit half 1x /h | Audit deep 1/4 /h |
| -- | --: | --: | --: | --: |
| `qwen3.6-35b-a3b` | 301.08 / 375.05 / 515.42 | 331.96 / 348.98 / 375.25 | 58.67 | 23.40 / 23.18 |
| `qwen3.8-27b` | 67.31 / 119.61 / 152.03 | 63.16 / 65.52 / 66.38 | 14.28 | 6.62 / 6.58 |

| Profile | Prefill 32k/64k/128k tok/s | Measured prefill input tokens | Near-context input per stream | Near-context wall seconds, 1/4 streams |
| -- | --: | --: | --: | --: |
| `qwen3.6-35b-a3b` | 4,454.50 / 3,241.15 / 2,237.37 | 32,780 / 65,547 / 131,071 | 245,752 | 173.44 / 692.61 |
| `qwen3.8-27b` | 796.35 / 704.46 / 558.69 | 32,784 / 65,556 / 131,075 | 245,748 | 602.03 / 2,406.49 |

The 32k and half audits use the first and third measured input counts
above, with 1,024 output tokens. Deep audits use 229,362 input tokens
for Qwen3.6 and 229,366 for Qwen3.8, with 256 output tokens. Prefill
and near-context phases request one output token. Four-way deep
execution is supported but does not multiply aggregate audit throughput.

### Growing conversation and fixed replay

Both profiles use 16 tool steps. Configured context is 262,144; the
measured verdict inputs below are about 164k, not 230k. Conversation
checks whether the model follows the tool loop. Replay fixes the
transcript and measures serving behavior independently of tool selection.

| Profile | Conversation compliance | Conversations/hour | Final input tokens | Cached input fraction |
| -- | -- | --: | --: | --: |
| `qwen3.6-35b-a3b` | 1/2 samples; unranked | 37.16 (sole compliant sample) | 164,744 in the compliant sample | 90.19% in the compliant sample |
| `qwen3.8-27b` | 2/2 samples | 10.29 (10.18-10.39) | 164,143-164,198 | 90.20% |

Qwen3.6's first sample read all 16 files and recalled all 16 findings.
Its second returned a verdict after one file, with 15 files remaining
and only 41,338 final input tokens. The JSON's 37.16/h rate summarizes
the sole compliant sample and must not enter the serving ranking.
This is an observed fixture failure, not a root-caused model or cache
defect. Retest the canonical conversation after changes to the runtime,
model, draft or template before promoting this conversation operating point.
Qwen3.8 read all 16 files and recalled all 16 findings in both samples.

| Profile | Fixed replay/hour | Verdict input tokens | Verdict output tokens / finish | Verdict output tok/s | Cached input fraction |
| -- | --: | --: | -- | --: | --: |
| `qwen3.6-35b-a3b` | 15.09 (15.09-15.10) | 164,671 | 16,384 / length limit, both samples | 112.55 | 82.86% |
| `qwen3.8-27b` | 10.17 (10.13-10.21) | 164,175 | 1,293-1,445 / stop | 32.74 | 90.20% |

Fixed replay uses 32-token probe caps and a 16,384-token verdict cap.
Verdict tok/s is end-to-end for that request. The different realized
output lengths matter when comparing the two models' replay rates.

### Concurrent replay

This separate profile uses 1,024-token probe caps and the same
16,384-token verdict cap. Its rates are not interchangeable with the
32-token-probe replay above. The harness ran alternating 1/2/4 and
4/2/1 passes. Qwen3.6 finished with two samples per count; Qwen3.8
required the canonical third 1/2/4 pass after exceeding 5% disagreement.

| Profile | Aggregate replay/hour, 1/2/4 streams | Observed rate ranges, 1/2/4 | Per-stream verdict tok/s, 1/2/4 | Cached input fraction, 1/2/4 |
| -- | --: | -- | --: | --: |
| `qwen3.6-35b-a3b` | 12.91 / 12.35 / 12.38 | 12.68-13.14 / 12.18-12.52 / 12.30-12.46 | 227.97 / 144.81 / 82.07 | 80.86% / 81.82% / 82.71% |
| `qwen3.8-27b` | 4.38 / 4.32 / 4.06 | 4.17-4.52 / 4.21-4.36 / 4.02-4.19 | 21.53 / 13.06 / 7.91 | 80.90% / 81.93% / 82.22% |

Both models peak at one stream in aggregate replay/hour. Four streams
provide concurrent sessions, with longer per-session latency. Qwen3.6
verdict inputs were 164,671-164,687 tokens and every verdict used the
full 16,384-token cap. Qwen3.8 inputs were 164,175-164,191; verdicts
stopped naturally at 1,287-2,203 output tokens. Probe completion medians
were 1,024 tokens for Qwen3.6 and 820 / 755 / 904.5 for Qwen3.8 at
1/2/4 streams. Verdict tok/s above is the harness's per-stream median,
not aggregate throughput.

### Capacity, stability and teardown

| Profile | Configured context | Active slots | Native virtual KV tokens | Conservative benchmark KV tokens | Campaign native peak GiB |
| -- | --: | --: | --: | --: | --: |
| `qwen3.6-35b-a3b` | 262,144 | 4 | 4,415,488 | 4,358,144 | 63.25 |
| `qwen3.8-27b` | 262,144 | 4 | 1,474,560 | 1,445,888 | 63.25 |

Virtual KV is sparse capacity, not committed memory. The conservative
bound reserves all four active state cells inside the dynamic budget.
The near-context measurements prove four admitted requests at their
listed input depths. Native counters also recorded four-wide decode.

Across the eight retained runs, all 880 submitted requests completed
(including capability, warmup and calibration traffic), with zero
failed/cancelled requests, capacity failures, Metal failures or resource
suspensions. Sampled memory pressure stayed normal and charger negotiation
stayed at 140 W. Qwen3.8 paused between batches for the standard battery
gate; these pauses are outside measured request wall times. Optional
checkpoint publication failures and state evictions did occur; they are
separate from inference failures and remain in the native telemetry.

Two teardowns required recovery after valid reports had been retained.
The first Qwen3.6 full run encountered macOS EPERM while checking the
exiting group; `cf98de4` fixed polling, and later teardowns exercised it.
The final Qwen3.8 concurrent run reached the 30-second escalation check,
where ownership validation rejected an unrecognized group member. Its
exact `ps` row was not retained, so the exit-state cause is not proven.
By subsequent inspection the group was empty; a second root
`make splash-stop` verified group and port release. The original campaign
manifests retain their failure status. Recovery evidence establishes final
cleanup without rewriting those failures. Retest this ownership check
after a long, cache-filled run when changing shutdown handling; readiness
or a short lifecycle alone does not cover it.

### Retained campaign evidence

Evidence roots under `~/.local/state/auditbench/trials/` on the measured host:

- `2026-09-19-splash-campaign/`: Qwen3.6 full and its capability check.
- `2026-09-19-splash-campaign-continuation2/`: the other seven reports,
  Qwen3.8 capability, final `validation.json` and recovery evidence.

Each report is under `<profile-name>-<benchmark-profile>/auditbench/`
within its root. Campaign manifests record commands, source hashes and
exit codes; run directories retain native telemetry and server logs.

| Profile | Benchmark | JSON filename |
| -- | -- | -- |
| `qwen3.6-35b-a3b` | full | `20260919T195925.456946+0000_splash_qwen3-6-35b-a3b_full.json` |
| `qwen3.6-35b-a3b` | conversation | `20260919T205701.690098+0000_splash_qwen3-6-35b-a3b_conversation.json` |
| `qwen3.6-35b-a3b` | replay | `20260919T205920.345224+0000_splash_qwen3-6-35b-a3b_replay.json` |
| `qwen3.6-35b-a3b` | replay-concurrent | `20260919T210748.323111+0000_splash_qwen3-6-35b-a3b_replay-concurrent.json` |
| `qwen3.8-27b` | full | `20260919T221622.423875+0000_splash_qwen3-8-27b_full.json` |
| `qwen3.8-27b` | conversation | `20260920T013452.454541+0000_splash_qwen3-8-27b_conversation.json` |
| `qwen3.8-27b` | replay | `20260920T014717.027791+0000_splash_qwen3-8-27b_replay.json` |
| `qwen3.8-27b` | replay-concurrent | `20260920T015948.044687+0000_splash_qwen3-8-27b_replay-concurrent.json` |

## Pre-integration full trials, Apple M5 Max, 2026-09-19

Host: MacBook Pro `Mac17,6`, Apple M5 Max, 40 GPU
cores, 128 GiB unified memory, macOS 27.0 build 26A428. These full
AuditBench v1 runs preceded the managed integration and used the
same release engine, model artifacts, 262,144-token context and 64 GiB
ceiling now configured here. They are `canonical: true` and
`publishable: false`, with `repository_dirty` as the publication reason.
Their trial adapter provenance is retained; these are not claimed as
clean-commit runs of the new managed adapter.

Release archive, native binary and model pins are checked by the managed
installer/launcher. The full runs used the Homebrew 1.0 distribution;
the managed runtime uses the standalone 1.0 archive with the identical
native engine and metallib hashes. DFlash 2 and state/prefix caching
were enabled at release defaults. Requests left `reasoning_effort`
unset, preserving default thinking. The shared harness was commit
`8b39ee2e48b37eaed2b335e3f4f76bdd82c08aaf`, with `audit_bench.py` SHA-256
`ee10944f7b1287bbe382708aee70804731731d0bb92ca93754427057bbf2c98b`.

### Throughput

All rates below are medians read from the retained JSON. Decode is
aggregate end-to-end output tok/s. Audit columns are completed
calls/hour. Four-way deep execution remains roughly flat in aggregate
throughput: it supports concurrent agents but does not multiply deep
audit calls/hour.

| Profile | Decode 1/2/4 tok/s | Audit 32k 1/2/4 /h | Audit half 1x /h | Audit deep 1/4 /h |
| -- | --: | --: | --: | --: |
| `qwen3.6-35b-a3b` | 299.53 / 374.85 / 512.57 | 332.13 / 345.91 / 375.67 | 58.75 | 23.33 / 23.16 |
| `qwen3.8-27b` | 67.02 / 119.25 / 151.50 | 62.69 / 64.92 / 65.71 | 14.14 | 6.59 / 6.58 |

| Profile | Prefill 32k/64k/128k tok/s | Measured half/deep input tokens | Near-context input tokens per stream | Near-context wall seconds, 1/4 streams |
| -- | --: | --: | --: | --: |
| `qwen3.6-35b-a3b` | 4,662.81 / 3,334.05 / 2,242.19 | 131,071 / 229,362 | 245,752 | 174.67 / 698.89 |
| `qwen3.8-27b` | 778.06 / 686.47 / 560.87 | 131,075 / 229,366 | 245,748 | 604.55 / 2,422.28 |

Near-context phases request one output token; audit 32k/half request
1,024 and audit deep requests 256. These full-profile results use
cache-neutral evidence prompts. The growing-conversation and replay
profiles were not measured in these earlier trials; no warm conversation
rate is inferred from this table. Cross-runtime comparisons are in the root
[README.md](../README.md#measured-overview).

### Capacity and stability

| Profile | Configured context | Native active slots | Native virtual KV tokens | Conservative managed benchmark KV tokens | Native peak GiB |
| -- | --: | --: | --: | --: | --: |
| `qwen3.6-35b-a3b` | 262,144 | 4 | 4,415,488 | 4,358,144 | 63.24 |
| `qwen3.8-27b` | 262,144 | 4 | 1,474,560 | 1,445,888 | 63.25 |

The virtual pool is sparse and shares the dynamic memory budget with
active and cached state cells. It is not a preallocated GPU pool.
The managed adapter reserves all four active state cells and rounds
remaining KV capacity down to native allocation extents. Both bounds
still admit four full configured contexts. The trial adapter passed
the raw virtual value after separately proving that four full-context
active states fit; the managed bound does not change admitted stream
counts for either measured operating point.

Qwen3.6 completed 69/69 submitted requests; Qwen3.8 completed 63/63.
Neither successful run recorded failed/cancelled requests, capacity
failures, Metal errors, suspensions or engine restarts. Native telemetry
confirmed four-wide decode. State eviction counts were 82 and 69.
Qwen3.8 had one sampled 3.40-second memory-admission wait during its
32K four-stream phase, cleared by the next sample, and 49 KV unmaps.
These are retained-state memory effects, not CPU offload measurements.
Both process groups and ports were verified released after completion.

The dense run used a 7,200-second HTTP request timeout. An earlier
attempt with upstream's 1,800-second default failed with HTTP 504 during
four-way near-context work while the native engine was progressing.
That failed attempt contributes no numbers to the tables. The laptop
power gate paused the successful dense campaign between batches to
recharge; the pause is outside measured request wall times.

### Retained full-run evidence

Base directory on the measured host:
`~/.local/state/auditbench/trials/2026-09-19-splash/`.

Qwen3.6:

```text
qwen3.6-20260919T132648Z/auditbench/20260919T132652.485005+0000_splash_qwen3-6-splash-1-0-64g_full.json
```

Qwen3.8:

```text
qwen3.8-20260919T151231Z/auditbench/20260919T151238.001212+0000_splash_qwen3-8-splash-1-0-64g_full.json
```

Each run directory also retains `status-before.json`,
`status-after.json`, `capacity-plan.json`, `server.log` and
`teardown.json`. Capability evidence belongs in
[CAPABILITIES.md](../CAPABILITIES.md), separate from serving rates.

## Managed integration checks, 2026-09-19

The standalone installation and uv-driven targets were exercised with
both pinned profiles: start, status, Capability Check v1, AuditBench's
decode diagnostic and stop. Both API gates passed all eight checks,
including schema enforcement. Qwen3.8 used API-key authentication.
Both teardowns verified empty process groups and released ports.

The following diagnostics preserve default thinking and use the same
262K context and 64 GiB cap. They have `canonical: false` and
`publishable: false` (`noncanonical_settings`, `repository_dirty`).
They verify the managed transport and batching; they do not replace the
full-run serving results above.

| Profile | Diagnostic decode 1/2/4 aggregate tok/s |
| -- | --: |
| `qwen3.6-35b-a3b` | 304.38 / 372.65 / 520.69 |
| `qwen3.8-27b` | 63.25 / 113.77 / 144.85 |

JSON reports under `~/.local/state/auditbench/`:

```text
20260919T192354.733745+0000_splash_qwen3-6-35b-a3b_decode.json
20260919T192803.813365+0000_splash_qwen3-8-27b_decode.json
```

An earlier Qwen3.6 integration diagnostic disabled thinking explicitly;
its different operating point is retained separately as
`20260919T191913.746450+0000_splash_qwen3-6-35b-a3b_decode.json`.
The official benchmark target preserves the model default.
