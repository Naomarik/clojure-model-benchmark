# Correctness Weighting

## Purpose

Clojure Model Benchmark reports one-shot correctness and agentic REPL correctness as its
primary component metrics. It also defines a secondary weighted overall score for a compact
summary across the two capabilities.

The overall score contains binary grader correctness only. It never includes REPL-use
telemetry, elapsed time, token counts, cost, or any other workflow or efficiency signal.

The canonical machine-readable definition is [`../weights.json`](../weights.json). The
manifest freezes the metric version, rubric version, scoring-definition digest, current suite
and protocol hashes, dimension vectors, integer weights, rationales, and normalization shares.

## Intrinsic-Demand Rubric

Each task is scored from 0 to 2 on five dimensions. Reviewers assess the effective contract
formed by the prompt, public fixture, and public grader. Prompt length, source length, filename
difficulty labels, model names, observed pass rates, current rankings, time, tokens, and cost
must not influence a rating.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Semantic breadth | One direct representation or domain | Translation or coordination across two representations or concepts | Three or more concepts, or substantial domain-specific semantics |
| State/effect reasoning | Pure value computation | One state, presence, or effect invariant | Ordering, exactly-once behavior, atomicity, idempotence, falsey caching, or multiple state invariants |
| Lifecycle/runtime reasoning | No runtime lifecycle concern | One concern such as laziness, dynamic binding, protocols, resources, Vars, or reload | Multiple phases or a boundary interaction such as laziness plus resource closure or Var roots plus reload |
| Compositional edge cases | Happy path only | One distinct edge family | Two or more independently enforced edge families requiring different handling |
| Interacting behavior | Literal or direct operation | Two coordinated transforms or branches | Three or more stages or branches, recursion, iteration, or cross-component invariants |

For a task with dimension scores `S`, `E`, `L`, `C`, and `I`, calculate:

```text
D = S + E + L + C + I
```

Convert the 0-10 rubric total to a compact integer weight:

| Rubric total | Weight |
|---:|---:|
| 0-1 | 1 |
| 2-3 | 2 |
| 4-5 | 3 |
| 6-7 | 4 |
| 8-10 | 5 |

The thresholds are fixed in the manifest. Tasks with equal totals intentionally tie and receive
the same weight. There is no forced ranking or target weight distribution.

## Formula

Let `p(m,t)` be 1 when model route `m` passed task `t` according to its deterministic grader
and 0 otherwise. Let `w(t)` be the manifest weight.

```text
one_shot_rate(m) = sum(w(t) * p(m,t), one-shot t) / 79
repl_rate(m)     = sum(w(t) * p(m,t), REPL t) / 46

overall(m) = 100 * (0.5 * one_shot_rate(m) + 0.5 * repl_rate(m))
```

The direct raw diagnostic is also available:

```text
direct_raw(m) = (one_shot_points(m) + repl_points(m)) / 125
```

Direct raw is not the recommended overall because it gives one-shot 79/125 = 63.2% of the
result and REPL 46/125 = 36.8%. Those shares arise from task count and authoring granularity,
not from a benchmark-design claim that one capability is more important.

The normalized overall gives each separately designed suite 50 points. This prevents adding or
splitting cases in one suite from silently changing that suite's importance. It does not attempt
to remove conceptual overlap within a suite.

## One-Shot Weights

Vectors are `[semantic breadth, state/effect, lifecycle/runtime, compositional edges,
interacting behavior]`.

