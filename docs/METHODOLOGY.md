# Methodology

## Scope

Clojure Model Benchmark measures two related but distinct behaviors: producing a correct answer to a self-contained Clojure prompt and repairing a small stateful Clojure project with access to a live REPL. It does not produce a combined overall score.

All prompts, graders, fixtures, and references are public. This favors auditability and local reproducibility over secrecy. It also means results cannot establish that a model has never seen benchmark material.

## One-Shot Correctness

The one-shot suite has 33 tasks spanning functions, data structures, EDN-shaped output, strict formatting, library idioms, and bug fixes. Each task consists of a name, prompt, and deterministic Python checker.

For each task, the runner:

1. Starts a fresh `opencode run --pure` session using the fixed `benchmark` agent.
2. Disables agent tools and requests temperature zero through the agent configuration.
3. Extracts assistant text from OpenCode's JSONL stream, using an export of the same session as a fallback when necessary.
4. Passes the text to the task checker.
5. Records the pass/fail result, checker detail, elapsed wall time, response, and raw OpenCode events locally.

The primary metric is accepted tasks out of 33. Temperature zero does not guarantee deterministic behavior across providers. Concurrency should be disclosed because provider queues and rate limits can influence failures and elapsed time.

## Agentic REPL Debugging

The agentic suite has 10 cases. Each contains a buggy `public/` project, a grader, and a known-good `reference/` overlay. For each case, the runner:

1. Copies only the public fixture and fixed agent definition into a new temporary workspace.
2. Starts a Babashka socket REPL on a random loopback port and runs case bootstrap code.
3. Gives the model a prompt, source inspection/edit tools, and the runner-owned `./repl-eval` client.
4. Restricts OpenCode's Bash permission to that client and asks the model to diagnose, edit `src/**`, reload, and verify.
5. Stops the OpenCode and REPL process groups.
6. Runs the public grader in a fresh Babashka process against the resulting source.
7. Records correctness, source changes, REPL events, and orchestration output locally.

The reference solution and grader are not copied into the model's temporary workspace, but both are public in the repository. This is an evaluation protocol, not a secrecy claim.

### Correctness

Each case receives one correctness point when its fresh-process grader exits successfully. Correctness is therefore reported as a count out of 10. Fresh-process grading prevents REPL-only mutation from substituting for a source repair.

### REPL-Use Telemetry

Each case can receive one heuristic point for each of four observed signals:

- any successful use of the REPL client;
- evaluation mentioning the case's project namespace beyond a plain `require`;
- a project evaluation containing a diagnostic token such as `meta`, `source`, `methods`, `macroexpand`, dereference, `class`, or `type`;
- project evaluation after the source-tree hash changes.

The maximum is 40 across 10 cases. This telemetry describes a rough workflow shape. It does not establish that an evaluation was useful, causally related to the repair, idiomatic, safe, or correct. The heuristic can miss meaningful work and can be gamed. Never merge it with correctness.

## Validation

`validate_new_cases.py` applies known-good answers to the one-shot checkers. `validate_repl_cases.py` establishes that each public REPL fixture loads, fails its grader before repair, and passes after applying the reference overlay. `repl_runner.py --all --smoke` exercises socket startup, bootstrap, reference reload through the client, shutdown, and grading without calling a model.

Validation establishes internal fixture consistency, not absence of grader bugs or overfitting. Human review should consider alternative valid implementations and unintended shortcuts.

## Reproducibility Record

A useful result record includes:

- benchmark version or source revision and suite hash;
- exact OpenCode version and model route;
- provider-visible model version when available;
- local model filename/hash, quantization, llama.cpp revision, and launch flags;
- Python and Babashka versions;
- hardware and operating system for local inference;
- timeouts, concurrency, context/output limits, and run count;
- date and any observed provider incidents or retries.

Do not aggregate runs from different suite hashes. Report repeated runs individually or with a documented summary statistic rather than silently selecting the best run.

## Timing

Elapsed values are end-to-end wall-clock observations that include provider latency, queueing, generation, tool use, process startup, local hardware, retries, and timeouts. They may help diagnose one setup. They are not valid cross-provider speed comparisons.

## Safety And Privacy

OpenCode permissions, temporary directories, loopback sockets, and command allowlists reduce accidental scope but do not form an OS sandbox. The benchmark executes generated code. Use host-level isolation for untrusted models or providers.

Raw artifacts can contain assistant output, prompts, source diffs, grader diagnostics, temporary and personal paths, session IDs, logs, and provider metadata. Keep them local by default. Public results should be manually sanitized aggregates with no credentials, identifiers, personal paths, or unreviewed raw text.

## Limitations

- Public benchmark content is susceptible to training-data and prompt contamination.
- Ten agentic projects and 33 short tasks cover only a small part of Clojure engineering.
- Deterministic graders can reject valid answers or accept unintended ones.
- A single run does not estimate variance.
- Hosted aliases may change model implementations without notice.
- Local quantization and inference configuration can affect outcomes.
- The fixed OpenCode agent and permission policy are part of the benchmark treatment.
- There is no secure submission environment, hidden test service, or secure leaderboard.
