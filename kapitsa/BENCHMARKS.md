# Kapitsa benchmarks

## Apple M5 Max

Results on this hardware are on its page,
[Apple M5 Max, 128 GB](../docs/hardware/apple-m5-max-128gb.md).

### Clover decode modes

Exploratory runs of 2026-10-28 on a source build of the same release
(`b46d9e5`), two slots, `AUDIT_BENCH_STREAMS=1,2` (non-canonical),
sessions/h:

| Mode | Sessions/h 1x / 2x |
| -- | -- |
| self-speculative, threshold, the checkpoint's ramps | 24.88 / 24.45 |
| 35B DFlash2 drafter (`NI_CLOVER_DECODE=dflash`) | 25.63 (2/3 complete) / 24.73 |

Exact acceptance (`NI_CLOVER_ACCEPT=exact`) decodes the causal pathway
greedily with presence 0.9 counted on every reply token, reasoning
included, and JSON answers lose the array's brackets. The drafter mode
decodes the same pathway at the request's sampling without the model's
`</think>` ramp, and long agent turns never close their thinking. Retest
when a release changes Clover's decode modes.
