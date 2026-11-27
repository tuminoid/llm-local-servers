# NVIDIA A100 SXM4 80GB

Measured on a shared server with one A100-SXM4-80GB (sm_80, 81,920 MiB
VRAM), 211 GiB RAM and 30 vCPUs without AVX-512. The 80 GB of VRAM holds a
quantized 35B MoE with room for several concurrent deep sessions, so the
fastest profiles here run more than one stream. sm_80 has no FP8 tensor
cores: FP8 weights run W8A16 through Marlin, so 4-bit weights decode faster.

The tables are rendered from
[nvidia-a100-sxm4-80gb.json](nvidia-a100-sxm4-80gb.json), which
`make results-import` fills from the retained harness JSON; never edit a
table by hand.

## Audit ranking

Canonical [AuditBench v3](https://github.com/tuminoid/llm-audit-bench) `session`
profile at each conf's declared sampling: 16 tool steps from 32k evidence,
report at about 165k. The vLLM rows ran 2026-11-26 on llm-audit-bench 3.0.0
(vLLM 0.34.0, Transformers 5.22.2, serving-default cache pins), except
`mimo-v2.6-9b-awq`'s (2026-11-25, vLLM 0.31.0). The Strata rows (Strata 0.2.21
built for sm_80) ran 2026-11-26. The Ollama rows (isolated Ollama 0.40.16, Flash
Attention, q8 KV) ran 2026-11-15/16 on llm-audit-bench 2.5.0, whose session code
3.0.0 ships unchanged. The FreeToken rows ran 2026-11-27 on FreeToken 0.2.3. The
harness climbs 1, 2, 4, 8 streams within admission and the KV pool while each
rung completes every session and gains 10%; Ollama's slots are the conf's
`OLLAMA_NUM_PARALLEL`, and Strata's are its conf's `STRATA_PARALLEL`.

A ranked row passes Capability Check v3 compatibility and publishes its
optimal operating point: the fastest measured stream count whose sessions
all completed. Complete counts sessions whose report ended on its own and
named at least 7/8 of its findings. vLLM's KV pool is the engine's own;
Ollama's is its allocation, configured context times slots. pp512/tg128 is
the llama-bench-method reference (one stream, greedy, depth ~0), not a
serving result; Ollama and Strata cannot force an exact output length, so it
is unavailable where the model stopped early. The OWASP vuln score is
Capability Check v3's audit aptitude: true-positive minus false-positive
rate on 28 OWASP BenchmarkPython cases (+1 perfect, 0 chance) with its 95%
interval; the intervals span about +-0.3, so rows stay ranked by rate.

<!-- results:audit -->

