# Ornith-1.5-122B published benchmarks

Model:
[ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B) at
`7681ef608624`, created 2026-10-16. Fetched 2026-10-25 by the model-benchmarks
skill. Published claims only, quoted as written; nothing here was measured by
this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 81.200 | TerminalBench 2.1 | own card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Verified | 84.500 | SWE-bench Verified (non-hack) | own card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Pro | 76.900 | SWE-bench Pro (no-hack) | own card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| SWE-bench Multilingual | 76.400 | SWE-bench Multilingual (non-hack) | own card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |
| Toolathlon-Verified | 70.800 | Toolathlon-Verified | own card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| NL2Repo | 51.200 | NL2Repo | own card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| CyberGym | 80.000 | CyberGym | own card | ornith-ai | - | [ornith-ai/Ornith-1.5-122B](https://huggingface.co/ornith-ai/Ornith-1.5-122B/blob/7681ef608624e7532d8164128bcffdbdbaf1b1af/README.md) |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

None.

## Not found

- Easy: LiveCodeBench v6, Aider Polyglot, BFCL v4
- Hard: Terminal-Bench 4.0, DeepSWE, SWE-Marathon, ProgramBench, FrontierSWE,
  SWE-Atlas-QnA, Agents' Last Exam
- Vuln audit: CyberGym-E2E, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
