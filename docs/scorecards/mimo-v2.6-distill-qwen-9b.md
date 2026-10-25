# MiMo-V2.6-Distill-Qwen-9B published benchmarks

Model:
[XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B)
at `2367e865d009`, created 2026-09-21. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 37.1 | Terminal Bench 2.1 | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B/blob/2367e865d009c13ac81713a2878291d33ab28177/README.md) |
| Toolathlon-Verified | 35.2 | Toolathlon-Verified | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B/blob/2367e865d009c13ac81713a2878291d33ab28177/README.md) |

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

- Easy: SWE-bench Verified, SWE-bench Pro, SWE-bench Multilingual, LiveCodeBench
  v6, Aider Polyglot, BFCL v4
- Hard: Terminal-Bench 4.0, DeepSWE, SWE-Marathon, ProgramBench, FrontierSWE,
  NL2Repo, SWE-Atlas-QnA, Agents' Last Exam
- Vuln audit: CyberGym-E2E, CyberGym, Vals CyberBench, SEC-bench Pro, SEC-bench,
  ExploitBench, ExploitGym, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
