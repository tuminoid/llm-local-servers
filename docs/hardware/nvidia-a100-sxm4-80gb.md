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

Canonical [AuditBench v3](https://github.com/tuminoid/llm-audit-bench)
`session` profile at each conf's declared sampling: 16 tool steps from 32k
evidence, report at about 165k. The vLLM rows ran 2026-11-24/25 on
llm-audit-bench 3.0.0 from fleet commit `8ab4e09` (vLLM 0.31.0,
Transformers 5.15.1, serving-default cache pins). The Ollama rows (isolated
Ollama 0.40.16, Flash Attention, q8 KV) and the Strata rows (Strata 0.2.13
built for sm_80) ran 2026-11-15/16 from the clean trial commit `54822f2` on
llm-audit-bench 2.5.0, whose session code 3.0.0 ships unchanged. The harness
climbs 1, 2, 4, 8 streams within admission and the KV pool while each rung
completes every session and gains 10%; Ollama's slots are the conf's
`OLLAMA_NUM_PARALLEL`, and Strata serves one.

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
| 1 | `qwen3.6-35b-a3b-awq` | vLLM | vLLM, CUDA | MoE | 262,144 | 8 | 2,797,230 | 55.22 @4x | 1x 38.13, 2x 50.57 | 1x 2/2, 2x 6/6, 4x 12/12 | 5,502 | 6,293.3 | 111.2 | 4,430 / 153.7 | +0.50 [+0.15, +0.73] | yes | `20261124T204905.089471+0000_vllm-cuda_qwen3-6-35b-a3b-awq_session.json` |
| 2 | `gemma4-26b-a4b-awq` | vLLM | vLLM, CUDA | MoE | 262,144 | 8 | 1,909,362 | 41.59 @2x | 1x 36.59, 4x 45.01 | 1x 2/2, 2x 4/4, 4x 11/12 | 1,484 | 2,117.2 | 63.7 | 8,212 / 178.4 | +0.71 [+0.36, +0.89] | yes | `20261124T212102.018862+0000_vllm-cuda_gemma4-26b-a4b-awq_session.json` |
| 3 | `qwen3.8-flash-next-nvfp4` | Strata | Strata | MoE | 262,144 | 1 | 262,144 | 27.66 @1x | -- | 3/3 | 6,188 | 2,136.0 | 110.2 | unavailable | +0.86 [+0.52, +0.98] | yes | `20261115T164004.814930+0000_strata_qwen3-8-flash-next-nvfp4_session.json` |
| 4 | `qwen3.8-27b-512k` | vLLM | vLLM, CUDA | dense | 524,288 | 8 | 779,829 | 20.52 @4x | 1x 9.38, 2x 16.00 | 1x 2/2, 2x 6/6, 4x 8/8 | 10,844 | 1,740.2 | 36.7 | 2,606 / 49.3 | +0.64 [+0.28, +0.85] | yes | `20261124T230336.466050+0000_vllm-cuda_qwen3-8-27b-512k_session.json` |
| 5 | `qwen3.8-27b` | vLLM | vLLM, CUDA | dense | 262,144 | 8 | 954,019 | 20.12 @4x | 1x 12.99, 2x 17.85 | 1x 2/2, 2x 6/6, 4x 8/8 | 9,482 | 1,851.5 | 50.0 | 2,964 / 75.4 | +0.71 [+0.35, +0.90] | yes | `20261124T220035.364825+0000_vllm-cuda_qwen3-8-27b_session.json` |
| 6 | `nemotron-3.5-bolt-74b-a9b-iq2` | Ollama | llama.cpp | hybrid MoE | 262,144 | 1 | 262,144 allocated | 15.53 @1x | -- | 3/3 | 11,157 | 1,185.9 | 119.6 | unavailable | +0.43 [+0.05, +0.70] | yes | `20261115T200425.049712+0000_ollama_nemotron-3-5-bolt-74b-a9b-iq2_session.json` |
| 7 | `qwen3.8-27b-dflash2` | vLLM | vLLM, CUDA | dense | 262,144 | 8 | 522,956 | 12.63 @2x | 1x 8.86 | 1x 3/3, 2x 6/6 | 7,509 | 1,759.3 | 22.0 | 2,599 / 108.6 | +0.64 [+0.28, +0.85] | yes | `20261125T001233.153991+0000_vllm-cuda_qwen3-8-27b-dflash2_session.json` |
| 8 | `flint-40b-a2b-nvfp4` | Ollama | llama.cpp | MoE | 262,144 | 4 | 1,048,576 allocated | 9.94 @1x | 2x 12.14 | 1x 2/2, 2x 5/6 | 8,496 | 918.7 | 40.7 | unavailable | +0.29 [-0.08, +0.58] | yes | `20261116T071203.318342+0000_ollama_flint-40b-a2b-nvfp4_session.json` |
| 9 | `deepseek-v4.1-flash-coder-iq2xxs` | Strata | Strata DeepSeek | MoE | 1,048,576 | 1 | 1,048,576 | 9.77 @1x | -- | 3/3 | 8,571 | 827.5 | 50.3 | unavailable | +0.86 [+0.52, +0.98] | yes | `20261115T174556.949264+0000_strata_deepseek-v4-1-flash-coder-iq2xxs_session.json` |
| -- | `ornith1.5-35b-a3b` | Ollama | llama.cpp | MoE | 262,144 | 1 | 262,144 allocated | 32.21 @1x | -- | 2/2 | 3,968 | 3,051.4 | 59.9 | unavailable | not scored | yes | `20261115T194107.762686+0000_ollama_ornith1-5-35b-a3b_session.json` |
| -- | `nanbeige4.3-33b-w4a16` | vLLM | vLLM, CUDA | dense | 262,144 | 8 | 284,704 | 7.59 @1x | -- | 2/2 | 10,136 | 930.4 | 27.9 | 2,917 / 71.3 | not scored | yes | `20261125T011916.186105+0000_vllm-cuda_nanbeige4-3-33b-w4a16_session.json` |
| -- | `deepseek-v4.1-flash-q2` | Strata | Strata DeepSeek | MoE | -- | -- | -- | no session | -- | -- | -- | -- | -- | -- | +0.86 [+0.52, +0.98] | -- | -- |
| -- | `mimo-v2.6-9b-awq` | vLLM | vLLM, CUDA | dense | 262,144 | 8 | 2,229,526 | -- | 1x 57.08 | 0/2 | 3,670 | 5,152.7 | 109.4 | 8,201 / 175.6 | not scored | no (incomplete_sessions) | `20261125T010833.773202+0000_vllm-cuda_mimo-v2-6-9b-awq_session.json` |

<!-- /results:audit -->

- `qwen3.6-35b-a3b-awq` is the fastest profile that passes: every session
  complete, and the ladder stopped at four streams, where the gain fell
  under 10%.
- `gemma4-26b-a4b-awq` publishes two streams: one 4x session left its report
  incomplete. It and `qwen3.8-27b-512k` enforce the schema with grammar
  whitespace forbidden in their confs.
- `qwen3.8-27b` serves W4A16 (`dbirks/Qwen3.8-27B-W4A16-AutoRound`), which
  halves the weight reads of the FP8 build; `qwen3.8-27b-512k` keeps FP8 for
  its larger window and ties it at four streams.
- `qwen3.8-flash-next-nvfp4` on Strata runs one slot at 262,144: int8 KV
  streamed from pinned RAM past a 32,768-token window, the n-gram table in
  RAM, MTP drafts four deep, every routed expert in VRAM. Mid-session decode
  ran 116-137 tok/s.
- `deepseek-v4.1-flash-coder-iq2xxs` runs on Strata's DeepSeek engine at
  1,048,576 with DSpark at a 0.65 floor and every routed expert in VRAM; its
  983,045-token near-context prompt read at 888 tok/s.
- `deepseek-v4.1-flash-q2` passes but has no session: 8,666 of its 15,360
  experts fit on the GPU at 1,048,576, and `strata-bench` refuses a set with
  experts off the GPU.
- `nemotron-3.5-bolt-74b-a9b-iq2` (NVIDIA's 24 GB IQ2_XXS) runs on Ollama's
  `nemotron_h_moe` runner, which serves one slot whatever the conf asks, so
  1x is its only operating point.
- `flint-40b-a2b-nvfp4` passes with the lowest audit aptitude here (+0.29,
  interval including zero). Its ladder stopped at 2x on an incomplete
  session, so 1x is its operating point.
- `qwen3.8-27b-dflash2` loses to plain `qwen3.8-27b` at the declared
  sampling: its target is FP8, and the drafter's sampled acceptance of about
  2.3 tokens does not make up the difference. Greedy, it leads at 8k.
- `mimo-v2.6-9b-awq` (neither session finished its report's findings),
  `nanbeige4.3-33b-w4a16` and Ollama `ornith1.5-35b-a3b` fail Capability
  Check v3 compatibility, so their rates cannot rank them.

## Capability Check

Capability Check v3 (llm-audit-bench 3.0.0, `365510b`), run 2026-11-19/20
from fleet commit `a21fd8a` on vLLM 0.31.0 with Transformers 5.15.1, Ollama
0.40.16 and Strata 0.2.13. The protocol and the column mapping are in
llm-audit-bench `docs/CAPABILITY.md`, the campaign runbook in
[CAPABILITIES.md](../../CAPABILITIES.md). Campaign marks the profiles this
hardware's campaigns run. Model identity shows the first 12 characters of
the digest or revision; every row's live identity matched the one pinned in
its model config. An audit row's score is in the audit ranking.

<!-- results:capability -->

| Runtime | Profile | Campaign | Identity | Reasoning | Thinking off | Tool call | Streaming tool call | Tool loop | JSON | Unaided document | Schema enforced | Clean samples | Compatibility | Audit aptitude | Model identity | Artifact |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| Ollama | `flint-40b-a2b-nvfp4` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `9543f736310d` | `20261119T184514.296753+0000_ollama_flint-40b-a2b-nvfp4.json` |
| Ollama | `nemotron-3.5-bolt-74b-a9b-iq2` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 34 of 36 (94%); fitness 8 of 8 | passed | sound 8 of 8 | `d6d3deeca271` | `20261119T201109.714683+0000_ollama_nemotron-3-5-bolt-74b-a9b-iq2.json` |
| Strata | `deepseek-v4.1-flash-coder-iq2xxs` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 35 of 36 (97%); fitness 8 of 8 | passed | sound 7 of 8 | `0b1d5da5734d` | `20261120T015850.589411+0000_strata_deepseek-v4-1-flash-coder-iq2xxs.json` |
| Strata | `qwen3.8-flash-next-nvfp4` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `640a1db97446` | `20261119T220514.667979+0000_strata_qwen3-8-flash-next-nvfp4.json` |
| vLLM | `gemma4-26b-a4b-awq` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `0ef577a57100` | `20261119T145100.047835+0000_vllm-cuda_gemma4-26b-a4b-awq.json` |
| vLLM | `qwen3.6-35b-a3b-awq` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `119886a10723` | `20261119T142313.656730+0000_vllm-cuda_qwen3-6-35b-a3b-awq.json` |
| vLLM | `qwen3.8-27b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 34 of 36 (94%); fitness 7 of 8 | passed | sound 7 of 7 | `1f05c441c4e6` | `20261119T153701.415810+0000_vllm-cuda_qwen3-8-27b.json` |
| vLLM | `qwen3.8-27b-512k` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `017b9c7af6b5` | `20261119T164755.866465+0000_vllm-cuda_qwen3-8-27b-512k.json` |
| vLLM | `qwen3.8-27b-dflash2` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `017b9c7af6b5` | `20261119T160828.532762+0000_vllm-cuda_qwen3-8-27b-dflash2.json` |
| Ollama | `ornith1.5-35b-a3b` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 19 of 23 (83%); fitness 8 of 8 | failed (clean_rate) | not scored | `9f3b89b25219` | `20261119T175309.862604+0000_ollama_ornith1-5-35b-a3b.json` |
| Strata | `deepseek-v4.1-flash-q2` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 36 of 36 (100%); fitness 8 of 8 | passed | sound 8 of 8 | `cb02422c900d` | `20261120T062422.397959+0000_strata_deepseek-v4-1-flash-q2.json` |
| vLLM | `mimo-v2.6-9b-awq` | yes | passed | passed | supported | supported | supported | supported | supported | valid | enforced (supported) | 5 of 8 (62%); fitness 5 of 8 | failed (fitness_clean, clean_rate) | not scored | `09a55d0912c0` | `20261119T143611.513989+0000_vllm-cuda_mimo-v2-6-9b-awq.json` |
| vLLM | `nanbeige4.3-33b-w4a16` | yes | passed | passed | supported | supported | supported | supported | supported | valid | whitespace_runaway (broken) | 6 of 8 (75%); fitness 6 of 8 | failed (fitness_clean, clean_rate) | not scored | `1c1666af6d96` | `20261119T205316.035551+0000_vllm-cuda_nanbeige4-3-33b-w4a16.json` |

<!-- /results:capability -->

- The three Strata profiles score highest, +0.86 each. Both
  DeepSeek-V4.1-Flash sets reasoned on 34 of 36 samples; the Coder leaked
  once.
- `mimo-v2.6-9b-awq` fails fitness, 5 of 8 clean (three runaways).
- `nanbeige4.3-33b-w4a16` fails fitness, 6 of 8 clean: one workflow turn
  emitted tool arguments that are not JSON and one ran out of turn budget.
  Its selection answers run 33k to 64k tokens.
- Ollama `ornith1.5-35b-a3b` fails on clean rate, 19 of 23: four
  vulnerability answers wrapped the JSON array in analysis prose. The same
  model passes on Apple M5 Max Splash, so the failure belongs to this engine
  and model combination.
- `qwen3.8-27b-dflash2` matches the plain profiles check for check, so the
  drafter changes no response semantics.