| Task | Vector | Weight | Rationale |
|---|---:|---:|---|
| `fn_remove_empty_vals` | `[1,0,0,2,2]` | 3 | Recursive cleaning, post-recursion emptiness, and preservation of false and zero interact. |
| `fn_vec_insert` | `[1,0,0,1,1]` | 2 | Converts arbitrary sequential input and coordinates prefix, item, and suffix splicing. |
| `fn_pluralize` | `[0,0,0,1,0]` | 1 | One direct equality branch with one negative case family. |
| `fn_ago_str` | `[1,0,0,2,2]` | 3 | An ordered threshold ladder coordinates four derived units and multiple boundaries. |
| `fn_keywordize_path` | `[1,0,0,1,1]` | 2 | Handles keyword versus collection input and transforms names into a dotted keyword. |
| `fn_normalize_email` | `[0,0,0,1,1]` | 2 | Nil propagation must compose with trimming and lowercasing. |
| `ds_honeysql_select` | `[1,0,0,0,1]` | 2 | Translates SQL intent into several coordinated HoneySQL EDN clauses. |
| `ds_hiccup_card` | `[1,0,0,0,1]` | 2 | Translates a nested UI description into exact hiccup structure. |
| `ds_malli_user_schema` | `[1,0,0,1,1]` | 2 | Coordinates Malli entry syntax, exact order, and optional-property placement. |
| `fix_submap` | `[0,0,0,1,1]` | 2 | Corrects map and key direction while retaining map guards. |
| `fix_update_if_exists` | `[0,0,0,1,0]` | 1 | A single presence guard surrounds an otherwise direct update. |
| `edn_status_counts` | `[0,0,0,0,1]` | 1 | Direct aggregation from status values to counts. |
| `json_config_to_edn` | `[1,0,0,0,0]` | 1 | Direct representation conversion with no behavioral interaction. |
| `strict_unused_binding` | `[0,0,0,0,0]` | 1 | Direct static identification of one unused local. |
| `strict_ring_response_edn` | `[1,0,0,0,0]` | 1 | Direct translation to a specified Ring response map. |
| `edn_route_names` | `[0,0,0,0,1]` | 1 | Extracts and sorts one field from a supplied literal route tree. |
| `ctx_remove_empty_vals` | `[1,0,0,2,2]` | 3 | Uses the same recursive contract as `fn_remove_empty_vals`; examples do not add weight. |
| `ctx_malli_user_schema` | `[1,0,0,1,1]` | 2 | Uses the same schema contract as `ds_malli_user_schema`; examples do not add weight. |
| `hard_require_auth_handler` | `[1,0,0,2,2]` | 3 | Coordinates authentication, lookup, ownership, non-disclosure, and ordered responses. |
| `hard_paginated_query` | `[2,1,0,2,2]` | 4 | Combines query construction, paging, optional filters, false presence, and absent `:where`. |
| `hard_nest_join_rows` | `[1,0,0,2,2]` | 3 | Groups flat joins, handles nil offers, nests entities, and sorts both levels. |
| `hard_hiccup_status_table` | `[1,0,0,1,2]` | 3 | Coordinates nested hiccup, conditional classes, conversions, order, and empty input. |
| `hard_day_buckets` | `[1,0,0,1,1]` | 2 | Combines integer bucket arithmetic, counting, sorted output, and empty input. |
| `hard_flatten_dict` | `[1,0,0,1,2]` | 3 | Recursive arbitrary-depth traversal accumulates and encodes paths into keys. |
| `hard_apply_user_patch` | `[0,1,0,2,1]` | 3 | Whitelisting distinguishes absence from explicit nil and false while preserving state. |
| `hard_reitit_path_by_name` | `[1,0,0,1,2]` | 3 | Recursive first-match search coordinates ancestor paths and absent results. |
| `hard_honeysql_boolean_tree` | `[2,0,0,1,2]` | 3 | Requires an exact nested Boolean query shape plus an optional exclusion branch. |
| `hard_malli_errors_to_tree` | `[1,0,0,2,2]` | 3 | Builds nested paths, handles integers, aggregates duplicates in order, and handles empty input. |
| `hard_deep_merge` | `[1,0,0,2,2]` | 3 | Recursive map-only merging distinguishes all non-map replacements, including nil and false. |
| `fix_lazy_notification_effects` | `[0,2,2,1,1]` | 4 | Requires eager ordered exactly-once effects despite laziness, with a fixed nil return. |
| `hard_normalize_project_pull` | `[2,0,0,2,2]` | 4 | Normalizes reverse references with filtering, sorting, exact shape, and absent children. |
| `fix_threading_pipeline` | `[0,0,1,1,1]` | 2 | Correct threading composes filtering, mapping, sorting, realization, and empty input. |
| `hard_reduce_until_match` | `[0,1,2,2,2]` | 4 | Requires `reduced` short-circuiting, non-realization, false preservation, and no-match behavior. |

One-shot total: **79 points**.

## REPL Weights

| Case | Vector | Weight | Rationale |
|---|---:|---:|---|
| `closed-order-stream` | `[1,1,2,1,1]` | 4 | Lazy consumption crosses reader lifetime; output must be realized and blanks ignored. |
| `hot-reload-pricing` | `[1,2,2,2,2]` | 5 | Coordinates parsing, `defonce` state, reload, atomic replacement, rollback, and pricing. |
| `tenant-cache` | `[1,2,1,2,2]` | 5 | Cache identity spans tenant, revision, and product while nil and false remain cached. |
| `webhook-event-fold` | `[1,2,0,2,2]` | 4 | Coordinates deduplication, sequence monotonicity, stale IDs, effects, and replay. |
| `payment-multimethod` | `[1,0,2,2,1]` | 4 | Requires compound dispatch, exact method membership, defaults, and reload-aware inspection. |
| `route-registry-reload` | `[1,2,2,1,2]` | 5 | Macro expansion, Var identity, registry state, reload, idempotence, and dispatch interact. |
| `transducer-completion` | `[1,1,2,2,2]` | 5 | Stateful reducer arities, buffered completion, early termination, and completion count interact. |
| `authorization-lazy-leak` | `[1,1,2,2,2]` | 5 | Dynamic binding, laziness, authorization order, pagination, realization, and field removal interact. |
| `dependency-planner` | `[2,0,0,2,2]` | 4 | Iterative capability planning separates deterministic ties, missing capabilities, and cycles. |
| `session-derived-index` | `[1,2,1,2,2]` | 5 | Two persistent atoms maintain an exact index across mutation, rebuild, sorting, and reload. |

