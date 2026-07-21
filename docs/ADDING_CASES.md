# Adding Cases

Benchmark cases are public and must remain deterministic, auditable, focused, and inexpensive to validate without a model.

## General Rules

- Measure one clear capability or failure mode.
- Avoid external network access, wall-clock dependence, randomness, locale dependence, and machine-specific paths.
- Accept semantically valid alternatives instead of matching one reference string where practical.
- Add a known-good reference and prove the intended starting point fails.
- Keep prompts, graders, fixtures, and references free of secrets and incompatible third-party material.
- Treat any prompt, grader, fixture, agent permission, or scoring change as benchmark-significant.

## One-Shot Tasks

One-shot tasks live in the canonical suite module used by `runner.py`. Add a `(name, prompt, checker)` entry and a known-good answer to `validate_new_cases.py`.

The checker should return `(passed: bool, detail: str)`. It should:

- parse only the format requested by the prompt;
- reject commentary when the task requests code or data only;
- test boundary cases relevant to the stated behavior;
- avoid relying on formatting that is not part of the task;
- provide concise diagnostics that do not expose private data.

Run:

```bash
python3 validate_new_cases.py
python3 runner.py --model PROVIDER/MODEL --label case-smoke --only TASK_NAME
```

The second command calls a model and may cost money. Existing result matrices are not comparable after the suite changes unless the version and suite hash distinguish them.

## Agentic REPL Cases

Create this structure:

```text
repl-cases/CASE-SLUG/
  public/
    src/...
    resources/...       # optional
  grader/
    grader.clj
  reference/
    src/...
    resources/...       # optional
```

The public `grader/` is withheld only from the temporary model workspace during a run.

Add one `ReplCase` to `repl_cases.py` with a unique slug, difficulty label, namespace, bootstrap form, timeout, prompt, and optional post-bootstrap resource mutation. The prompt should describe observable requirements without prescribing the implementation. The public fixture should load successfully but fail the grader for the intended reason.

The grader runs in a fresh Babashka process with `src:resources` on the classpath. It should test final source behavior, complete quickly, avoid the network, and not depend on state left in the agent's REPL. The reference overlay should be a minimal known-good implementation, not an extra test-specific bypass.

Run all model-free checks:

```bash
python3 validate_repl_cases.py
python3 repl_runner.py --case CASE-SLUG --smoke
python3 repl_runner.py --all --smoke
```

Review the case for shortcuts through file names, prompt wording, grader assumptions, persistent global state, lazy realization, and accidental access outside `src/**`. Remember that OpenCode permissions are not an OS sandbox.

## Review Checklist

- The public fixture loads and deterministically fails.
- The reference deterministically passes in a fresh process.
- Plausible alternative repairs pass.
- Superficial or REPL-only workarounds fail.
- The case works from any repository path.
- No private path, credential, generated package, raw model output, or session identifier is present.
- Documentation describes any new metric or changed interpretation.
- Existing published results are marked incomparable when appropriate.
