# MiMo-V2.6-Flash-RL published benchmarks

Model:
[XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL)
at `dcd3fd83fb18`, created 2026-09-21. Fetched 2026-10-25 by the
model-benchmarks skill. Published claims only, quoted as written; nothing here
was measured by this repository.

## Easy

Saturated or near-saturated at the frontier, still spread among small and
mid-size open models.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 2.1 | 87.6 | Terminal Bench 2.1 | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| Terminal-Bench 2.1 | 87.6 | Terminal Bench 2.1 | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |
| Toolathlon-Verified | 73.6 | Toolathlon-Verified | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| Toolathlon-Verified | 73.6 | Toolathlon-Verified | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |

## Hard

Long-horizon software engineering where the frontier still scores low or models
spread widely.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| Terminal-Bench 4.0 | 28.8 | Terminal Bench 4.0 | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| Terminal-Bench 4.0 | 28.8 | Terminal Bench 4.0 | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |
| Terminal-Bench 4.0 | 24.24% | Vals AI | leaderboard | Vals AI | Mini-SWE-agent | [www.vals.ai](https://www.vals.ai/benchmarks/terminal-bench-4) |
| DeepSWE | 67.9 | DeepSWE v1.1 | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| DeepSWE | 67.9 | DeepSWE v1.1 | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |
| ProgramBench | 26.0 | ProgramBench | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| ProgramBench | 26.0 | ProgramBench | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |
| ProgramBench | 0.50% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/programbench) |
| Agents' Last Exam | 27.6 | Agents’ Last Exam | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| Agents' Last Exam | 27.6 | Agents’ Last Exam | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |

## Vuln audit

Finding, reproducing, exploiting and patching vulnerabilities in real code;
CTF-style benchmarks are out of scope.

| Benchmark | Score | As labelled | Source | Reporter | Settings | Where |
| -- | --: | -- | -- | -- | -- | -- |
| CyberGym | 95.1 | CyberGym | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| CyberGym | 95.1 | CyberGym | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |
| Vals CyberBench | 77.2 | MiMo Cyber Bench | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| Vals CyberBench | 77.2 | MiMo Cyber Bench | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |
| Vals CyberBench | 75.36% | Vals AI | leaderboard | Vals AI | - | [www.vals.ai](https://www.vals.ai/benchmarks/cyber) |
| SEC-bench Pro | 47.5 | SEC Bench Pro | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| SEC-bench Pro | 47.5 | SEC Bench Pro | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |
| ExploitBench | 25.3 | ExploitBench | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| ExploitBench | 25.3 | ExploitBench | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |
| ExploitGym | 6.0 | ExploitGym | own card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Flash-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL/blob/dcd3fd83fb181622fbc606fbb1709901982a62c2/README.md) |
| ExploitGym | 6.0 | ExploitGym | vendor card | XiaomiMiMo | - | [XiaomiMiMo/MiMo-V2.6-Pro-RL](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/b61f21852680ee02a29e946e18cf8697f4844061/README.md) |

## Discrepancies

Benchmarks whose sources disagree; differing labels often mean a different
variant, harness or metric.

- ProgramBench: XiaomiMiMo 26.0 (ProgramBench); Vals AI 0.50% (Vals AI)
- Terminal-Bench 4.0: XiaomiMiMo 28.8 (Terminal Bench 4.0); Vals AI 24.24% (Vals
  AI)
- Vals CyberBench: XiaomiMiMo 77.2 (MiMo Cyber Bench); Vals AI 75.36% (Vals AI)

## Not found

- Easy: SWE-bench Verified, SWE-bench Pro, SWE-bench Multilingual, LiveCodeBench
  v6, Aider Polyglot, BFCL v4
- Hard: SWE-Marathon, FrontierSWE, NL2Repo, SWE-Atlas-QnA
- Vuln audit: CyberGym-E2E, SEC-bench, CVE-Bench

## Unreadable sources

- Terminal-Bench 2.1: <https://www.tbench.ai/?version=2.1> (client-rendered; the
  server only renders the current board)
- Agents' Last Exam: <https://agents-last-exam.org> (client-rendered table)
- SWE-Marathon: <https://www.swe-marathon.org/> (no leaderboard published yet)