| Rank | Profile | Runtime | Engine | Tier | Context | Slots | KV pool | Best sessions/h | Other stream counts | Complete | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | pp512 / tg128 | OWASP vuln score [95% CI] | Publishable | Session JSON |
| --: | -- | -- | -- | -- | --: | --: | --: | --: | -- | -- | --: | --: | --: | -- | -- | -- | -- |
| 1 | `ornith1.5-35b-a3b` | FreeToken | FreeToken | MoE | 262,144 | 8 | 2,526,012 | 87.67 @8x | 1x 49.94, 2x 69.05, 4x 79.10 | 1x 2/2, 2x 6/6, 4x 12/12, 8x 24/24 | 4,400 | -- | 121.4 | 5,201 / 161.5 | +0.43 [+0.08, +0.67] | yes | `20261127T022039.640235+0000_freetoken_ornith1-5-35b-a3b_session.json` |
| 2 | `qwen3.6-35b-a3b-awq` | vLLM | vLLM, CUDA | MoE | 262,144 | 8 | 2,768,962 | 60.39 @8x | 1x 40.45, 2x 50.23, 4x 56.46 | 1x 2/2, 2x 6/6, 4x 12/12, 8x 24/24 | 5,090 | 6,278.1 | 115.7 | 4,818 / 160.4 | +0.29 [-0.06, +0.56] | yes | `20261126T011450.881188+0000_vllm-cuda_qwen3-6-35b-a3b-awq_session.json` |
| 3 | `gemma4-26b-a4b-awq` | vLLM | vLLM, CUDA | MoE | 262,144 | 8 | 1,867,958 | 45.74 @4x | 1x 37.48, 2x 44.55 | 1x 2/2, 2x 4/4, 4x 12/12 | 1,662 | 2,246.6 | 65.8 | 8,079 / 176.6 | +0.57 [+0.20, +0.80] | yes | `20261126T020906.470981+0000_vllm-cuda_gemma4-26b-a4b-awq_session.json` |
| 4 | `qwen3.8-flash-next-nvfp4` | Strata | Strata | MoE | 262,144 | 1 | 262,144 | 36.51 @1x | -- | 2/2 | 6,011 | 3,577.3 | 106.8 | unavailable | +0.79 [+0.44, +0.94] | yes | `20261126T102849.790130+0000_strata_qwen3-8-flash-next-nvfp4_session.json` |
| 5 | `qwen3.8-27b` | vLLM | vLLM, CUDA | dense | 262,144 | 8 | 937,042 | 23.48 @4x | 1x 11.61, 2x 17.18 | 1x 2/2, 2x 6/6, 4x 12/12 | 11,225 | 1,873.3 | 50.2 | 2,978 / 75.4 | +0.79 [+0.44, +0.94] | yes | `20261126T024637.568140+0000_vllm-cuda_qwen3-8-27b_session.json` |
| 6 | `inkling-2-mini` | Strata | Strata | MoE | 262,144 | 4 | 1,048,576 | 22.09 @1x | 2x 21.18 | 1x 3/3, 2x 6/6 | 2,150 | 1,395.1 | 37.5 | unavailable | +0.79 [+0.44, +0.94] | yes | `20261126T093907.575568+0000_strata_inkling-2-mini_session.json` |
| 7 | `qwen3.8-27b-512k` | vLLM | vLLM, CUDA | dense | 524,288 | 8 | 765,444 | 19.56 @4x | 1x 10.95, 2x 15.74 | 1x 2/2, 2x 4/4, 4x 12/12 | 8,734 | 1,745.3 | 36.9 | 2,586 / 49.4 | +0.79 [+0.44, +0.94] | yes | `20261126T045503.048019+0000_vllm-cuda_qwen3-8-27b-512k_session.json` |
| 8 | `nemotron-3.5-bolt-74b-a9b-iq2` | Ollama | llama.cpp | hybrid MoE | 262,144 | 1 | 262,144 allocated | 15.53 @1x | -- | 3/3 | 11,157 | 1,185.9 | 119.6 | unavailable | +0.43 [+0.05, +0.70] | yes | `20261115T200425.049712+0000_ollama_nemotron-3-5-bolt-74b-a9b-iq2_session.json` |
| 9 | `flint-40b-a2b-nvfp4` | Ollama | llama.cpp | MoE | 262,144 | 4 | 1,048,576 allocated | 9.94 @1x | 2x 12.14 | 1x 2/2, 2x 5/6 | 8,496 | 918.7 | 40.7 | unavailable | +0.29 [-0.08, +0.58] | yes | `20261116T071203.318342+0000_ollama_flint-40b-a2b-nvfp4_session.json` |
| 10 | `nanbeige4.3-33b-w4a16` | vLLM | vLLM, CUDA | dense | 262,144 | 8 | 282,112 | 8.02 @1x | -- | 2/2 | 8,204 | 935.6 | 28.1 | 2,720 / 72.0 | +0.43 [+0.06, +0.69] | yes | `20261126T060737.628810+0000_vllm-cuda_nanbeige4-3-33b-w4a16_session.json` |
| -- | `mimo-v2.6-9b-awq` | vLLM | vLLM, CUDA | dense | 262,144 | 8 | 2,229,526 | -- | 1x 57.08 | 0/2 | 3,670 | 5,152.7 | 109.4 | 8,201 / 175.6 | not scored | no (incomplete_sessions) | `20261125T010833.773202+0000_vllm-cuda_mimo-v2-6-9b-awq_session.json` |

<!-- /results:audit -->

- `ornith1.5-35b-a3b` on FreeToken serves the publisher's Q4_K_M GGUF with
  every expert in VRAM; its prefix cache reuses each resent turn, including
  the previous reply.
  FreeToken reports no cached-token count on a call with no cache hit, so
  its rows carry no session prefill rate
  ([freetoken/BENCHMARKS.md](../../freetoken/BENCHMARKS.md)).
- `qwen3.6-35b-a3b-awq` completes every session at each of 1, 2, 4 and 8
  streams.
- `gemma4-26b-a4b-awq` and `qwen3.8-27b-512k` enforce the schema with
  grammar whitespace forbidden in their confs.
- `qwen3.8-27b` serves W4A16 (`dbirks/Qwen3.8-27B-W4A16-AutoRound`), which
  halves the weight reads of the FP8 build; `qwen3.8-27b-512k` keeps FP8 for
  its larger window and runs 83% of its rate at four streams.
- `qwen3.8-flash-next-nvfp4` on Strata runs one slot at 262,144: int8 KV
  streamed from pinned RAM past a 32,768-token window, the n-gram table in
  RAM, MTP drafts four deep, every routed expert in VRAM.
- `inkling-2-mini` runs on Strata's Inkling engine with all 3,072 experts
  in VRAM and its DSpark drafter; two streams gained nothing over one.
