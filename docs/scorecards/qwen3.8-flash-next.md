# Qwen3.8-Flash-Next published benchmarks

Model: [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
at `de4b8e4d43b9`, created 2026-08-24. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 85.80 | Terminal-Bench 2.1 | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| Terminal-Bench 2.1 | 83.400 | TerminalBench 2.1 | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Verified | 78.7 | SWE-bench Verified | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Verified | 82.800 | SWE-bench Verified (non-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Pro | 62.5 | Agentic coding SWE-bench Pro | own card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| SWE-bench Pro | 60.37 | SWE-bench Pro | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Pro | 43.900 | SWE-bench Pro (no-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Multilingual | 81.0 | Multilingual software engineering SWE-bench Multilingual | own card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| SWE-bench Multilingual | 77.10 | SWE-bench Multilingual | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Multilingual | 73.000 | SWE-bench Multilingual (non-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| LiveCodeBench v6 | 91.9 | Competitive coding LiveCodeBench v6 | own card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| LiveCodeBench v6 | 94.1 | LiveCodeBench v6 | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| Toolathlon-Verified | 73.5 | Real-world tool use Toolathlon Verified (Pass@1) | own card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| Toolathlon-Verified | 71.400 | Toolathlon-Verified | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 20.71 | Terminal Bench 4 [offline] | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| DeepSWE | 58.7 | Agentic coding DeepSWE 1.1 | own card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| DeepSWE | 55.57 | DeepSWE [offline] | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| NL2Repo | 48.1 | Repo-level code generation NL2Repo-Bench | own card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| NL2Repo | 45.200 | NL2Repo | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| Agents' Last Exam | Pass@1 24.3 Score 51.2 | Frontier agentic tasks Agents' Last Exam | own card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| CyberGym | 78.000 | CyberGym | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- DeepSWE: Qwen 58.7 (Agentic coding DeepSWE 1.1); nvidia 55.57 (DeepSWE
  [offline])
- SWE-bench Pro: Qwen 62.5 (Agentic coding SWE-bench Pro); nvidia 60.37
  (SWE-bench Pro); ornith-ai 43.900 (SWE-bench Pro (no-hack))
- SWE-bench Multilingual: Qwen 81.0 (Multilingual software engineering SWE-bench
  Multilingual); nvidia 77.10 (SWE-bench Multilingual); ornith-ai 73.000
  (SWE-bench Multilingual (non-hack))
- NL2Repo: Qwen 48.1 (Repo-level code generation NL2Repo-Bench); ornith-ai
  45.200 (NL2Repo)
- Toolathlon-Verified: Qwen 73.5 (Real-world tool use Toolathlon Verified
  (Pass@1)); ornith-ai 71.400 (Toolathlon-Verified)
- LiveCodeBench v6: Qwen 91.9 (Competitive coding LiveCodeBench v6); nvidia 94.1
  (LiveCodeBench v6)
- SWE-bench Verified: nvidia 78.7 (SWE-bench Verified); ornith-ai 82.800
  (SWE-bench Verified (non-hack))
- Terminal-Bench 2.1: nvidia 85.80 (Terminal-Bench 2.1); ornith-ai 83.400
  (TerminalBench 2.1)

## Not found

- Easy: Aider Polyglot, BFCL v4
- Hard: SWE-Marathon, ProgramBench, FrontierSWE, SWE-Atlas-QnA
- Vuln audit: CyberGym-E2E, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
