# Clojure Model Benchmark

An open, reproducible benchmark for measuring how language models write Clojure and how coding agents diagnose stateful Clojure failures through a live REPL.

The project deliberately reports two different capabilities:

- **One-shot correctness:** 33 independent prompts, each answered in a fresh noninteractive agent session and checked by a deterministic grader.
- **Agentic REPL debugging:** 10 buggy projects repaired in isolated temporary workspaces with a prestarted Babashka socket REPL. Correctness and REPL-use telemetry are reported separately.

This is an open benchmark. Prompts, graders, buggy fixtures, and reference solutions are public. It is useful for reproducible local experiments, not as a secure or contamination-resistant leaderboard.

## Development Snapshot

These are single-run exploratory observations from the pre-release development harness. This table contains correctness results only. Component correctness remains primary; `Weighted overall` is a secondary correctness-only score.

| Model route | One-shot correct | One-shot weighted | Agentic correct | Agentic weighted | Weighted overall |
|---|---:|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | 32/33 | 76/79 | 8/10 | 38/46 | **89.4**† |
| `ollama-cloud/kimi-k2.6` | 32/33 | 77/79 | 7/10 | 33/46 | **84.6**† |
| `ollama-cloud/deepseek-v4-pro` | 33/33 | 79/79 | 6/10 | 28/46 | **80.4** |
| `zai-coding-plan/glm-5.2` | 33/33 | 79/79 | 6/10 | 28/46 | **80.4** |
| `llama-cpp-qwen27/Qwen3.6-27B-Q4_K_M.gguf` | 29/33 | 67/79 | 7/10 | 33/46 | **78.3** |
| `ollama-cloud/deepseek-v4-flash` | 32/33 | 75/79 | 6/10 | 28/46 | **77.9** |
| `ollama-cloud/kimi-k2.5` | 32/33 | 76/79 | 4/10 | 18/46 | **67.7** |
| `ollama-cloud/minimax-m2.5` | 29/33 | 66/79 | 4/10 | 18/46 | **61.3** |
| `llama-cpp-qwen/Qwen3.6-35B-A3B-Q4_K_M.gguf` | 23/33 | 48/79 | 6/10 | 28/46 | **60.8** |

The overall formula is `100 * (0.5 * one-shot-weighted/79 + 0.5 * REPL-weighted/46)`. Task weights range from 1 to 5 and are assigned from semantic breadth, state/effects, runtime lifecycle, edge cases, and interacting behavior. See [`docs/WEIGHTING.md`](docs/WEIGHTING.md) and the machine-readable [`weights.json`](weights.json).

Every row is historical because two REPL prompts were clarified for the public release and these artifacts predate protocol fingerprints. † GPT-5.6 Sol and Kimi K2.6 also each contain one null-response infrastructure failure counted as false in this retrospective calculation. Complete current-treatment reruns are required before treating any row as a current result. The v1 weights were assigned retrospectively after these results existed, not preregistered.

**Run observations (not correctness scores).** `REPL workflow signals` is a diagnostic telemetry count, not tests passed: each of the 10 agentic cases records connection, project evaluation, diagnostic evaluation, and project evaluation after a source change. It does not enter the weighted overall score.

| Model route | One-shot wall time | Agentic wall time | Agentic timeouts | REPL workflow signals |
|---|---:|---:|---:|---:|
| `openai/gpt-5.6-sol` | 2m 51s | 14m 02s | 0 | 35/40 |
| `ollama-cloud/kimi-k2.6` | 10m 57s | 29m 03s | 0 | 30/40 |
| `ollama-cloud/deepseek-v4-pro` | 7m 58s | 32m 36s | 0 | 34/40 |
| `zai-coding-plan/glm-5.2` | 8m 21s | 52m 33s | 0 | 33/40 |
| `llama-cpp-qwen27/Qwen3.6-27B-Q4_K_M.gguf` | 17m 08s | 48m 17s | 0 | 33/40 |
| `ollama-cloud/deepseek-v4-flash` | 7m 11s | 16m 07s | 0 | 33/40 |
| `ollama-cloud/kimi-k2.5` | 10m 33s | 25m 40s | 0 | 33/40 |
| `ollama-cloud/minimax-m2.5` | 8m 02s | 66m 22s | 6 | 28/40 |
| `llama-cpp-qwen/Qwen3.6-35B-A3B-Q4_K_M.gguf` | 6m 22s | 38m 30s | 3 | 26/40 |