REPL total: **46 points**.

## Initial V1 Assignment

The `correctness-weighted-v1` weights were assigned retrospectively on 2026-07-21. One primary
task analyst produced the dimension vectors and the per-task rationales recorded above. An
independent methodology and code audit reviewed the rubric, implementation, and arithmetic.

Existing model results were already available. The initial assignment was therefore not
preregistered and was not performed by two blind reviewers. The per-task rationales are the
recorded assignment evidence; this project does not claim reviewer IDs, blinded independence,
or disagreement records that did not exist.

## Future Review Protocol

For future task additions and metric versions, weight assignment must happen before candidate
model runs are inspected.

1. Freeze the prompt, fixture, grader, reference, agent policy, and runtime assumptions.
2. Validate that the starting fixture fails for the intended reason and the reference passes.
3. Enumerate atomic obligations and distinct edge families before scoring dimensions.
4. Have two reviewers score independently without model identities, responses, pass rates,
   aggregate scores, or subjective filename difficulty labels.
5. Require every nonzero dimension to cite a prompt clause, fixture behavior, or grader assertion.
6. Apply the fixed threshold table without ranking tasks or targeting a weight distribution.
7. If reviewers cross a weight boundary or differ by more than one on any dimension, obtain a
   third independent review.
8. Resolve a three-reviewer disagreement using the median for each dimension, then derive the
   weight. Do not take the median of final weights.
9. If only two reviewers remain tied and a third is unavailable, use the lower supported
   dimension value and record the unresolved issue.
10. Record reviewer decisions, evidence, rubric version, metric version, suite hashes, and date.

## Protocol Fingerprints

New run artifacts record a `protocol_sha256` that binds correctness to the treatment that
produced it, not only to task text. Protocol manifests use this canonical hash framing:

1. Initialize SHA-256.
2. Add the UTF-8 domain `clojure-model-benchmark-protocol-v1` as an 8-byte unsigned big-endian
   length followed by the domain bytes.
3. Sort files by repository-relative POSIX path.
4. For each file, add the UTF-8 path and then the raw file content, framing each independently as
   an 8-byte unsigned big-endian length followed by its bytes.

Length-delimiting every field prevents ambiguous path/content concatenations. The one-shot
protocol covers `runner.py`, `suites/eval_clojure.py`, `.opencode/agent/benchmark.md`, and
`.opencode/opencode.json`. The REPL protocol covers `repl_runner.py`, `repl_eval.py`,
`repl_cases.py`, `.opencode/agent/repl-benchmark.md`, `.opencode/opencode.json`, and every file
under `repl-cases/`.

Current protocol hashes are:

| Treatment | Protocol SHA-256 |
|---|---|
| One-shot | `a801d645516c900e3bcfd5ac937a81390a360fe795bc12a004c3578dae775664` |
| REPL | `e79364d90498bc9b7776fd849cf9f02b2e584226370b7b83c2db28fa07a2bfdf` |

`weights.json` and `overall_matrix.py` are deliberately excluded to avoid making scoring edits
change the model treatment or creating a self-reference. The runners calculate their own hashes;
the scorer independently recalculates them and validates the manifest and artifacts.

## Metric Definition Fingerprint

Metric version `correctness-weighted-v1` is bound to
`26d37c069a76255d6b87448a4733bc1ab240de467c794ff571c4ff32188e91e0`.

The digest is SHA-256 over UTF-8 canonical JSON using sorted object keys, separators `,` and `:`,
and ASCII escaping. The hashed object includes normalization, rubric version, dimension names,
thresholds, suite task names, vectors, weights, task counts, and suite weight totals. It excludes
rationales, assignment prose, suite hashes, and protocol hashes because those do not define the
scoring arithmetic.

For a future v2, update the metric version, calculate the new canonical definition digest, store
it in `weights.json`, and add the version-to-digest mapping in `overall_matrix.py`. Validation must
fail if scoring arithmetic changes while retaining a known metric version.

