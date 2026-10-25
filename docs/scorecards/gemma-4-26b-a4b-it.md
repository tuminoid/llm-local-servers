# gemma-4-26B-A4B-it published benchmarks

Model:
[google/gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it) at
`4d7ae4984b7d`, created 2026-03-11. Fetched 2026-10-25 by the model-benchmarks
skill. Published claims only, quoted as written; nothing here was measured by
this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 37.22 | Terminal-Bench 2.1 | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16/blob/e09a4cedb1787db1760375ee5539f222cae0c672/README.md) |
| Terminal-Bench 2.1 | 37.22 | Terminal-Bench 2.1 | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16/blob/a9904d24bcc1d289a1950fa9d2b978c47cf903b9/README.md) |
| SWE-bench Verified | 25.80 | SWE-Bench Verified (OpenCode) | competitor card | LiquidAI | - | [LiquidAI/LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/3fcfdbfa1a1b6d8166846a6323e69f1e1254440d/README.md) |
| SWE-bench Verified | 17.4 | SWE-bench Verified | competitor card | Qwen | - | [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) |
| SWE-bench Verified | 57.40 | SWE-bench Verified | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16/blob/a9904d24bcc1d289a1950fa9d2b978c47cf903b9/README.md) |
| SWE-bench Pro | 13.8 | SWE-bench Pro | competitor card | Qwen | - | [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) |
| SWE-bench Multilingual | 17.3 | SWE-bench Multilingual | competitor card | Qwen | - | [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) |
| SWE-bench Multilingual | 43.40 | SWE-bench Multilingual | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16/blob/a9904d24bcc1d289a1950fa9d2b978c47cf903b9/README.md) |
| LiveCodeBench v6 | 77.1% | LiveCodeBench v6 | own card | google | - | [google/gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it/blob/4d7ae4984b7db7de8f8457170b3f1a419ee76d52/README.md) |
| LiveCodeBench v6 | 77.1% | LiveCodeBench v6 | vendor card | google | - | [google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it/blob/842da3794eaa0b77d5f08bae87a17459d91ff475/README.md) |
| LiveCodeBench v6 | 77.1 | LiveCodeBench v6 | competitor card | Qwen | - | [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) |
| BFCL v4 | 57.09 | BFCLv4 | competitor card | LiquidAI | - | [LiquidAI/LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/3fcfdbfa1a1b6d8166846a6323e69f1e1254440d/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| NL2Repo | 11.6 | NL2Repo | competitor card | Qwen | - | [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- SWE-bench Verified: LiquidAI 25.80 (SWE-Bench Verified (OpenCode)); Qwen 17.4
  (SWE-bench Verified); nvidia 57.40 (SWE-bench Verified)
- SWE-bench Multilingual: Qwen 17.3 (SWE-bench Multilingual); nvidia 43.40
  (SWE-bench Multilingual)

## Not found

- Easy: Aider Polyglot, Toolathlon-Verified
- Hard: Terminal-Bench 4.0, DeepSWE, SWE-Marathon, ProgramBench, FrontierSWE,
  SWE-Atlas-QnA, Agents' Last Exam
- Vuln audit: CyberGym-E2E, CyberGym, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
