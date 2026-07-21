# Contributing

Thank you for helping improve Clojure Model Benchmark. Contributions may include fixtures, graders, harness portability, documentation, and independently reproduced results.

## Before Opening A Change

- Discuss large suite or scoring changes in an issue first.
- Keep one-shot and agentic REPL component scores separately reported. Never fold REPL-use telemetry into correctness or the secondary overall.
- Do not add secrets, model weights, raw provider output, session IDs, personal paths, or unreviewed run artifacts.
- Disclose generated or model-assisted contributions when that context helps reviewers evaluate provenance.
- Confirm that contributed fixtures and text may be released under the MIT License.

## Development

Python 3.11+ and Babashka 1.12.218+ are required. The runtime is standard-library only. Optional lint tooling can be installed with:

```bash
python3 -m pip install -e '.[dev]'
```

Before submitting:

```bash
python3 -m py_compile *.py suites/eval_clojure.py
python3 validate_new_cases.py
python3 validate_repl_cases.py
python3 repl_runner.py --all --smoke
python3 overall_matrix.py --validate
ruff check .
```

No model or paid provider is needed for these checks.

## Benchmark Changes

Follow [`docs/ADDING_CASES.md`](docs/ADDING_CASES.md). Every case must have deterministic grading, a known-bad starting point, and a known-good public reference. Prefer a focused semantic failure over broad application scaffolding.

A benchmark-changing pull request should explain:

- the behavior being measured;
- why the grader accepts correct alternatives and rejects the intended bug;
- any likely shortcuts or contamination risks;
- whether existing results become incomparable and require a new version.

Do not include new model scores in the same change that alters prompts, graders, permissions, or fixtures unless they are clearly marked as post-change exploratory runs.

Every added or behaviorally changed case must be reviewed under [`docs/WEIGHTING.md`](docs/WEIGHTING.md). For future changes, two reviewers assign the five intrinsic-demand dimensions without viewing model results. Update `weights.json`, expected suite and protocol hashes, totals, metric-definition digest, and the full documentation table in the same change. If scoring changes, bump the metric version and add its known digest mapping to `overall_matrix.py`. Prompt clarifications, grader acceptance changes, fixture behavior changes, and runtime-policy changes require the reruns described by the weighting change rules. Do not use pass rates, model identities, existing filename difficulty labels, or desired rankings to choose a weight.

## Results

Only submit sanitized aggregates under `results/`. Include model route/version, quantization where applicable, harness revision, suite and protocol hashes, inference settings, run count, and date. Never describe elapsed totals as cross-provider speed comparisons.

Generate local weighted matrices with `python3 overall_matrix.py`. The generator matches exact model routes and rejects mismatched suite or protocol treatments and infrastructure-invalid runs. Its allow flags are reserved for clearly labeled retrospective development analyses and must not be used to present historical artifacts as current results.

## Pull Requests

Keep changes small and explain behavioral effects. CI must pass. By contributing, you agree to follow the project Code of Conduct.
