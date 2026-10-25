# DeepSeek-V4.1-Flash-1017 published benchmarks

Model:
[deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)
at `1bae0e108899`, created 2026-10-17. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 42.3 | Terminal-Bench 4.0 | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/blob/1bae0e1088993b9b82de08f59de5be5a34e42170/README.md) |
| Terminal-Bench 4.0 | 42.3 | Terminal Bench 4.0 | competitor card | MiniMaxAI | - | [MiniMaxAI/MiniMax-M3.1-Flash](https://huggingface.co/MiniMaxAI/MiniMax-M3.1-Flash/blob/54e4e69dfc452b1e94a426c24a4fdeeaa8e3ad5e/README.md) |
| Terminal-Bench 4.0 | 31.82% | Vals AI | leaderboard | Vals AI | Mini-SWE-agent | [www.vals.ai](https://www.vals.ai/benchmarks/terminal-bench-4) |
| DeepSWE | 77.0 | DeepSWE v1.1 | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/blob/1bae0e1088993b9b82de08f59de5be5a34e42170/README.md) |
| DeepSWE | 77.0 | DeepSWE v1.1 | competitor card | MiniMaxAI | - | [MiniMaxAI/MiniMax-M3.1-Flash](https://huggingface.co/MiniMaxAI/MiniMax-M3.1-Flash/blob/54e4e69dfc452b1e94a426c24a4fdeeaa8e3ad5e/README.md) |
| ProgramBench | 29.1 | ProgramBench | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/blob/1bae0e1088993b9b82de08f59de5be5a34e42170/README.md) |
| NL2Repo | 68.2 | NL2Repo-Bench | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/blob/1bae0e1088993b9b82de08f59de5be5a34e42170/README.md) |
| NL2Repo | 68.2 | NL2Repo-Bench | competitor card | MiniMaxAI | - | [MiniMaxAI/MiniMax-M3.1-Flash](https://huggingface.co/MiniMaxAI/MiniMax-M3.1-Flash/blob/54e4e69dfc452b1e94a426c24a4fdeeaa8e3ad5e/README.md) |
| Agents' Last Exam | 35.4 | Agents’ Last Exam | own card | deepseek-ai | - | [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/blob/1bae0e1088993b9b82de08f59de5be5a34e42170/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- Terminal-Bench 4.0: deepseek-ai 42.3 (Terminal-Bench 4.0); MiniMaxAI 42.3
  (Terminal Bench 4.0); Vals AI 31.82% (Vals AI)

## Not found

- Easy: Terminal-Bench 2.1, SWE-bench Verified, SWE-bench Pro, SWE-bench
  Multilingual, LiveCodeBench v6, Aider Polyglot, BFCL v4, Toolathlon-Verified
- Hard: SWE-Marathon, FrontierSWE, SWE-Atlas-QnA
- Vuln audit: CyberGym-E2E, CyberGym, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
