# granite-4.2-30b published benchmarks

Model:
[ibm-granite/granite-4.2-30b](https://huggingface.co/ibm-granite/granite-4.2-30b)
at `9e668ce1c538`, created 2026-08-07. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 29.24 | Terminal-Bench 2.1 | own card | ibm-granite | - | [ibm-granite/granite-4.2-30b](https://huggingface.co/ibm-granite/granite-4.2-30b/blob/9e668ce1c538387ef24d3644e9b0606647762636/README.md) |
| SWE-bench Verified | 57 | SWE Bench Verified | own card | ibm-granite | - | [ibm-granite/granite-4.2-30b](https://huggingface.co/ibm-granite/granite-4.2-30b/blob/9e668ce1c538387ef24d3644e9b0606647762636/README.md) |
| SWE-bench Pro | 33.29 | SWE Bench Pro | own card | ibm-granite | - | [ibm-granite/granite-4.2-30b](https://huggingface.co/ibm-granite/granite-4.2-30b/blob/9e668ce1c538387ef24d3644e9b0606647762636/README.md) |
| SWE-bench Multilingual | 41.89 | SWE Bench Multilingual | own card | ibm-granite | - | [ibm-granite/granite-4.2-30b](https://huggingface.co/ibm-granite/granite-4.2-30b/blob/9e668ce1c538387ef24d3644e9b0606647762636/README.md) |
| LiveCodeBench v6 | 75.77 | LiveCodeBench v6 | own card | ibm-granite | - | [ibm-granite/granite-4.2-30b](https://huggingface.co/ibm-granite/granite-4.2-30b/blob/9e668ce1c538387ef24d3644e9b0606647762636/README.md) |
| BFCL v4 | 61.39 | BFCL (v4) | own card | ibm-granite | - | [ibm-granite/granite-4.2-30b](https://huggingface.co/ibm-granite/granite-4.2-30b/blob/9e668ce1c538387ef24d3644e9b0606647762636/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |

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

- Easy: Aider Polyglot, Toolathlon-Verified
- Hard: Terminal-Bench 4.0, DeepSWE, SWE-Marathon, ProgramBench, FrontierSWE,
  NL2Repo, SWE-Atlas-QnA, Agents' Last Exam
- Vuln audit: CyberGym-E2E, CyberGym, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
