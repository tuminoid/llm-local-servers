# Nanbeige4.3-33B published benchmarks

Model:
[Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B) at
`c1093c501cc6`, created 2026-10-24. Fetched 2026-10-25 by the model-benchmarks
skill. Published claims only, quoted as written; nothing here was measured by
this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 80.9 | Terminal-Bench 2.1 | own card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| SWE-bench Pro | 60.3 | SWE-Bench Pro | own card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| Toolathlon-Verified | 70.4 | Toolathlon-Verified | own card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 23.8 | Terminal-Bench 4.0 | own card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| DeepSWE | 65.5 | DeepSWE | own card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| NL2Repo | 53.0 | NL2Repo | own card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |
| SWE-Atlas-QnA | 50.8 | SWE-Atlas-QnA | own card | Nanbeige | - | [Nanbeige/Nanbeige4.3-33B](https://huggingface.co/Nanbeige/Nanbeige4.3-33B/blob/c1093c501cc6460427c0ac634db7223d0450c0ee/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

None.

## Not found

- Easy: SWE-bench Verified, SWE-bench Multilingual, LiveCodeBench v6, Aider
  Polyglot, BFCL v4
- Hard: SWE-Marathon, ProgramBench, FrontierSWE, Agents' Last Exam
- Vuln audit: CyberGym-E2E, CyberGym, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
