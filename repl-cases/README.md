# Agentic REPL Cases

The benchmark agent receives only the selected case's `public/` tree. Public graders and reference overlays remain outside the copied workspace during a run. Canonical prompt text, difficulty, namespace, and timeout are defined in `../repl_cases.py`.

| Case | Difficulty | Primary debugging mechanism |
|---|---|---|
| `closed-order-stream` | medium | lazy realization after resource closure |
| `hot-reload-pricing` | hard | `defonce` state versus changed disk rules |
| `tenant-cache` | hard | history-dependent cache keys and nil caching |
| `webhook-event-fold` | hard | stale and duplicate event transitions |
| `payment-multimethod` | very-hard | live multimethod dispatch table |
| `route-registry-reload` | very-hard | macro-captured function versus Var root |
| `transducer-completion` | very-hard | reducing-function completion arity |
| `authorization-lazy-leak` | extremely-hard | deferred realization and authorization order |
| `dependency-planner` | extremely-hard | capability graph progression and diagnostics |
| `session-derived-index` | hard | persistent primary and derived atom state |

Each directory contains:

- `public/`: buggy source copied into the agent workspace
- `grader/grader.clj`: deterministic, publicly reproducible fresh-process grader
- `reference/`: known-good source overlay used only by validation