Elapsed values are recorded end-to-end wall time summed across tasks. They include provider latency, queueing, generation, tool use, process startup, local hardware, and timeouts, so they describe these runs but are not controlled cross-provider speed comparisons. Exact seconds and per-task/per-case values are preserved in [`artifacts/matrix.json`](artifacts/matrix.json) and [`artifacts/repl-matrix.json`](artifacts/repl-matrix.json).

The local Qwen routes ran through a ROCm/HIP `llama.cpp` build on an AMD Ryzen AI Max+ 395 with Radeon 8060S (`gfx1151`, 40 GPU compute units) and 128 GB-class unified memory (121 GiB visible to Linux). The local server used full GPU offload, flash attention, four slots, and thinking disabled; the dense 27B route used MTP speculative decoding and the 35B-A3B route used n-gram speculation. The benchmark machine is configured with the ACPI `performance` platform profile, `performance` CPU governor, and active AMD P-state. The current documented `llama.cpp` build is `9671` (`c1304d7b28e1`); historical artifacts do not fingerprint the machine power state or server revision.

### Claude Models (Claude Code transport)

Single-run results on the current public suite via Claude Code's noninteractive CLI (`--transport claude`), all at `--effort low`, the minimum reasoning setting (see [`CLAUDE.md`](CLAUDE.md) and [`docs/CLAUDE_TRANSPORT.md`](docs/CLAUDE_TRANSPORT.md)). These runs use a different harness and the clarified public agentic prompts, so they are not directly comparable to the OpenCode development snapshot above. The table contains correctness results only.

| Model | Effort | One-shot correct | One-shot weighted | Agentic correct | Agentic weighted | Weighted overall |
|---|---|---:|---:|---:|---:|---:|
| `claude-fable-5` | low | 33/33 | 79/79 | 7/10 | 33/46 | **85.9** |
| `claude-opus-4-8` | low | 33/33 | 79/79 | 7/10 | 33/46 | **85.9** |
| `claude-sonnet-5` | low | 32/33 | 76/79 | 7/10 | 33/46 | **84.0** |
| `claude-haiku-4-5` | low | 32/33 | 76/79 | 7/10 | 33/46 | **84.0** |

**Run observations (not correctness scores).** Wall time has the same end-to-end meaning and limitations described above.

| Model | One-shot wall time | Agentic wall time | Agentic timeouts | REPL workflow signals |
|---|---:|---:|---:|---:|
| `claude-fable-5` | 2m 02s | 4m 42s | 0 | 36/40 |
| `claude-opus-4-8` | 1m 57s | 5m 33s | 0 | 37/40 |
| `claude-sonnet-5` | 1m 56s | 6m 44s | 0 | 20/40 |
| `claude-haiku-4-5` | 8m 21s | 24m 53s | 0 | 34/40 |

Exact Claude timings are preserved per task and case in the corresponding [`artifacts/runs/`](artifacts/runs/) and [`artifacts/repl-runs/`](artifacts/repl-runs/) JSON files.

These artifacts match the current suite and protocol fingerprints and contain no infrastructure-invalid cases. The v1 weighting policy itself remains retrospective and not preregistered.

See [`results/development-snapshot.md`](results/development-snapshot.md) for provenance and caveats.

## What The Benchmark Runs

**One-shot suite (33 tasks, defined in [`suites/eval_clojure.py`](suites/eval_clojure.py)).** Each task is a single prompt answered with no tools, checked deterministically by executing the response with Babashka or comparing it structurally as EDN. The tasks are drawn from real Clojure/ClojureScript web-application patterns — reitit routes, hiccup components, malli schemas, HoneySQL query maps, Ring handlers, Datomic-style pull results, and i18n/data utilities:

| Category | Count | What it exercises |
|---|---:|---|
| Function writing (`fn_*`) | 6 | Small idiomatic utilities: nil-safe normalization, recursive map cleaning, vector splicing, relative-time formatting |
| Harder multi-step functions (`hard_*`) | 13 | Auth handlers with ownership checks, conditional HoneySQL builders, join-row nesting, transducer-friendly `reduce`/`reduced`, deep merge, laziness-safe effects |
| Bug fixes (`fix_*`) | 4 | Spot and repair a planted bug: wrong `select-keys` direction, unguarded `update`, lazy `map` side effects, `->` vs `->>` |
| Data-structure emission (`ds_*`) | 3 | Emit exact HoneySQL, hiccup, and malli EDN shapes |
| EDN/JSON transformation (`edn_*`, `json_*`) | 3 | Aggregate entity vectors, convert JSON config to EDN, extract route names |
| Strict-format answers (`strict_*`) | 2 | Lint diagnosis and exact Ring response maps with nothing but the answer |
| Context-augmented variants (`ctx_*`) | 2 | The same checkers as two base tasks, with representative project source prepended as context |

