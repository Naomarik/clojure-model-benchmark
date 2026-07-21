# Clojure Model Benchmark

An open, reproducible benchmark for measuring how language models write Clojure and how coding agents diagnose stateful Clojure failures through a live REPL.

The project deliberately reports two different capabilities:

- **One-shot correctness:** 33 independent prompts, each answered in a fresh OpenCode session and checked by a deterministic grader.
- **Agentic REPL debugging:** 10 buggy projects repaired in isolated temporary workspaces with a prestarted Babashka socket REPL. Correctness and REPL-use telemetry are reported separately.

This is an open benchmark. Prompts, graders, buggy fixtures, and reference solutions are public. It is useful for reproducible local experiments, not as a secure or contamination-resistant leaderboard.

## Development Snapshot

These are single-run exploratory observations from the pre-release development harness. The two score columns are not combined. REPL use is heuristic workflow telemetry, not a quality score. Two agentic prompts were clarified for the public release, so these historical scores must not be mixed with results from the current suite.

| Model route | One-shot | REPL correct | REPL use |
|---|---:|---:|---:|
| `ollama-cloud/deepseek-v4-flash` | 32/33 | 6/10 | 33/40 |
| `ollama-cloud/deepseek-v4-pro` | 33/33 | 6/10 | 34/40 |
| `zai-coding-plan/glm-5.2` | 33/33 | 6/10 | 33/40 |
| `openai/gpt-5.6-sol` | 32/33 | 8/10 | 35/40 |
| `ollama-cloud/kimi-k2.5` | 32/33 | 4/10 | 33/40 |
| `ollama-cloud/kimi-k2.6` | 32/33 | 7/10 | 30/40 |
| `ollama-cloud/minimax-m2.5` | 29/33 | 4/10 | 28/40 |
| `llama-cpp-qwen27/Qwen3.6-27B-Q4_K_M.gguf` | 29/33 | 7/10 | 33/40 |
| `llama-cpp-qwen/Qwen3.6-35B-A3B-Q4_K_M.gguf` | 23/33 | 6/10 | 26/40 |

See [`results/development-snapshot.md`](results/development-snapshot.md) for provenance and caveats. Elapsed measurements are intentionally omitted here: they include different providers, hardware, queues, rate limits, and timeout policies and are not cross-provider speed comparisons.

## Architecture

```text
model provider or llama.cpp
          |
          v
OpenCode noninteractive CLI
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
```

Do not mix artifacts with different suite hashes, harness revisions, model routes, or materially different inference settings.

## Outputs And Privacy

The runners write incremental artifacts under `artifacts/runs/` and `artifacts/repl-runs/`. These raw files can contain full prompts and responses, source diffs, grader output, temporary or personal paths, OpenCode session IDs, provider metadata, and logs. They are ignored by Git and should be reviewed as sensitive before sharing.

Generated `artifacts/tests.json`, matrices under `artifacts/`, and raw REPL logs are also ignored. Publish a manually reviewed aggregate under `results/` instead. A public result should include exact model identification and methodology but no credentials, personal paths, session IDs, raw provider payloads, or unreviewed model output.

## Interpretation

- Public graders and reference solutions make auditability possible but make contamination possible. Do not claim the benchmark is unseen.
- Current results are one run per route and do not estimate variance or statistical significance.
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
| `runner.py` | One-shot OpenCode runner |
| `suites/eval_clojure.py` | Bundled 33-task one-shot suite and graders |
| `matrix.py` | One-shot aggregate generator |
| `repl_runner.py` | Stateful REPL case runner and no-model smoke lifecycle |
| `repl_cases.py` | Agentic case metadata and prompts |
| `repl_eval.py` | Narrow socket-REPL client copied into case workspaces |
| `repl_matrix.py` | Agentic aggregate generator |
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
