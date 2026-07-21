# Clojure Model Benchmark Playbook

## Purpose

Compare remote models through OpenCode's noninteractive CLI using both the canonical one-shot Clojure suite and a separate stateful REPL-debugging suite.

The one-shot and agentic suites use different graders and are never combined into one score.

## Fairness Contract

- Canonical source: `suites/eval_clojure.py`
- Prompts and checker callables are imported directly; they are not rewritten.
- `artifacts/tests.json` snapshots every prompt and the canonical source SHA-256.
- Each task starts a new OpenCode session with the same benchmark agent.
- The benchmark agent has temperature 0, no tools, and only requests the prompt's exact output format.
- OpenCode runs with `--pure`, preventing external plugins from changing requests or responses.
- External OpenCode skills are explicitly disabled for benchmark processes.
- Raw OpenCode JSONL events, extracted response, checker detail, and elapsed time are retained for every task.
- If OpenCode's live JSONL omits finalized text for a reasoning model, the runner retrieves that same session with `opencode export` and records the fallback payload.
- Provider-side implementation details and nondeterminism remain outside this harness's control.

The local Qwen baseline used direct OpenAI-compatible API calls with a 2,048-token output cap. OpenCode does not expose an equivalent CLI output-cap flag. These tasks produce short answers, but this transport difference should be disclosed when comparing old local-Qwen artifacts to these runs.

## Pinned Models

Model aliases and exact provider IDs are in `models.json`.

### Local Servers

The project provider configuration expects the A3B server on port 8081 and the dense MTP server on port 8083. The managed launchers resolve `llama-server` from `LLAMA_SERVER_BIN` or `PATH`; model files are never assumed:

```bash
QWEN36_A3B_MODEL=/path/to/model.gguf bin/qwen36-a3b-server start
QWEN36_27B_MTP_MODEL=/path/to/model.gguf bin/qwen36-27b-mtp-server start
```

Set `QWEN36_A3B_MMPROJ` to add the optional A3B multimodal projector. Both launchers support `start`, `stop`, `restart`, `status`, and `logs`; runtime state uses `XDG_RUNTIME_DIR`, then `TMPDIR`.

## Run One Model

```bash
python runner.py --label deepseek-v4-pro --model ollama-cloud/deepseek-v4-pro
```

Use `--only TASK_NAME` for a smoke test. A run artifact is updated atomically after every task, so interrupted runs preserve completed results.
Use `--concurrency N` only when the serving configuration has at least N independent request slots.

## Run The Matrix

Run each pinned model with a unique label, then aggregate:

```bash
python matrix.py
```

Outputs:

- `artifacts/tests.json`: extracted canonical prompts and provenance
- `artifacts/runs/*.json`: complete per-model transcripts and grades
- `artifacts/matrix.json`: machine-readable comparison
- `artifacts/MATRIX.md`: human-readable overall and per-task matrix

## Verify

```bash
sha256sum suites/eval_clojure.py
python -m py_compile suites/eval_clojure.py runner.py matrix.py
python validate_new_cases.py
opencode models
```

The SHA-256 must match `canonical_suite_sha256` in every run artifact. If the canonical suite changes, rerun all models rather than mixing hashes.

## Agentic REPL Suite

The agentic suite contains exactly ten cases under `repl-cases/`. Each run receives a fresh copy of one `public/` fixture, a prestarted Babashka socket REPL on a random loopback port, and the project `repl-benchmark` agent with workspace read/search/edit and Bash restricted to `./repl-eval`. The prompt limits edits to `src/**`; fresh grading considers source behavior only. The public grader and reference overlay are not copied into the agent workspace.

The runner retains the REPL's stdin, starts it in a new process group, and terminates that group in `finally`. Grader tests execute only after the REPL and OpenCode process finish, using a new Babashka process. External network tools and external-directory access are denied by the agent configuration, but this is a practical permission boundary rather than an OS sandbox.

Run one case:

```bash
python repl_runner.py \
  --case tenant-cache \
  --model openai/gpt-5.6-sol \
  --label gpt-5.6-sol-tenant-cache
```

Run all ten cases:

```bash
python repl_runner.py \
  --all \
  --model openai/gpt-5.6-sol \
  --label gpt-5.6-sol-repl
```

Run a no-model lifecycle smoke test with known-good references:

```bash
python repl_runner.py --case tenant-cache --smoke
```

Validate every fixture and reference:

```bash
python validate_repl_cases.py
```

Generate the separate agentic matrix:

```bash
python repl_matrix.py
```

Agentic outputs:

- `artifacts/repl-runs/*.json`: incremental per-label results
- `artifacts/repl-matrix.json`: machine-readable agentic matrix
- `artifacts/REPL_MATRIX.md`: correctness and REPL-use columns

### REPL Telemetry

Agents evaluate forms with:

```bash
./repl-eval '(bench.tenant-cache/lookup loader :a 1 "p1")'
```

The runner-owned log records the form, response, elapsed time, and current source-tree hash. REPL use is scored separately on four signals: connection, project evaluation, diagnostic evaluation, and project evaluation after a source change. A trivial arithmetic probe earns only the connection signal and is not meaningful project use.

### Fairness Notes

- Every case starts from the same immutable public fixture copy.
- Every model gets a fresh OpenCode session and REPL process per case.
- Prompts, timeouts, graders, and reference overlays are versioned with the harness.
- Grading uses source files in a fresh process; REPL-only `intern`, atom mutation, or `alter-var-root` changes cannot satisfy grader tests.
- Results preserve raw OpenCode JSONL, assistant text, grader output, REPL evaluations, source hashes, timing, and server logs.
- Correctness and REPL use remain separate; neither is merged with the one-shot matrix.