**Agentic REPL suite (10 cases, defined in [`repl_cases.py`](repl_cases.py) with fixtures in [`repl-cases/`](repl-cases/)).** Each case is a small buggy project copied into a temporary workspace with a live Babashka socket REPL. The model must diagnose stateful runtime behavior, edit `src`, reload, and verify; a fresh-process grader then decides correctness. The cases target Clojure-specific runtime semantics: lazy realization after resource closure, `defonce` state vs. changed disk rules, history-dependent cache contamination, idempotent event folding, live multimethod dispatch tables, macro-captured functions vs. Var roots, transducer completion arity, authorization-before-realization ordering, capability-graph planning, and primary-vs-derived atom state. Difficulty ranges from medium to extremely-hard; the full case table is in [`repl-cases/README.md`](repl-cases/README.md).

## Architecture

```text
model provider or llama.cpp
          |
          v
OpenCode or Claude Code CLI
     |                |
     v                v
33 one-shot tasks   10 temporary project copies
deterministic       Babashka socket REPL + agent edits
response graders    fresh-process public grader
     |                |
     v                v
raw local artifacts -> separate matrix generators
```

The one-shot agent has tools disabled. The REPL agent can inspect and edit its copied workspace and can invoke only the runner-provided `./repl-eval` command through its OpenCode Bash permission. Those permissions are **not an OS sandbox**. Run models and providers you trust on a machine appropriate for executing generated code.

## Prerequisites

