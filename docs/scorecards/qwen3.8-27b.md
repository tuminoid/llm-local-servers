# Qwen3.8-27B published benchmarks

Model: [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) at
`1d4bf0f2ff60`, created 2026-08-05. Fetched 2026-10-25 by the model-benchmarks
skill. Published claims only, quoted as written; nothing here was measured by
this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 73.0 | Agentic terminal coding Terminal Bench 2.1 (Terminus) | own card | Qwen | - | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) |
| Terminal-Bench 2.1 | 73.0 | Terminal-Bench 2.1 | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| Terminal-Bench 2.1 | 71.900 | TerminalBench 2.1 | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Verified | 76.800 | SWE-bench Verified (non-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Pro | 61.7 | Agentic coding SWE-bench Pro | own card | Qwen | - | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) |
| SWE-bench Pro | 61.7 | Agentic coding SWE-bench Pro | vendor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| SWE-bench Pro | 61.7 | SWE-Bench Pro | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| SWE-bench Pro | 65.500 | SWE-bench Pro (no-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Multilingual | 73.8 | Multilingual software engineering SWE-bench Multilingual | vendor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| SWE-bench Multilingual | 70.300 | SWE-bench Multilingual (non-hack) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| LiveCodeBench v6 | 90.3 | Competitive coding LiveCodeBench v6 | own card | Qwen | - | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) |
| LiveCodeBench v6 | 90.3 | Competitive coding LiveCodeBench v6 | vendor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| Toolathlon-Verified | 67.1 | Real-world tool use Toolathlon Verified (Pass@1) | vendor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| Toolathlon-Verified | 68.5 | Toolathlon-Verified | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| Toolathlon-Verified | 67.100 | Toolathlon-Verified | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 6.3 | Terminal-Bench 4.0 | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| DeepSWE | 42.2 | Agentic coding DeepSWE 1.1 | own card | Qwen | - | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) |
| DeepSWE | 42.2 | Agentic coding DeepSWE 1.1 | vendor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| DeepSWE | 42.5 | DeepSWE | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| ProgramBench | 0.00% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/programbench) |
| NL2Repo | 42.3 | Repo-level code generation NL2Repo-Bench | own card | Qwen | - | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) |
| NL2Repo | 42.3 | Repo-level code generation NL2Repo-Bench | vendor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |
| NL2Repo | 48.3 | NL2Repo | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| NL2Repo | 42.300 | NL2Repo | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-Atlas-QnA | 41.9 | SWE-Atlas-QnA | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| Agents' Last Exam | Pass@1 20.4 Score 42.9 | Frontier agentic tasks Agents' Last Exam | own card | Qwen | - | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) |
| Agents' Last Exam | Pass@1 20.4 Score 42.9 | Frontier agentic tasks Agents' Last Exam | vendor card | Qwen | - | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| CyberGym | 55.000 | CyberGym | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| Vals CyberBench | 67.80% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/cyber) |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- Terminal-Bench 2.1: Qwen 73.0 (Agentic terminal coding Terminal Bench 2.1
  (Terminus)); Nanbeige 73.0 (Terminal-Bench 2.1); ornith-ai 71.900
  (TerminalBench 2.1)
- SWE-bench Pro: Qwen 61.7 (Agentic coding SWE-bench Pro); Nanbeige 61.7
  (SWE-Bench Pro); ornith-ai 65.500 (SWE-bench Pro (no-hack))
- NL2Repo: Qwen 42.3 (Repo-level code generation NL2Repo-Bench); Nanbeige 48.3
  (NL2Repo); ornith-ai 42.300 (NL2Repo)
- DeepSWE: Qwen 42.2 (Agentic coding DeepSWE 1.1); Nanbeige 42.5 (DeepSWE)
- Toolathlon-Verified: Nanbeige 68.5 (Toolathlon-Verified); Qwen 67.1
  (Real-world tool use Toolathlon Verified (Pass@1)); ornith-ai 67.100
  (Toolathlon-Verified)
- SWE-bench Multilingual: Qwen 73.8 (Multilingual software engineering SWE-bench
  Multilingual); ornith-ai 70.300 (SWE-bench Multilingual (non-hack))

## Not found

- Easy: Aider Polyglot, BFCL v4
- Hard: SWE-Marathon, FrontierSWE
- Vuln audit: CyberGym-E2E, SEC-bench Pro, SEC-bench, ExploitBench, ExploitGym,
  CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
