# Contributing

Thank you for helping improve Clojure Model Benchmark. Contributions may include fixtures, graders, harness portability, documentation, and independently reproduced results.

## Before Opening A Change

- Discuss large suite or scoring changes in an issue first.
- Keep one-shot correctness and agentic REPL metrics separate.
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

## Results

Only submit sanitized aggregates under `results/`. Include model route/version, quantization where applicable, harness revision, suite hashes, inference settings, run count, and date. Never describe elapsed totals as cross-provider speed comparisons.

## Pull Requests

Keep changes small and explain behavioral effects. CI must pass. By contributing, you agree to follow the project Code of Conduct.