- Linux
- Python 3.11 or newer; the harness uses only the standard library
- [Babashka](https://babashka.org/) 1.12.218 or newer
- [OpenCode](https://opencode.ai/) 1.15.12 or newer
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 2.1.216 or newer for optional Claude transport runs
- [llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-server` for local GGUF models
- Provider credentials configured in OpenCode for cloud runs

Check the tools:

```bash
python3 --version
bb --version
opencode --version
llama-server --version
```

## Quick Start

No Python package installation is needed:

```bash
python3 validate_new_cases.py
python3 validate_repl_cases.py
python3 repl_runner.py --case tenant-cache --smoke
```

The validators and smoke mode do not call a model. To run a model already configured in OpenCode:

```bash
python3 runner.py \
  --model openai/gpt-5.6-sol \
  --label gpt-5.6-sol

python3 repl_runner.py \
  --all \
  --model openai/gpt-5.6-sol \
  --label gpt-5.6-sol-repl
```

Model runs may incur provider charges.

## Local Models

Model files are not included. Start each OpenAI-compatible llama.cpp endpoint in a separate terminal. Environment variables keep machine-specific paths out of tracked configuration:

```bash
export LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-llama-server}"
export QWEN36_27B_MTP_MODEL="/path/to/Qwen3.6-27B-Q4_K_M.gguf"
export QWEN36_A3B_MODEL="/path/to/Qwen3.6-35B-A3B-Q4_K_M.gguf"
```

Use the managed repository launchers. They support `start`, `stop`, `restart`, `status`, and `logs`, store runtime files outside the repository, and wait for readiness. The OpenCode provider configuration expects the 35B-A3B endpoint on `localhost:8081` and the dense 27B endpoint on `localhost:8083`:

```bash
bin/qwen36-a3b-server start
bin/qwen36-27b-mtp-server start
bin/qwen36-27b-mtp-server status
```

The launchers also accept model-specific `*_HOST`, `*_PORT`, `*_SLOTS`, `*_CTX`, and thinking-related environment variables shown in each script's usage text. If a port changes, update `.opencode/opencode.json` to match.

Confirm the model route before spending a full run:

```bash
opencode models
python3 runner.py \
  --model llama-cpp-qwen27/Qwen3.6-27B-Q4_K_M.gguf \
  --label local-qwen27-smoke \
  --only fn_pluralize
```

Local results depend on the exact GGUF, llama.cpp build, launch flags, prompt transport, and hardware. Record those details alongside any published aggregate.

## Cloud Models

Authenticate providers through OpenCode, not through files committed to this repository. Follow the [OpenCode provider documentation](https://opencode.ai/docs/providers/), then verify the exact route:

```bash
opencode auth login
opencode models
```

Pass the complete `provider/model` ID shown by OpenCode to `--model`. `models.json` records the routes used for the development snapshot; availability and model aliases can change upstream.

## Commands

Run one-shot tasks:

```bash
python3 runner.py --model PROVIDER/MODEL --label LABEL
python3 runner.py --model PROVIDER/MODEL --label LABEL --only TASK_NAME
python3 runner.py --model PROVIDER/MODEL --label LABEL --concurrency 2
```

Run agentic cases:

```bash
python3 repl_runner.py --case tenant-cache --model PROVIDER/MODEL --label LABEL
python3 repl_runner.py --all --model PROVIDER/MODEL --label LABEL
python3 repl_runner.py --all --smoke
```

Validate the public suites:

```bash
python3 validate_new_cases.py
python3 validate_repl_cases.py
```

Generate matrices from local raw runs:

```bash
python3 matrix.py
python3 repl_matrix.py
python3 overall_matrix.py
```

Validate the weighting manifest without model artifacts:

```bash
python3 overall_matrix.py --validate
```

Do not mix artifacts with different suite or protocol hashes, harness revisions, model routes, or materially different inference settings.

## Outputs And Privacy

The runners write incremental artifacts under `artifacts/runs/` and `artifacts/repl-runs/`. These raw files can contain full prompts and responses, source diffs, grader output, temporary or personal paths, OpenCode session IDs, provider metadata, and logs. They are ignored by Git and should be reviewed as sensitive before sharing.

Generated `artifacts/tests.json`, matrices under `artifacts/`, and raw REPL logs are also ignored. Publish a manually reviewed aggregate under `results/` instead. A public result should include exact model identification and methodology but no credentials, personal paths, session IDs, raw provider payloads, or unreviewed model output.

## Interpretation

- Public graders and reference solutions make auditability possible but make contamination possible. Do not claim the benchmark is unseen.
- Current results are one run per route and do not estimate variance or statistical significance.
- The weighted overall is a secondary 50/50 policy choice, not an empirical claim that the two suites are interchangeable.
- The initial v1 weights were assigned retrospectively and are not preregistered; future weights must be frozen through blind review before scored runs are inspected.
- A pass means the public deterministic checker accepted the answer or final source. It does not prove general Clojure competence.
- REPL-use points indicate connection, project evaluation, diagnostic-looking evaluation, and post-edit evaluation. The signal is heuristic and can be gamed or earned without a correct repair.
- OpenCode permissions reduce accidental access but do not isolate generated code at the operating-system level.
- Provider-side model revisions, routing, nondeterminism, outages, and policy behavior are outside the harness's control.
- Elapsed totals include end-to-end orchestration and cannot support fair cross-provider speed claims.
- Different quantization, inference flags, context limits, and hardware can materially affect local observations.
- There is no secure submission service or secure leaderboard.

More detail is in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Project Layout

| Path | Purpose |
|---|---|
| `runner.py` | One-shot OpenCode and Claude Code runner |
| `suites/eval_clojure.py` | Bundled 33-task one-shot suite and graders |
| `matrix.py` | One-shot aggregate generator |
| `repl_runner.py` | Stateful REPL case runner and no-model smoke lifecycle |
| `repl_cases.py` | Agentic case metadata and prompts |
| `repl_eval.py` | Narrow socket-REPL client copied into case workspaces |
| `repl_matrix.py` | Agentic aggregate generator |
| `overall_matrix.py` | Strict weighted correctness aggregate generator |
| `weights.json` | Versioned task weights, rubric vectors, and suite hashes |
| `validate_new_cases.py` | One-shot grader/reference validator |
| `validate_repl_cases.py` | Buggy-fixture and reference validator |
| `repl-cases/` | Public fixtures, graders, and reference solutions |
| `.opencode/agent/` | Fixed benchmark agent definitions |
| `bin/` | Local llama.cpp server lifecycle scripts |
| `models.json` | Development-snapshot model routes |
| `results/` | Sanitized, reviewable published aggregates |
| `docs/` | Methodology and case-authoring guides |

## Contributing

Contributions are welcome under [`CONTRIBUTING.md`](CONTRIBUTING.md). By participating, you agree to the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). The benchmark code and fixtures are MIT licensed; model weights and external tools are not distributed by this project.
