# GLM-5.3-Flash published benchmarks

Model: [zai-org/GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash) at
`46a050bec130`, created 2026-08-25. Fetched 2026-10-25 by the model-benchmarks
skill. Published claims only, quoted as written; nothing here was measured by
this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 82.70 | Terminal-Bench 2.1 | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Verified | 79.10 | SWE-bench Verified | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Pro | 59.70 | SWE-bench Pro | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| SWE-bench Multilingual | 78.30 | SWE-bench Multilingual | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| LiveCodeBench v6 | 80.6 | LiveCodeBench v6 | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 15.15 | Terminal Bench 4 [offline] | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| Terminal-Bench 4.0 | 35.76 | Claude Code; effort none | leaderboard | Terminal-Bench | 330 trials | [www.tbench.ai](https://www.tbench.ai/) |
| Terminal-Bench 4.0 | 37.37% | Vals AI | leaderboard | Vals AI | Mini-SWE-agent | [www.vals.ai](https://www.vals.ai/benchmarks/terminal-bench-4) |
| DeepSWE | 57.77 / 63.4 (reported) | DeepSWE [offline] | competitor card | nvidia | - | [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16/blob/fb0ee0bc6b3f70342afd8d84cb80dbadbaa8a1fe/README.md) |
| DeepSWE | 63% | effort max | leaderboard | Datacurve | ± 4% | [deepswe.datacurve.ai](https://deepswe.datacurve.ai/) |
| ProgramBench | 0.00% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/programbench) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Vals CyberBench | 67.86% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/cyber) |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- Terminal-Bench 4.0: nvidia 15.15 (Terminal Bench 4 [offline]); Terminal-Bench
  35.76 (Claude Code; effort none); Vals AI 37.37% (Vals AI)
- DeepSWE: nvidia 57.77 / 63.4 (reported) (DeepSWE [offline]); Datacurve 63%
  (effort max)

## Not found

- Easy: Aider Polyglot, BFCL v4, Toolathlon-Verified
- Hard: SWE-Marathon, FrontierSWE, NL2Repo, SWE-Atlas-QnA, Agents' Last Exam
- Vuln audit: CyberGym-E2E, CyberGym, SEC-bench Pro, SEC-bench, ExploitBench,
  ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
