# Development Snapshot

This sanitized table preserves aggregate observations from one exploratory run per model route. It contains no raw model output, session identifier, personal path, or provider payload.

| Model route | One-shot correct (33) | Agentic correct (10) | REPL use (40) | Agentic timeouts |
|---|---:|---:|---:|---:|
| `ollama-cloud/deepseek-v4-flash` | 32 | 6 | 33 | 0 |
| `ollama-cloud/deepseek-v4-pro` | 33 | 6 | 34 | 0 |
| `zai-coding-plan/glm-5.2` | 33 | 6 | 33 | 0 |
| `openai/gpt-5.6-sol` | 32 | 8 | 35 | 0 |
| `ollama-cloud/kimi-k2.5` | 32 | 4 | 33 | 0 |
| `ollama-cloud/kimi-k2.6` | 32 | 7 | 30 | 0 |
| `ollama-cloud/minimax-m2.5` | 29 | 4 | 28 | 6 |
| `llama-cpp-qwen27/Qwen3.6-27B-Q4_K_M.gguf` | 29 | 7 | 33 | 0 |
| `llama-cpp-qwen/Qwen3.6-35B-A3B-Q4_K_M.gguf` | 23 | 6 | 26 | 3 |

## Methodology Notes

- Snapshot date: 2026-07-21.
- One-shot suite hash recorded by the source run artifacts: `c34c4c7f06a4a6117277137163d083e39f7208727300b8c7b72e3e5c188d0a96`.
- Bundled release suite hash: `7b90af9a2bface2c6ee43a84c709268e95679a7d29802d5a5d2a38d05d8d3bc9`. The file hash changed while making the harness standalone: personal provenance comments were generalized and Babashka discovery was made portable. The 33 task definitions, prompts, and checkers used for these observations were not changed. The historical artifacts and bundled file are therefore not byte-identical even though the evaluated task semantics are unchanged.
- Agentic suite hash recorded by the source runs: `ce6d62226ecfe58cd2af17b8cf3ce8bf38edc6db7034501a3ac2d337efd99433`.
- Current agentic suite hash: `3f3bc431e14c3bbf4aec013af403d7df99c5706b5a0ef7823ef12cc20dc87d57`. The release clarifies previously implicit malformed-EDN and multimethod contracts, and renames public grader directories. These historical scores must not be mixed with new run artifacts or presented as results from the current agentic suite.
- Every entry is a single-run exploratory observation, not an estimate of expected performance.
- The one-shot and agentic suites measure different tasks and their scores must not be added or averaged together.
- REPL use is a heuristic workflow signal based on observed evaluations. It is not correctness, quality, safety, or proof that the REPL caused a repair.
- Model routes are provider identifiers, not immutable model version guarantees. Hosted implementations may change.
- Local Qwen observations depend on the exact GGUF, llama.cpp revision and flags, and hardware.
- Prompts, graders, and reference solutions are public, so contamination or task-specific adaptation cannot be excluded.
- OpenCode permissions are not an OS sandbox.
- Raw elapsed totals were omitted because these runs crossed providers and local hardware; they are not cross-provider speed comparisons.
- This project does not operate a secure leaderboard.

See [`../docs/METHODOLOGY.md`](../docs/METHODOLOGY.md) before interpreting or reproducing these results.
