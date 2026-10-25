# NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 published benchmarks

Model:
[nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16)
at `a9904d24bcc1`, created 2026-08-01. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 24.58 | Terminal-Bench 2.1 | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16/blob/a9904d24bcc1d289a1950fa9d2b978c47cf903b9/README.md) |
| Terminal-Bench 2.1 | 23.46 | Terminal-Bench 2.1 | vendor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16/blob/e09a4cedb1787db1760375ee5539f222cae0c672/README.md) |
| SWE-bench Verified | 51.56 | SWE-bench Verified | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16/blob/a9904d24bcc1d289a1950fa9d2b978c47cf903b9/README.md) |
| SWE-bench Verified | 53.40 | SWE-Bench Verified (OpenCode) | competitor card | LiquidAI | - | [LiquidAI/LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/3fcfdbfa1a1b6d8166846a6323e69f1e1254440d/README.md) |
| SWE-bench Multilingual | 39.33 | SWE-bench Multilingual | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16/blob/a9904d24bcc1d289a1950fa9d2b978c47cf903b9/README.md) |
| BFCL v4 | 53.78 | BFCLv4 | competitor card | LiquidAI | - | [LiquidAI/LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/3fcfdbfa1a1b6d8166846a6323e69f1e1254440d/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| ProgramBench | 0.00% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/programbench) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Vals CyberBench | 29.46% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/cyber) |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- SWE-bench Verified: nvidia 51.56 (SWE-bench Verified); LiquidAI 53.40
  (SWE-Bench Verified (OpenCode))
- Terminal-Bench 2.1: nvidia 24.58 (Terminal-Bench 2.1); nvidia 23.46
  (Terminal-Bench 2.1)

## Not found

- Easy: SWE-bench Pro, LiveCodeBench v6, Aider Polyglot, Toolathlon-Verified
- Hard: Terminal-Bench 4.0, DeepSWE, SWE-Marathon, FrontierSWE, NL2Repo,
  SWE-Atlas-QnA, Agents' Last Exam
- Vuln audit: CyberGym-E2E, CyberGym, SEC-bench Pro, SEC-bench, ExploitBench,
  ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
