# Splash benchmarks

## Apple M5 Max, Splash 1.0, 2026-09-19

Host `tumi-m5-max.local`: MacBook Pro `Mac17,6`, Apple M5 Max, 40 GPU
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

Near-context phases request one output token; audit half/deep request
256. These full-profile results use cache-neutral evidence prompts.
The shared growing-conversation and replay profiles have not yet been
measured for Splash; no warm conversation rate is inferred from this
table. Cross-runtime comparisons are in the root
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
