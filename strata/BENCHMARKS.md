# Strata benchmarks

## AuditBench v2: A100-SXM4-80GB

Strata 0.2.10 (`ffa80d73`) built by `strata-install` for sm_80 against CUDA
13.2, one slot, context 262,144, int8 KV streamed from pinned RAM past a
32,768-token window and the n-gram table in RAM (both derived from the
host's 211 GiB), MTP drafts four deep, every routed expert in VRAM.
Canonical AuditBench v2 `session` profile at the conf's declared sampling,
llm-audit-bench 2.5.0, from the clean fleet commit `9f94bad`, 2026-11-04.
One slot admits one stream, so the ladder measured 1x. Sessions/h is the
median over 3 samples; complete counts sessions whose report ended on its
own and named at least 7/8 of its findings. JSON files are under
`~/.local/state/auditbench/` on the host.

| Runtime and profile | Context | Slots | KV pool | Sessions/h by streams | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | Complete | pp512 / tg128 | Capability v2 | Publishable | JSON |
| -- | --: | --: | --: | -- | --: | --: | --: | -- | -- | -- | -- | -- |
| Strata `qwen3.8-flash-next-nvfp4` | 262,144 | 1 | 262,144 | 1x 28.76 | 5,480 | 2,294.5 | 106.8 | 3/3 | unavailable | pass | yes | `20261104T174104.076114+0000_strata_qwen3-8-flash-next-nvfp4_session.json` |

- Capability Check v2 passes with audit fitness 11 of 12 (selection
  invented 1), `json_schema` enforced and a valid unaided document:
  `20261104T173911.625858+0000_strata_qwen3-8-flash-next-nvfp4.json`, the
  same commit. The trial runs of the same pack passed 12 of 12.
- Mid-session decode ran 112-133 tok/s; the near-context phase
  (245,760-token prompt) read 2,796 tok/s.
- Strata ends a response at EOS rather than at `max_tokens`, so the
  reference measurement is unavailable; it is a diagnostic only.

## Pack and setting comparison: A100-SXM4-80GB (exploratory)

Strata 0.2.10 (`ffa80d73`) built from source for sm_80 by its own setup
(CUDA 13.2), 2026-11-04, on the A100-SXM4-80GB host (211 GiB RAM, 30 vCPUs
without AVX-512). Context 262,144, int8 KV streamed from RAM past a
32,768-token window, the n-gram table in RAM, MTP drafts four deep. The
harness, llm-audit-bench 2.5.0, ran directly against the server with the
canonical `session` profile at the checkpoint's sampling (temperature 1.0,
top_p 0.95, top_k 20). These runs are not publishable: no fleet adapter
checked identity. Evidence is under
`~/.local/state/auditbench/trials/2026-11-04-strata-a100/`.

Every pack kept all 24,576 routed experts in VRAM and passed Capability
Check v2 with audit fitness 12 of 12 and `json_schema` enforced:

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
