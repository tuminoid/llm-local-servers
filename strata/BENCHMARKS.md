# Strata benchmarks

## A100-SXM4-80GB

Results on this hardware are on its page,
[NVIDIA A100 SXM4 80GB](../docs/hardware/nvidia-a100-sxm4-80gb.md).

## Pack and setting comparison: A100-SXM4-80GB (exploratory)

Strata 0.2.10 (`ffa80d73`) built from source for sm_80 by its own setup
(CUDA 13.2), 2026-11-04, on the A100-SXM4-80GB host (211 GiB RAM, 30 vCPUs
without AVX-512). Context 262,144, int8 KV streamed from RAM past a
32,768-token window, the n-gram table in RAM, MTP drafts four deep. The
harness, llm-audit-bench 2.5.0, ran directly against the server with the
canonical `session` profile at the checkpoint's sampling (temperature 1.0,
top_p 0.95, top_k 20). These runs are not publishable: no fleet adapter
checked identity.

Every pack kept all 24,576 routed experts in VRAM:

| Pack | Slots | Sessions/h 1x | 2x | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | 245,760-token prompt |
| -- | --: | --: | --: | --: | --: | --: | --: |
| ISTA-DASLab GSQ-RCO Q2_0 | 8 | 39.89 | 31.17 | 4,196 | 2,930 | 117.8 | 3,545 tok/s |
| ISTA-DASLab GSQ-RCO IQ3_S | 8 | 31.17 | 29.02 | 6,274 | 2,741 | 112.3 | 3,322 tok/s |
| NVFP4, Strata's GPTQ pack | 1 | 29.50 | -- | 5,528 | 2,221 | 111.7 | 2,790 tok/s |
| NVFP4, NVIDIA's checkpoint | 1 | 28.71 | -- | 4,959 | 2,201 | 105.8 | 2,821 tok/s |
| NVFP4, NVIDIA's FP4-QAD checkpoint | 1 | 27.44 | -- | 5,725 | 2,123 | 105.8 | 2,784 tok/s |

Q2_0 settings, each changed alone:

| Setting | Sessions/h 1x | 2x |
| -- | --: | --: |
| Setup's defaults | 39.89 | 31.17 |
| `--batch-mtp` | 36.40 | 33.77 |
| `STRATA_PF_FUSED_NT=256 STRATA_PF_BATCH=256 STRATA_GDN_TC=1` | 36.30 | 32.25 |
| `--batch-mtp`, `STRATA_BATCH_DECODE_SHARE=1.5` | 36.97 | 31.35 |

- One stream is the optimal operating point everywhere. At two, the engine
  reads one admission's prompt at a time while the other slot decodes
  between its chunks, and per-stream decode mid-session falls to 11-29
  tok/s. Batch MTP drafts recover part of it; a larger decode share costs
  prompt speed (1,648 tok/s) for no rate.
- The A100 runs NVFP4 as W4A8 on int8 MMQ, with no FP4 tensor cores: prompt
  reading falls to about 2,200 tok/s against 2,750-2,930 for the GSQ-RCO
  packs, while decode stays close. The three NVFP4 packs differ by less
  than the sessions' length variance (4,960-5,730 output tokens).
- Strata's own quality measurement (4,995 teacher-forced positions against
  Unsloth's Q8_0, `docs/NVFP4.md` and `docs/QUANTS.md` at the pin) puts the
  GPTQ pack at 91.8-92.1% the same top token and mean KL 0.069, IQ3_S at
  87.7% and 0.144, Q2_0 at 80.6% and 0.315. It publishes none for NVIDIA's
  checkpoint. The fleet profile serves the GPTQ pack.
- A Q2_0 smoke request decoded 165.8 tok/s alone (MTP accepted 263 of 296
  drafts).

## DeepSeek-V4.1-Flash sets and context: A100-SXM4-80GB (exploratory)

Strata 0.2.10 (`ffa80d73`), `strata-dsv41` built for sm_80 with the options
`strata-install` now uses, the packs by Strata's own setup, 2026-11-05. One
slot, DSpark auto at a 0.65 floor, sampling temperature 1.0, top_p 1.0,
min_p 0. The harness, llm-audit-bench 2.5.0, ran directly against the
server, so no row is publishable. The 262,144 rows are the canonical
`session` profile; the 524,288 and 1,048,576 rows are the near-context probe
plus one session of `AUDIT_BENCH_CONV_MAX_STEPS=200`, which the harness cuts
to the 50 and 104 steps that fit 7/8 of the context.

| Set | Context | Experts on the GPU | Sessions/h 1x | Steps | Prefill tok/s | Turn decode first/mid/last | Report decode | Near-context prompt |
| -- | --: | -- | --: | --: | --: | -- | --: | -- |
| Coder | 262,144 | 8,064 of 8,064 | 11.21 | 16 | 802.5 | 54.0/84.4/76.5 | 51.4 | 245,760 tok, 189 s |
| Coder | 524,288 | 8,064 of 8,064 | 4.81 | 50 | 717.9 | 60.8/80.0/74.6 | 60.5 | 491,520 tok, 428 s |
| Coder | 1,048,576 | 8,064 of 8,064 | 1.98 | 104 | 589.1 | 50.0/75.4/54.6 | 54.0 | 983,040 tok, 1,101 s |
| IQ2_XXS (2.00 bpw) | 262,144 | 8,768 of 15,360 | 8.37 | 16 | 670.7 | 31.4/34.1/34.2 | 29.2 | 245,760 tok, 210 s |
| IQ2_XXS (2.00 bpw) | 524,288 | 8,734 of 15,360 | 3.47 | 50 | 598.6 | 29.2/33.8/31.4 | 27.5 | 491,520 tok, 471 s |
| IQ2_XXS (2.00 bpw) | 1,048,576 | 8,666 of 15,360 | 1.64 | 104 | 511.1 | 28.2/32.6/28.4 | 26.0 | 983,040 tok, 1,189 s |

- Every session completed. The attention cache takes 0.24 GB at 262K,
  0.49 at 512K and 0.97 at 1M: the Coder keeps every expert on the card at
  all three, and the IQ2_XXS set moves about a hundred more to the CPU lane
  at 1M. Its CPU experts (56.7-57.6 GB) are copied into RAM at load.
- In both sets two of four workflow samples answered the audit's opening
  turn with a 46-token tool call and no thinking
  (`no_reasoning 2`). The template opens the thinking block and asks for
  reasoning before any tool call at effort 75 of 100; the model scales its
  thinking to the step. A replay of that opening turn on the Coder left 4 of
  10 thinks empty at the default and 2 of 10 at `reasoning_effort` max, the
  non-empty ones 30-377 characters, so effort does not fix it. Strata's
  config caps `reasoning_effort` at high.
- Against ds4 on the M5 (`deepseek-v4.1-flash-q2`, the same 1017 checkpoint,
  SSD streaming, mid-session decode 14.7 tok/s, report 14.2, prefill 629),
  the Coder decodes 3.6-5.7x faster at 262K and the IQ2_XXS set 2.1-2.3x;
  prefill gains 1.1-1.3x.
