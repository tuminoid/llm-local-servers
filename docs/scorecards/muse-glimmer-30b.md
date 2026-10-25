# Muse-Glimmer-30B published benchmarks

Model:
[meta-models/Muse-Glimmer-30B](https://huggingface.co/meta-models/Muse-Glimmer-30B)
at `cec94fcfd651`, created 2026-08-09. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 61.8 | Terminal-Bench 2.1 | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| Terminal-Bench 2.1 | 51.7 | Agentic terminal coding Terminal Bench 2.1 (Terminus) | competitor card | Qwen | - | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) |
| Terminal-Bench 2.1 | 51.7 | Terminal-Bench 2.1 (Terminus-2) | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-35B-A3B](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B/blob/10fbf86fed7ecee4a061f8b499a618f46001cac1/README.md) |
| SWE-bench Verified | 76 | SWE-bench Verified | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-35B-A3B](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B/blob/10fbf86fed7ecee4a061f8b499a618f46001cac1/README.md) |
| SWE-bench Pro | 36.9 | SWE-Bench Pro | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| SWE-bench Pro | 51.2 | Agentic coding SWE-bench Pro | competitor card | Qwen | - | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) |
| SWE-bench Pro | 51.2 | SWE-bench Pro | competitor card | ornith-ai | - | [ornith-ai/Ornith-1.5-35B-A3B](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B/blob/10fbf86fed7ecee4a061f8b499a618f46001cac1/README.md) |
| Toolathlon-Verified | 47.2 | Toolathlon-Verified | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 1.6 | Terminal-Bench 4.0 | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| DeepSWE | 4.4 | DeepSWE | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| NL2Repo | 27.4 | NL2Repo | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| SWE-Atlas-QnA | 17.7 | SWE-Atlas-QnA | competitor card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- Terminal-Bench 2.1: Nanbeige 61.8 (Terminal-Bench 2.1); Qwen 51.7 (Agentic
  terminal coding Terminal Bench 2.1 (Terminus)); ornith-ai 51.7 (Terminal-Bench
  2.1 (Terminus-2))
- SWE-bench Pro: Nanbeige 36.9 (SWE-Bench Pro); Qwen 51.2 (Agentic coding
  SWE-bench Pro); ornith-ai 51.2 (SWE-bench Pro)

## Not found

- Easy: SWE-bench Multilingual, LiveCodeBench v6, Aider Polyglot, BFCL v4
- Hard: SWE-Marathon, ProgramBench, FrontierSWE, Agents' Last Exam
- Vuln audit: CyberGym-E2E, CyberGym, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