## Versioning And Change Rules

The metric and rubric have separate versions. A rubric change can alter weights without changing
task behavior; a suite or protocol change can alter treatment while retaining the same rubric.

| Change | Reweight? | Rerun? |
|---|---|---|
| Prompt adds, removes, or changes accepted behavior | Yes | Entire affected suite |
| Prompt clarifies an existing obligation | Review, usually retain | Yes, because model treatment changed |
| Grader changes pass/fail acceptance | Yes | Entire affected suite |
| Fixture changes diagnosis, state, lifecycle, or solution demands | Yes | Entire affected suite |
| Reference-only refactor with identical behavior | Usually no after review | No after validation |
| Comment, path portability, or provenance-only edit | No; record semantic equivalence | No |
| Timeout, agent permission, tool, bootstrap, or runtime-policy change | Usually no | Yes |
| Add or remove a task | Assign or remove weight and bump versions | Entire affected suite |

Do not silently combine artifacts with materially different suite or protocol hashes. A documented
semantic-equivalence exception can support a historical analysis, but output must remain clearly
marked and must not be presented as a current-treatment result.

## Invalid Runs And Retries

A valid deterministic grader pass is 1. A valid grader fail, including model-generated
nontermination, is 0. An ordinary agent timeout uses the final fresh-process grader result: a
repair completed before timeout can still pass.

Every one-shot result with a null `response` is infrastructure-invalid, even when its detail is
missing or malformed. For REPL runs, startup or bootstrap failure, provider/process failure, and a
successful agent exit with entirely missing or empty event stdout are infrastructure-invalid. An
empty `assistant_text` alone is not invalid when event stdout records tool activity or source edits;
after normal agent execution, the fresh-process grader remains authoritative. Provider outages,
corrupt artifacts, runner crashes, and validated harness failures are also infrastructure-invalid.

Do not remove invalid cases and shrink one model's denominator. Rerun the complete affected suite
under the same route and settings, or report the route as incomplete. Predeclare whether a complete
rerun replaces an invalid run or repeated runs are reported separately, and never select the better
observation after seeing both.

`overall_matrix.py` rejects suite or protocol treatment mismatches and infrastructure-invalid
artifacts by default. `--allow-suite-mismatch` retains its original name for compatibility but
allows either kind of treatment mismatch. It and `--allow-infrastructure-failures` exist only for
explicit, prominently marked retrospective development calculations.

## Historical Development Artifacts

The local development artifacts use one-shot hash
`c34c4c7f06a4a6117277137163d083e39f7208727300b8c7b72e3e5c188d0a96` and REPL hash
`ce6d62226ecfe58cd2af17b8cf3ce8bf38edc6db7034501a3ac2d337efd99433`.
They predate `protocol_sha256` and therefore cannot establish an exact current treatment match.

The one-shot source hash changed for documented portability and provenance edits without changing
the 33 task contracts. The REPL suite is materially historical: current prompts clarify malformed
EDN behavior in `hot-reload-pricing` and enumerate supported dispatch combinations in
`payment-multimethod`. Any combined value calculated from these artifacts must be called a
retrospective development aggregate, not a current public-treatment score.

## Interpretation Limits

- Component one-shot and REPL scores remain primary; overall is secondary.
- Public prompts, fixtures, graders, references, and weights permit contamination and targeted
  optimization.
- A deterministic grader can accept shortcuts or reject valid alternatives.
- Integer weighting cannot remove benchmark gaming or convert narrow cases into a comprehensive
  measure of Clojure engineering.
- Strong models may saturate the short one-shot suite, reducing discrimination.
- One run per route does not estimate variance, uncertainty, or statistical significance.
- Hosted routes can change upstream, and local quantization or inference settings can change
  outcomes.
- Equal suite normalization is a transparent design policy, not a claim that the capabilities are
  interchangeable.

## Commands

Validate the manifest against current suite sources without model artifacts:

```bash
python3 overall_matrix.py --validate
```

Generate a current matrix from valid matching artifacts:

```bash
python3 overall_matrix.py
```

Generate the explicitly marked historical development calculation:

```bash
python3 overall_matrix.py \
  --allow-suite-mismatch \
  --allow-infrastructure-failures
```

The default command validates every JSON artifact in each input directory. If a directory also
contains partial smoke runs or unrelated routes, repeat `--model-route EXACT_ROUTE` to select the
complete exact-route pairs intended for one aggregate; incomplete selected artifacts still fail.

Generated JSON and Markdown are local ignored artifacts. Publish only a reviewed, sanitized
aggregate under `results/`.
