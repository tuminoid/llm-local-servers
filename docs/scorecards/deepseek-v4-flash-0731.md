# DeepSeek-V4-Flash-0731 published benchmarks

Model:
[deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)
at `7872f01b1d1f`, created 2026-07-31. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 82.7 | Terminal Bench 2.1 | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md) |
| Terminal-Bench 2.1 | 76.80 | Terminal-Bench 2.1 | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| Terminal-Bench 2.1 | 82.700 | TerminalBench 2.1 | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Verified | 75.4 | SWE-bench Verified | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Pro | 56.0 | Agentic coding SWE-bench Pro | competitor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| SWE-bench Pro | 56.91 | SWE-bench Pro | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Multilingual | 72.0 | SWE-bench Multilingual | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| LiveCodeBench v6 | 90.6 | Competitive coding LiveCodeBench v6 | competitor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| LiveCodeBench v6 | 94.6 | LiveCodeBench v6 | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| Toolathlon-Verified | 70.3 | Toolathlon-Verified | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md) |
| Toolathlon-Verified | 70.3 | Real-world tool use Toolathlon Verified (Pass@1) | competitor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| Toolathlon-Verified | 70.300 | Toolathlon-Verified | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 3.54 | Terminal Bench 4 [offline] | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| Terminal-Bench 4.0 | 18.69% | Vals AI | leaderboard | Vals AI | Mini-SWE-agent | [www.vals.ai](https://www.vals.ai/benchmarks/terminal-bench-4) |
| DeepSWE | 54.4 | DeepSWE | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md) |
| DeepSWE | 54.4 | Agentic coding DeepSWE 1.1 | competitor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| DeepSWE | 42.3 | DeepSWE [offline] | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| ProgramBench | 0.00% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/programbench) |
| NL2Repo | 54.2 | NL2Repo | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md) |
| NL2Repo | 54.2 | Repo-level code generation NL2Repo-Bench | competitor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| NL2Repo | 54.200 | NL2Repo | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| Agents' Last Exam | 25.2 | Agents' Last Exam | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md) |
| Agents' Last Exam | Pass@1 25.2 Score -- | Frontier agentic tasks Agents' Last Exam | competitor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| CyberGym-E2E | 55.7 | PATCH-ONLY; Aegis | leaderboard | CyberGym | 920 tasks; self-hosted / 90 min; submitter ZJU Aegis | [www.cybergym.io](https://www.cybergym.io/cybergym-e2e/) |
| CyberGym-E2E | 32.5 | S1; Aegis | leaderboard | CyberGym | 920 tasks; self-hosted / 90 min; submitter ZJU Aegis | [www.cybergym.io](https://www.cybergym.io/cybergym-e2e/) |
| CyberGym-E2E | 29.2 | S2; Aegis | leaderboard | CyberGym | 920 tasks; self-hosted / 90 min; submitter ZJU Aegis | [www.cybergym.io](https://www.cybergym.io/cybergym-e2e/) |
| CyberGym-E2E | 28.4 | S3; Aegis | leaderboard | CyberGym | 920 tasks; self-hosted / 90 min; submitter ZJU Aegis | [www.cybergym.io](https://www.cybergym.io/cybergym-e2e/) |
| CyberGym-E2E | 10.3 | S4; Aegis | leaderboard | CyberGym | 920 tasks; self-hosted / 90 min; submitter ZJU Aegis | [www.cybergym.io](https://www.cybergym.io/cybergym-e2e/) |
| CyberGym | 76.7 | Cybergym | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/7872f01b1d1fe23eabc4c98b48bffcef5a386062/README.md) |
| CyberGym | 76.700 | CyberGym | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| Vals CyberBench | 72.08% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/cyber) |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- Terminal-Bench 2.1: deepseek-ai 82.7 (Terminal Bench 2.1); nvidia 76.80
  (Terminal-Bench 2.1); ornith-ai 82.700 (TerminalBench 2.1)
- DeepSWE: deepseek-ai 54.4 (DeepSWE); Qwen 54.4 (Agentic coding DeepSWE 1.1);
  nvidia 42.3 (DeepSWE [offline])
- Agents' Last Exam: deepseek-ai 25.2 (Agents' Last Exam); Qwen Pass@1 25.2
  Score -- (Frontier agentic tasks Agents' Last Exam)
- SWE-bench Pro: Qwen 56.0 (Agentic coding SWE-bench Pro); nvidia 56.91
  (SWE-bench Pro)
- LiveCodeBench v6: Qwen 90.6 (Competitive coding LiveCodeBench v6); nvidia 94.6
  (LiveCodeBench v6)
- Terminal-Bench 4.0: nvidia 3.54 (Terminal Bench 4 [offline]); Vals AI 18.69%
  (Vals AI)
- CyberGym-E2E: CyberGym 32.5 (S1; Aegis); CyberGym 29.2 (S2; Aegis); CyberGym
  28.4 (S3; Aegis); CyberGym 10.3 (S4; Aegis); CyberGym 55.7 (PATCH-ONLY; Aegis)

## Not found

- Easy: Aider Polyglot, BFCL v4
- Hard: SWE-Marathon, FrontierSWE, SWE-Atlas-QnA
- Vuln audit: SEC-bench Pro, SEC-bench, ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