- `nemotron-3.5-bolt-74b-a9b-iq2` (NVIDIA's 24 GB IQ2_XXS) runs on Ollama's
  `nemotron_h_moe` runner, which serves one slot whatever the conf asks, so
  1x is its only operating point.
- `flint-40b-a2b-nvfp4` passes with the lowest audit aptitude here (+0.29,
  interval including zero). Its ladder stopped at 2x on an incomplete
  session, so 1x is its operating point.
- `mimo-v2.6-9b-awq` (neither session finished its report's findings) fails
  Capability Check v3 compatibility, so its rate cannot rank it.

## Interactive profiles

These profiles do not fit the card entirely and serve one stream; they are
not ranked for audits.

<!-- results:interactive -->

| Profile | Runtime | Engine | Tier | Context | Slots | KV pool | Sessions/h by streams | Complete | Out tok/session 1x | Prefill tok/s 1x | Report decode 1x | pp512 / tg128 | Publishable | Session JSON |
| -- | -- | -- | -- | --: | --: | --: | -- | -- | --: | --: | --: | -- | -- | -- |
| `glm5.3-flash-q2kxl` | FreeToken | FreeToken | MoE | 262,144 | 1 | 262,400 | 1x 8.83 | 2/2 | 6,814 | -- | 38.1 | 125 / 40.1 | yes | `20261127T104905.324636+0000_freetoken_glm5-3-flash-q2kxl_session.json` |

<!-- /results:interactive -->

- `glm5.3-flash-q2kxl` on FreeToken keeps its experts in pinned host RAM
  behind a GPU expert cache; the near-context probe prefilled a cold
  245,760-token prompt at 1,264 tok/s.

## Capability Check

Capability Check v3 (llm-audit-bench 3.0.0): the vLLM rows run 2026-11-25/26
on vLLM 0.34.0 with Transformers 5.22.2, the Strata rows 2026-11-26 on
Strata 0.2.21, the Ollama rows 2026-11-19/20 on Ollama 0.40.16, the
FreeToken rows 2026-11-27 on FreeToken 0.2.3.
The protocol and the column mapping are in llm-audit-bench
`docs/CAPABILITY.md`, the campaign runbook in
[CAPABILITIES.md](../../CAPABILITIES.md). Campaign marks the profiles this
hardware's campaigns run. Model identity shows the first 12 characters of
the digest or revision; every row's live identity matched the one pinned in
its model config. An audit row's score is in the audit ranking.

<!-- results:capability -->

| Runtime | Profile | Campaign | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Clean samples | Compatibility | Audit aptitude | Model identity | Artifact |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| FreeToken | `ornith1.5-35b-a3b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | unsupported (refused) | 33 of 36 (92%); fitness 8 of 8 | passed | sound 8 of 8 | `12393612fd4f` | `20261127T021855.172418+0000_freetoken_ornith1-5-35b-a3b.json` |
| Ollama | `flint-40b-a2b-nvfp4` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `9543f736310d` | `20261119T184514.296753+0000_ollama_flint-40b-a2b-nvfp4.json` |
| Ollama | `nemotron-3.5-bolt-74b-a9b-iq2` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 34 of 36 (94%); fitness 8 of 8 | passed | sound 8 of 8 | `d6d3deeca271` | `20261119T201109.714683+0000_ollama_nemotron-3-5-bolt-74b-a9b-iq2.json` |
| Strata | `inkling-2-mini` | yes | passed | passed | untested | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `800c946d7b9c` | `20261126T081237.149195+0000_strata_inkling-2-mini.json` |
| Strata | `qwen3.8-flash-next-nvfp4` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `640a1db97446` | `20261126T093740.926300+0000_strata_qwen3-8-flash-next-nvfp4.json` |
| vLLM | `gemma4-26b-a4b-awq` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `0ef577a57100` | `20261125T221013.298634+0000_vllm-cuda_gemma4-26b-a4b-awq.json` |
| vLLM | `nanbeige4.3-33b-w4a16` | yes | passed | passed | supported | supported | supported | supported | supported | valid | whitespace_runaway (broken) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `1c1666af6d96` | `20261126T011317.419806+0000_vllm-cuda_nanbeige4-3-33b-w4a16.json` |
| vLLM | `qwen3.6-35b-a3b-awq` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `119886a10723` | `20261125T215648.514991+0000_vllm-cuda_qwen3-6-35b-a3b-awq.json` |
| vLLM | `qwen3.8-27b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `1f05c441c4e6` | `20261125T224542.283757+0000_vllm-cuda_qwen3-8-27b.json` |
| vLLM | `qwen3.8-27b-512k` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `017b9c7af6b5` | `20261125T235732.836908+0000_vllm-cuda_qwen3-8-27b-512k.json` |
| vLLM | `mimo-v2.6-9b-awq` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 6 of 8 (75%); fitness 6 of 8 | failed (fitness_clean, clean_rate) | not scored | `09a55d0912c0` | `20261126T000929.109418+0000_vllm-cuda_mimo-v2-6-9b-awq.json` |
| FreeToken | `glm5.3-flash-q2kxl` | yes | passed | passed | untested | supported | supported | supported | supported | valid | unsupported (refused) | 34 of 36 (94%); fitness 8 of 8 | passed | +0.79 [+0.44, +0.94]; sound 8 of 8 | `a38483c8cd5d` | `20261127T104314.518530+0000_freetoken_glm5-3-flash-q2kxl.json` |

<!-- /results:capability -->

- `mimo-v2.6-9b-awq` fails fitness, 6 of 8 clean (a loop and a runaway).
