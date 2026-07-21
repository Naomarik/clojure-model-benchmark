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

## Retrospective Weighted Aggregate

This table applies metric `correctness-weighted-v1` after the development runs. The weights were assigned retrospectively after these results existed and are not preregistered. It is not a current public-treatment result. Every row is historical because the REPL artifacts predate the current wording of `hot-reload-pricing` and `payment-multimethod`, and all artifacts predate protocol fingerprints. The one-shot and REPL component scores remain primary; overall is a secondary correctness-only 50/50 normalized summary. REPL-use telemetry, elapsed time, tokens, and cost are excluded.

| Exact model route | One-shot weighted | REPL weighted | Direct raw diagnostic | Secondary overall | Status |
|---|---:|---:|---:|---:|---|
| `openai/gpt-5.6-sol` | 76/79 (96.2025%) | 38/46 (82.6087%) | 114/125 (91.2000%) | **89.4056** | historical; infrastructure-provisional |
| `ollama-cloud/kimi-k2.6` | 77/79 (97.4684%) | 33/46 (71.7391%) | 110/125 (88.0000%) | **84.6037** | historical; infrastructure-provisional |
| `ollama-cloud/deepseek-v4-pro` | 79/79 (100.0000%) | 28/46 (60.8696%) | 107/125 (85.6000%) | **80.4348** | historical |
| `zai-coding-plan/glm-5.2` | 79/79 (100.0000%) | 28/46 (60.8696%) | 107/125 (85.6000%) | **80.4348** | historical |
| `llama-cpp-qwen27/Qwen3.6-27B-Q4_K_M.gguf` | 67/79 (84.8101%) | 33/46 (71.7391%) | 100/125 (80.0000%) | **78.2746** | historical |
| `ollama-cloud/deepseek-v4-flash` | 75/79 (94.9367%) | 28/46 (60.8696%) | 103/125 (82.4000%) | **77.9031** | historical |
| `ollama-cloud/kimi-k2.5` | 76/79 (96.2025%) | 18/46 (39.1304%) | 94/125 (75.2000%) | **67.6665** | historical |
| `ollama-cloud/minimax-m2.5` | 66/79 (83.5443%) | 18/46 (39.1304%) | 84/125 (67.2000%) | **61.3374** | historical |
| `llama-cpp-qwen/Qwen3.6-35B-A3B-Q4_K_M.gguf` | 48/79 (60.7595%) | 28/46 (60.8696%) | 76/125 (60.8000%) | **60.8145** | historical |

`openai/gpt-5.6-sol` has a null-response request failure on `ctx_remove_empty_vals`, and `ollama-cloud/kimi-k2.6` has one on `fn_normalize_email`. The retrospective calculation uses their recorded false booleans, but both rows are infrastructure-provisional and require complete valid reruns before publication as current scores. Ordinary agent timeouts retain their fresh-process grader outcomes and are reported in the original table above.

The exact formula, task weights, validation policy, and historical limitations are documented in [`../docs/WEIGHTING.md`](../docs/WEIGHTING.md).

## Current-Treatment Claude Aggregate

These single Claude Code runs match the current suite and protocol fingerprints and contain no infrastructure-invalid cases. They all use `--effort low`. The v1 weights were still assigned retrospectively after results existed, so the component scores remain primary.

| Exact model route | One-shot weighted | REPL weighted | Secondary overall | Status |
|---|---:|---:|---:|---|
| `claude-fable-5` | 79/79 (100.0000%) | 33/46 (71.7391%) | **85.8696** | current treatment; retrospective weighting |
| `claude-opus-4-8` | 79/79 (100.0000%) | 33/46 (71.7391%) | **85.8696** | current treatment; retrospective weighting |
| `claude-haiku-4-5` | 76/79 (96.2025%) | 33/46 (71.7391%) | **83.9708** | current treatment; retrospective weighting |
| `claude-sonnet-5` | 76/79 (96.2025%) | 33/46 (71.7391%) | **83.9708** | current treatment; retrospective weighting |

## Methodology Notes

- Snapshot date: 2026-07-21.
- One-shot suite hash recorded by the source run artifacts: `c34c4c7f06a4a6117277137163d083e39f7208727300b8c7b72e3e5c188d0a96`.
- Bundled release suite hash: `7b90af9a2bface2c6ee43a84c709268e95679a7d29802d5a5d2a38d05d8d3bc9`. The file hash changed while making the harness standalone: personal provenance comments were generalized and Babashka discovery was made portable. The 33 task definitions, prompts, and checkers used for these observations were not changed. The historical artifacts and bundled file are therefore not byte-identical even though the evaluated task semantics are unchanged.
- Agentic suite hash recorded by the source runs: `ce6d62226ecfe58cd2af17b8cf3ce8bf38edc6db7034501a3ac2d337efd99433`.
- Current agentic suite hash: `3f3bc431e14c3bbf4aec013af403d7df99c5706b5a0ef7823ef12cc20dc87d57`. The release clarifies previously implicit malformed-EDN and multimethod contracts, and renames public grader directories. These historical scores must not be mixed with new run artifacts or presented as results from the current agentic suite.
- Historical artifacts do not contain `protocol_sha256`; exact current runner, agent, configuration, and fixture treatment equivalence cannot be established from them.
- Metric-definition hash: `26d37c069a76255d6b87448a4733bc1ab240de467c794ff571c4ff32188e91e0`.
- Every entry is a single-run exploratory observation, not an estimate of expected performance.
- The one-shot and agentic suites measure different tasks, so their component scores remain primary. The secondary weighted overall uses the fixed correctness-only normalization documented in `docs/WEIGHTING.md`; an unnormalized addition or average is not the overall metric.
- REPL use is a heuristic workflow signal based on observed evaluations. It is not correctness, quality, safety, or proof that the REPL caused a repair.
- Model routes are provider identifiers, not immutable model version guarantees. Hosted implementations may change.
- Local Qwen observations depend on the exact GGUF, llama.cpp revision and flags, and hardware.
- Prompts, graders, and reference solutions are public, so contamination or task-specific adaptation cannot be excluded.
- OpenCode permissions are not an OS sandbox.
- Raw elapsed totals were omitted because these runs crossed providers and local hardware; they are not cross-provider speed comparisons.
- This project does not operate a secure leaderboard.

See [`../docs/METHODOLOGY.md`](../docs/METHODOLOGY.md) before interpreting or reproducing these results.
