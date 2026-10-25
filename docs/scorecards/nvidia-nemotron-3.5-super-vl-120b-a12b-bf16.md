# NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16 published benchmarks

Model:
[nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16)
at `fb0ee0bc6b3f`, created 2026-10-12. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 60.67 | Terminal-Bench 2.1 | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| Terminal-Bench 2.1 | 66.700 | TerminalBench 2.1 | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Verified | 71.10 | SWE-bench Verified | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Verified | 61.200 | SWE-bench Verified (non-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Pro | 51.78 | SWE-bench Pro | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Pro | 42.500 | SWE-bench Pro (no-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Multilingual | 67.72 | SWE-bench Multilingual | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Multilingual | 48.000 | SWE-bench Multilingual (non-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| LiveCodeBench v6 | 88.22 | LiveCodeBench v6 | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| Toolathlon-Verified | 60.100 | Toolathlon-Verified | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 1 | Terminal Bench 4 [offline] | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| DeepSWE | 24.65 | DeepSWE [offline] | own card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| NL2Repo | 21.000 | NL2Repo | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| CyberGym | 34.000 | CyberGym | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- SWE-bench Verified: nvidia 71.10 (SWE-bench Verified); ornith-ai 61.200
  (SWE-bench Verified (non-hack))
- SWE-bench Multilingual: nvidia 67.72 (SWE-bench Multilingual); ornith-ai
  48.000 (SWE-bench Multilingual (non-hack))
- SWE-bench Pro: nvidia 51.78 (SWE-bench Pro); ornith-ai 42.500 (SWE-bench Pro
  (no-hack))
- Terminal-Bench 2.1: nvidia 60.67 (Terminal-Bench 2.1); ornith-ai 66.700
  (TerminalBench 2.1)

## Not found

- Easy: Aider Polyglot, BFCL v4
- Hard: SWE-Marathon, ProgramBench, FrontierSWE, SWE-Atlas-QnA, Agents' Last
  Exam
- Vuln audit: CyberGym-E2E, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
