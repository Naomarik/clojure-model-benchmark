#!/usr/bin/env python3
"""Canonical metadata for the separate agentic REPL benchmark."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplCase:
    slug: str
    difficulty: str
    namespace: str
    bootstrap: str
    timeout: int
    prompt: str
    mutate_after_bootstrap: dict[str, str] | None = None


CASES = [
    ReplCase(
        "closed-order-stream", "medium", "bench.closed-order-stream",
        "(require 'bench.closed-order-stream :reload)", 300,
        """`bench.closed-order-stream/read-orders` should return a fully realized vector of parsed order maps while safely closing its reader. It currently returns a value that fails when consumed after the function returns. Blank lines should be ignored. Diagnose this against a temporary file in the live REPL, fix only files under `src`, reload, and verify the repair.""",
    ),
    ReplCase(
        "hot-reload-pricing", "hard", "bench.hot-reload-pricing",
        "(require 'bench.hot-reload-pricing :reload)", 420,
        """The live `bench.hot-reload-pricing` namespace loaded VIP rules before `resources/pricing.edn` changed from 10% to 25%. `price` still uses the stale rules, and `reload-rules!` does not refresh them. Fix refresh behavior so valid files atomically replace the rules. Malformed EDN must make `reload-rules!` throw while retaining the last valid rules unchanged. Inspect live state, fix `src`, reload, and demonstrate the transition.""",
        {"resources/pricing.edn": "{:discounts {:regular 0 :vip 25}}\n"},
    ),
    ReplCase(
        "tenant-cache", "hard", "bench.tenant-cache",
        "(require 'bench.tenant-cache :reload)", 420,
        """`bench.tenant-cache/lookup` contaminates tenants and revisions when product IDs overlap, and falsey loader results are not reliably cached. Use the live cache and an instrumented loader to reproduce call-history-dependent results. Fix `src`, reload, clear state, and verify tenant, revision, and nil caching behavior.""",
    ),
    ReplCase(
        "webhook-event-fold", "hard", "bench.webhook-event-fold",
        "(require 'bench.webhook-event-fold :reload)", 480,
        """`bench.webhook-event-fold` must process each event ID once and must not let a stale lower-sequence event regress subscription state or emit effects. Stale unseen IDs should still be remembered. Replay event sequences in the live REPL, repair `src`, reload, and verify idempotent folding.""",
    ),
    ReplCase(
        "payment-multimethod", "very-hard", "bench.payment-multimethod",
        "(require 'bench.payment-multimethod :reload)", 480,
        """`bench.payment-multimethod/handle-payment` dispatches on `[operation provider]`, but its methods currently miss the supported combinations. Exactly `[:charge :card]`, `[:refund :card]`, and `[:charge :bank]` are supported; `[:refund :bank]` and every other combination are unsupported and must use the default behavior. Inspect the live dispatch value and method table, repair the methods in `src`, reload, and verify supported and default behavior.""",
    ),
    ReplCase(
        "route-registry-reload", "very-hard", "bench.route-registry",
        "(require 'bench.routes :reload)", 540,
        """The route registry keeps a stale handler function after `bench.route-handlers/dashboard` is redefined or reloaded. Registered routes must follow the current Var root, remain idempotent, and preserve 404 behavior. Inspect macro expansion, registry contents, and Var identity in the live REPL; fix `src`, reload the relevant namespaces, and verify hot-reload dispatch.""",
    ),
    ReplCase(
        "transducer-completion", "very-hard", "bench.transducer-completion",
        "(require 'bench.transducer-completion :reload)", 600,
        """`bench.transducer-completion/partition-until` emits a partition when the predicate matches, including the matching input, but drops a final partial partition during completion. It must compose with downstream reducers and complete exactly once. Exercise its reducing-function arities in the REPL, fix `src`, reload, and verify empty, partial, and early-termination inputs.""",
    ),
    ReplCase(
        "authorization-lazy-leak", "extremely-hard", "bench.authorization-lazy-leak",
        "(require 'bench.authorization-lazy-leak :reload)", 660,
        """`bench.authorization-lazy-leak/feed-page` applies pagination before tenant authorization and returns work whose result depends on where it is realized. It must capture the authorized tenant, filter before taking the page, return a realized vector, and never leak tenant fields. Reproduce realization outside `binding`, fix `src`, reload, and verify full isolated pages.""",
    ),
    ReplCase(
        "dependency-planner", "extremely-hard", "bench.dependency-planner",
        "(require 'bench.dependency-planner :reload)", 720,
        """`bench.dependency-planner/plan` incorrectly compares required capabilities with completed job IDs. It must choose the lexicographically smallest runnable job, accumulate provided capabilities, distinguish missing capabilities from true cycles, and return deterministic IDs. Inspect intermediate small plans in the REPL, fix `src`, reload, and verify valid, missing, cyclic, and tie cases.""",
    ),
    ReplCase(
        "session-derived-index", "hard", "bench.session-derived-index",
        "(require 'bench.session-derived-index :reload)", 420,
        """`bench.session-derived-index` maintains `sessions` plus a derived `by-user` index, but puts/deletes leave it stale and rebuild merges obsolete users. The index must exactly reflect primary state with session IDs sorted, including across repeated rebuilds and namespace reloads. Inspect both live atoms, repair `src`, reload, and verify a sequence of puts, deletes, and rebuilds.""",
    ),
]

CASE_BY_SLUG = {case.slug: case for case in CASES}

assert len(CASES) == 10
assert len(CASE_BY_SLUG) == 10
