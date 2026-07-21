#!/usr/bin/env python3
"""Build a correctness-only weighted matrix from one-shot and REPL artifacts."""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from repl_cases import CASES

ROOT = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = ROOT / "weights.json"
DEFAULT_ONE_SHOT_RUNS = ROOT / "artifacts/runs"
DEFAULT_REPL_RUNS = ROOT / "artifacts/repl-runs"
DEFAULT_JSON_OUTPUT = ROOT / "artifacts/overall-matrix.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "artifacts/OVERALL_MATRIX.md"
ONE_SHOT_SUITE = ROOT / "suites/eval_clojure.py"
REPL_AGENT = ROOT / ".opencode/agent/repl-benchmark.md"
REPL_CASES_ROOT = ROOT / "repl-cases"
PROTOCOL_HASH_DOMAIN = b"clojure-model-benchmark-protocol-v1"
ONE_SHOT_PROTOCOL_PATHS = (
    ROOT / "runner.py",
    ONE_SHOT_SUITE,
    ROOT / ".opencode/agent/benchmark.md",
    ROOT / ".opencode/opencode.json",
)
REPL_PROTOCOL_PATHS = (
    ROOT / "repl_runner.py",
    ROOT / "repl_eval.py",
    ROOT / "repl_cases.py",
    REPL_AGENT,
    ROOT / ".opencode/opencode.json",
)
KNOWN_METRIC_DEFINITION_SHA256 = {
    "correctness-weighted-v1": "26d37c069a76255d6b87448a4733bc1ab240de467c794ff571c4ff32188e91e0",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {path}: {error}")
    if not isinstance(value, dict):
        fail(f"{path}: top-level JSON value must be an object")
    return value


def is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def canonical_manifest_hash(paths: list[Path] | tuple[Path, ...]) -> str:
    """Hash sorted repository paths and contents with unambiguous framing."""
    digest = hashlib.sha256()

    def update(value: bytes) -> None:
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)

    update(PROTOCOL_HASH_DOMAIN)
    for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix()):
        update(path.relative_to(ROOT).as_posix().encode())
        update(path.read_bytes())
    return digest.hexdigest()


def expected_weight(total: int, thresholds: list[dict]) -> int:
    matches = [
        threshold["weight"]
        for threshold in thresholds
        if threshold["min"] <= total <= threshold["max"]
    ]
    if len(matches) != 1:
        fail(f"rubric total {total} matches {len(matches)} threshold ranges")
    return matches[0]


def load_one_shot_names() -> set[str]:
    spec = importlib.util.spec_from_file_location("weighted_eval_clojure", ONE_SHOT_SUITE)
    if spec is None or spec.loader is None:
        fail(f"cannot import canonical suite: {ONE_SHOT_SUITE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = [task[0] for task in module.TASKS]
    if len(names) != len(set(names)):
        fail("canonical one-shot suite contains duplicate task names")
    return set(names)


def current_repl_hash() -> str:
    digest = hashlib.sha256()
    paths = [ROOT / "repl_cases.py", REPL_AGENT]
    paths.extend(sorted(path for path in REPL_CASES_ROOT.rglob("*") if path.is_file()))
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def current_protocol_hashes() -> dict[str, str]:
    repl_paths = list(REPL_PROTOCOL_PATHS)
    repl_paths.extend(path for path in REPL_CASES_ROOT.rglob("*") if path.is_file())
    return {
        "one_shot": canonical_manifest_hash(ONE_SHOT_PROTOCOL_PATHS),
        "repl": canonical_manifest_hash(repl_paths),
    }


def validate_runner_protocol_implementations(expected: dict[str, str]) -> None:
    for suite_name, source in (
        ("one_shot", ROOT / "runner.py"),
        ("repl", ROOT / "repl_runner.py"),
    ):
        spec = importlib.util.spec_from_file_location(f"protocol_{suite_name}_runner", source)
        if spec is None or spec.loader is None:
            fail(f"cannot import protocol implementation: {source}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        actual = module.protocol_hash()
        if actual != expected[suite_name]:
            fail(
                f"{source}: runner protocol hash {actual} does not match independent scorer "
                f"hash {expected[suite_name]}"
            )


def scoring_definition(manifest: dict) -> dict:
    """Return the canonical, prose-free scoring definition bound to a metric version."""
    return {
        "normalization": manifest["normalization"],
        "rubric_version": manifest["rubric_version"],
        "dimension_names": manifest["dimension_names"],
        "total_to_weight_thresholds": manifest["total_to_weight_thresholds"],
        "suites": {
            suite_name: {
                "task_count": suite["task_count"],
                "weight_total": suite["weight_total"],
                "tasks": {
                    task_name: {
                        "dimensions": task["dimensions"],
                        "weight": task["weight"],
                    }
                    for task_name, task in suite["tasks"].items()
                },
            }
            for suite_name, suite in manifest["suites"].items()
        },
    }


def scoring_definition_hash(manifest: dict) -> str:
    encoded = json.dumps(
        scoring_definition(manifest), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_manifest(path: Path) -> dict:
    manifest = read_json(path)
    if manifest.get("schema_version") != 1:
        fail(f"{path}: unsupported schema_version")
    for key in ("metric_version", "rubric_version"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            fail(f"{path}: {key} must be a non-empty string")
    assignment = manifest.get("assignment")
    if not isinstance(assignment, dict):
        fail(f"{path}: assignment must be an object")
    if assignment.get("date") != "2026-07-21":
        fail(f"{path}: assignment date must record the v1 assignment date")
    if assignment.get("timing") != "retrospective" or assignment.get("preregistered") is not False:
        fail(f"{path}: v1 assignment must be recorded as retrospective and not preregistered")
    for key in ("task_analysis", "audit", "limitations"):
        if not isinstance(assignment.get(key), str) or not assignment[key].strip():
            fail(f"{path}: assignment.{key} must be a non-empty string")

    normalization = manifest.get("normalization")
    if not isinstance(normalization, dict):
        fail(f"{path}: normalization must be an object")
    shares = (normalization.get("one_shot_share"), normalization.get("repl_share"))
    if shares != (0.5, 0.5) or sum(shares) != 1:
        fail(f"{path}: normalization must use fixed 0.5/0.5 suite shares")

    dimensions = manifest.get("dimension_names")
    if not isinstance(dimensions, list) or len(dimensions) != 5:
        fail(f"{path}: dimension_names must contain exactly five entries")
    if len(set(dimensions)) != len(dimensions) or not all(
        isinstance(name, str) and name for name in dimensions
    ):
        fail(f"{path}: dimension_names must be unique non-empty strings")

    thresholds = manifest.get("total_to_weight_thresholds")
    if not isinstance(thresholds, list) or len(thresholds) != 5:
        fail(f"{path}: total_to_weight_thresholds must contain five ranges")
    covered: dict[int, int] = {}
    for threshold in thresholds:
        if not isinstance(threshold, dict):
            fail(f"{path}: each threshold must be an object")
        values = [threshold.get(key) for key in ("min", "max", "weight")]
        if not all(is_plain_int(value) for value in values):
            fail(f"{path}: threshold values must be integers")
        minimum, maximum, weight = values
        if minimum > maximum or weight not in range(1, 6):
            fail(f"{path}: invalid threshold {threshold}")
        for total in range(minimum, maximum + 1):
            if total in covered:
                fail(f"{path}: overlapping threshold at rubric total {total}")
            covered[total] = weight
    if set(covered) != set(range(11)):
        fail(f"{path}: thresholds must cover every rubric total from 0 through 10")

    suites = manifest.get("suites")
    if not isinstance(suites, dict) or set(suites) != {"one_shot", "repl"}:
        fail(f"{path}: suites must contain exactly one_shot and repl")
    canonical_names = {
        "one_shot": load_one_shot_names(),
        "repl": {case.slug for case in CASES},
    }
    canonical_hashes = {
        "one_shot": hashlib.sha256(ONE_SHOT_SUITE.read_bytes()).hexdigest(),
        "repl": current_repl_hash(),
    }
    protocol_hashes = current_protocol_hashes()
    validate_runner_protocol_implementations(protocol_hashes)
    for suite_name, suite in suites.items():
        if not isinstance(suite, dict):
            fail(f"{path}: {suite_name} must be an object")
        tasks = suite.get("tasks")
        if not isinstance(tasks, dict):
            fail(f"{path}: {suite_name}.tasks must be an object")
        if set(tasks) != canonical_names[suite_name]:
            missing = sorted(canonical_names[suite_name] - set(tasks))
            extra = sorted(set(tasks) - canonical_names[suite_name])
            fail(f"{path}: {suite_name} task mismatch; missing={missing}, extra={extra}")
        if suite.get("task_count") != len(tasks):
            fail(f"{path}: {suite_name} task_count does not match its task manifest")
        if suite.get("expected_sha256") != canonical_hashes[suite_name]:
            fail(
                f"{path}: {suite_name} expected hash does not match current source "
                f"({suite.get('expected_sha256')} != {canonical_hashes[suite_name]})"
            )
        if suite.get("expected_protocol_sha256") != protocol_hashes[suite_name]:
            fail(
                f"{path}: {suite_name} expected protocol hash does not match current treatment "
                f"({suite.get('expected_protocol_sha256')} != {protocol_hashes[suite_name]})"
            )
        weight_total = 0
        for task_name, task in tasks.items():
            if not isinstance(task, dict):
                fail(f"{path}: {suite_name}.{task_name} must be an object")
            vector = task.get("dimensions")
            if (
                not isinstance(vector, list)
                or len(vector) != len(dimensions)
                or not all(is_plain_int(value) and value in range(3) for value in vector)
            ):
                fail(f"{path}: {suite_name}.{task_name} has an invalid dimension vector")
            weight = task.get("weight")
            if not is_plain_int(weight):
                fail(f"{path}: {suite_name}.{task_name} weight must be an integer")
            derived = expected_weight(sum(vector), thresholds)
            if weight != derived:
                fail(
                    f"{path}: {suite_name}.{task_name} weight {weight} does not match "
                    f"rubric-derived weight {derived}"
                )
            if not isinstance(task.get("rationale"), str) or not task["rationale"].strip():
                fail(f"{path}: {suite_name}.{task_name} requires a rationale")
            weight_total += weight
        if suite.get("weight_total") != weight_total:
            fail(
                f"{path}: {suite_name} weight_total {suite.get('weight_total')} "
                f"does not match calculated total {weight_total}"
            )
    definition_hash = scoring_definition_hash(manifest)
    expected_definition_hash = KNOWN_METRIC_DEFINITION_SHA256.get(manifest["metric_version"])
    if expected_definition_hash is None:
        fail(
            f"{path}: metric_version {manifest['metric_version']!r} has no known scoring-definition digest"
        )
    if definition_hash != expected_definition_hash:
        fail(
            f"{path}: scoring definition changed without a metric version update "
            f"({definition_hash} != {expected_definition_hash})"
        )
    if manifest.get("scoring_definition_sha256") != definition_hash:
        fail(f"{path}: scoring_definition_sha256 does not match the canonical definition")
    return manifest


def artifact_name(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_artifacts(directory: Path, kind: str) -> dict[str, tuple[Path, dict]]:
    paths = sorted(directory.glob("*.json"))
    if not paths:
        fail(f"no {kind} artifacts found in {directory}")
    by_route: dict[str, tuple[Path, dict]] = {}
    for path in paths:
        run = read_json(path)
        route = run.get("model")
        if not isinstance(route, str) or not route:
            fail(f"{path}: model must be a non-empty exact route")
        if route in by_route:
            previous = by_route[route][0]
            fail(f"duplicate {kind} route {route!r}: {previous} and {path}")
        by_route[route] = (path, run)
    return by_route


def select_routes(
    runs: dict[str, tuple[Path, dict]], requested: set[str], kind: str
) -> dict[str, tuple[Path, dict]]:
    if not requested:
        return runs
    missing = sorted(requested - set(runs))
    if missing:
        fail(f"requested {kind} model routes are missing: {missing}")
    return {route: runs[route] for route in requested}


def transport_family(run: dict, artifact: Path) -> str:
    transport = run.get("transport")
    if transport is None:
        return "opencode"
    if not isinstance(transport, str):
        fail(f"{artifact}: transport must be a string")
    if transport.startswith("opencode"):
        return "opencode"
    if transport.startswith("claude"):
        return "claude"
    fail(f"{artifact}: unsupported transport {transport!r}")


def exact_results(
    run: dict, expected: set[str], name_key: str, artifact: Path
) -> dict[str, dict]:
    results = run.get("results")
    if not isinstance(results, list):
        fail(f"{artifact}: results must be an array")
    names = [item.get(name_key) for item in results if isinstance(item, dict)]
    if len(names) != len(results) or not all(isinstance(name, str) for name in names):
        fail(f"{artifact}: every result requires a string {name_key}")
    if len(names) != len(set(names)):
        fail(f"{artifact}: duplicate {name_key} values")
    if set(names) != expected:
        missing = sorted(expected - set(names))
        extra = sorted(set(names) - expected)
        fail(f"{artifact}: result set mismatch; missing={missing}, extra={extra}")
    return dict(zip(names, results, strict=True))


def one_shot_infrastructure_reason(result: dict) -> str | None:
    detail = result.get("detail")
    if result.get("response") is None:
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        return "one-shot response is null without a usable failure detail"
    return None


def repl_infrastructure_reason(result: dict, transport: str) -> str | None:
    opencode = result.get("opencode")
    if not isinstance(opencode, dict):
        return "missing OpenCode orchestration record"
    timed_out = opencode.get("timed_out")
    if not isinstance(timed_out, bool):
        return "OpenCode timed_out is not boolean"
    if timed_out:
        return None
    exit_code = opencode.get("exit_code")
    stderr = opencode.get("stderr")
    if exit_code is None:
        detail = stderr.strip() if isinstance(stderr, str) else ""
        return detail or "OpenCode or REPL startup ended without an exit code"
    if not is_plain_int(exit_code):
        return "OpenCode exit_code is invalid"
    if exit_code != 0:
        return f"OpenCode/provider process exited {exit_code}"
    stdout = opencode.get("stdout")
    if not isinstance(stdout, str) or not stdout.strip():
        return "agent process exited successfully without event stdout"
    if transport == "claude":
        start = stdout.find("{")
        if start < 0:
            return "Claude Code returned no JSON result payload"
        try:
            payload = json.loads(stdout[start:])
        except json.JSONDecodeError as error:
            return f"Claude Code returned malformed JSON: {error}"
        if payload.get("is_error") is True or payload.get("subtype") != "success":
            detail = payload.get("result")
            return f"Claude Code error result: {str(detail)[:500]}"
    return None


def validate_one_shot_run(
    path: Path, run: dict, tasks: dict[str, dict]
) -> tuple[dict[str, dict], list[dict]]:
    results = exact_results(run, set(tasks), "task", path)
    if run.get("total") != len(tasks):
        fail(f"{path}: total does not match the manifest task count")
    passed_count = 0
    invalid = []
    for name, result in results.items():
        passed = result.get("passed")
        if not isinstance(passed, bool):
            fail(f"{path}: {name} passed must be boolean")
        passed_count += passed
        reason = one_shot_infrastructure_reason(result)
        if reason:
            invalid.append({"suite": "one_shot", "task": name, "reason": reason})
    score = run.get("score")
    if not is_plain_int(score) or score != passed_count:
        fail(f"{path}: stored score does not match task-level booleans")
    return results, invalid


def validate_repl_run(
    path: Path, run: dict, tasks: dict[str, dict], transport: str
) -> tuple[dict[str, dict], list[dict], int]:
    results = exact_results(run, set(tasks), "case", path)
    invalid = []
    timeouts = 0
    for name, result in results.items():
        correctness = result.get("correctness")
        if not isinstance(correctness, dict):
            fail(f"{path}: {name} correctness must be an object")
        passed = correctness.get("passed")
        score = correctness.get("score")
        if not isinstance(passed, bool):
            fail(f"{path}: {name} correctness.passed must be boolean")
        if not is_plain_int(score) or score not in (0, 1) or score != int(passed):
            fail(f"{path}: {name} correctness score does not match its boolean")
        if correctness.get("max_score") != 1:
            fail(f"{path}: {name} correctness.max_score must be 1")
        exit_code = correctness.get("exit_code")
        if is_plain_int(exit_code) and passed != (exit_code == 0):
            fail(f"{path}: {name} grader exit code disagrees with correctness")
        reason = repl_infrastructure_reason(result, transport)
        if reason:
            invalid.append({"suite": "repl", "task": name, "reason": reason})
        opencode = result["opencode"]
        timeouts += bool(opencode.get("timed_out"))
    return results, invalid, timeouts


def route_status(treatment_mismatch: bool, infrastructure_invalid: bool) -> str:
    if treatment_mismatch and infrastructure_invalid:
        return "historical-treatment-mismatch+infrastructure-provisional"
    if treatment_mismatch:
        return "historical-treatment-mismatch"
    if infrastructure_invalid:
        return "infrastructure-provisional"
    return "current-valid"


def weighted_score(results: dict[str, dict], tasks: dict[str, dict], repl: bool) -> int:
    return sum(
        tasks[name]["weight"]
        * bool(result["correctness"]["passed"] if repl else result["passed"])
        for name, result in results.items()
    )


def correctness_count(results: dict[str, dict], repl: bool) -> int:
    return sum(
        bool(result["correctness"]["passed"] if repl else result["passed"])
        for result in results.values()
    )


def build_matrix(
    manifest: dict,
    manifest_path: Path,
    one_shot_runs: dict[str, tuple[Path, dict]],
    repl_runs: dict[str, tuple[Path, dict]],
    allow_suite_mismatch: bool,
    allow_infrastructure_failures: bool,
) -> dict:
    if set(one_shot_runs) != set(repl_runs):
        missing_one = sorted(set(repl_runs) - set(one_shot_runs))
        missing_repl = sorted(set(one_shot_runs) - set(repl_runs))
        fail(f"exact model routes are unpaired; missing one-shot={missing_one}, missing REPL={missing_repl}")

    suites = manifest["suites"]
    one_tasks = suites["one_shot"]["tasks"]
    repl_tasks = suites["repl"]["tasks"]
    one_total = suites["one_shot"]["weight_total"]
    repl_total = suites["repl"]["weight_total"]
    one_share = manifest["normalization"]["one_shot_share"]
    repl_share = manifest["normalization"]["repl_share"]
    models = []
    generated_from = []
    all_mismatches = []
    all_invalid = []

    for route in sorted(one_shot_runs):
        one_path, one_run = one_shot_runs[route]
        repl_path, repl_run = repl_runs[route]
        one_transport = transport_family(one_run, one_path)
        repl_transport = transport_family(repl_run, repl_path)
        if one_transport != repl_transport:
            fail(
                f"{route}: one-shot transport {one_transport!r} does not match "
                f"REPL transport {repl_transport!r}"
            )
        one_effort = one_run.get("effort")
        repl_effort = repl_run.get("effort")
        if one_effort != repl_effort:
            fail(
                f"{route}: one-shot effort {one_effort!r} does not match "
                f"REPL effort {repl_effort!r}"
            )
        if one_transport == "claude" and one_effort != "low":
            fail(f"{route}: published Claude artifacts must use the canonical 'low' effort")
        generated_from.extend((artifact_name(one_path), artifact_name(repl_path)))
        one_results, one_invalid = validate_one_shot_run(one_path, one_run, one_tasks)
        repl_results, repl_invalid, timeouts = validate_repl_run(
            repl_path, repl_run, repl_tasks, repl_transport
        )
        invalid = one_invalid + repl_invalid
        all_invalid.extend({"model": route, **item} for item in invalid)

        observed_treatment_hashes = {
            "one_shot": {
                "suite_sha256": one_run.get("canonical_suite_sha256"),
                "protocol_sha256": one_run.get("protocol_sha256"),
            },
            "repl": {
                "suite_sha256": repl_run.get("suite_sha256"),
                "protocol_sha256": repl_run.get("protocol_sha256"),
            },
        }
        expected_treatment_hashes = {
            suite_name: {
                "suite_sha256": suites[suite_name]["expected_sha256"],
                "protocol_sha256": suites[suite_name]["expected_protocol_sha256"],
            }
            for suite_name in ("one_shot", "repl")
        }
        mismatches = {
            suite_name: {
                fingerprint: {
                    "expected": expected_treatment_hashes[suite_name][fingerprint],
                    "observed": observed_treatment_hashes[suite_name][fingerprint],
                }
                for fingerprint in ("suite_sha256", "protocol_sha256")
                if observed_treatment_hashes[suite_name][fingerprint]
                != expected_treatment_hashes[suite_name][fingerprint]
            }
            for suite_name in ("one_shot", "repl")
        }
        mismatches = {suite_name: values for suite_name, values in mismatches.items() if values}
        all_mismatches.extend(
            {
                "model": route,
                "suite": suite_name,
                "fingerprint": fingerprint,
                **hashes,
            }
            for suite_name, fingerprints in mismatches.items()
            for fingerprint, hashes in fingerprints.items()
        )

        one_correct = correctness_count(one_results, repl=False)
        repl_correct = correctness_count(repl_results, repl=True)
        one_points = weighted_score(one_results, one_tasks, repl=False)
        repl_points = weighted_score(repl_results, repl_tasks, repl=True)
        one_rate = one_points / one_total
        repl_rate = repl_points / repl_total
        direct_points = one_points + repl_points
        direct_total = one_total + repl_total
        overall = 100 * (one_share * one_rate + repl_share * repl_rate)
        models.append(
            {
                "model": route,
                "status": route_status(bool(mismatches), bool(invalid)),
                "transport": one_transport,
                "effort": one_effort,
                "artifacts": {
                    "one_shot": artifact_name(one_path),
                    "repl": artifact_name(repl_path),
                },
                "observed_treatment_hashes": observed_treatment_hashes,
                "treatment_mismatches": mismatches,
                "one_shot": {
                    "correct": one_correct,
                    "total": len(one_tasks),
                    "weighted_points": one_points,
                    "weighted_total": one_total,
                    "weighted_percent": 100 * one_rate,
                },
                "repl": {
                    "correct": repl_correct,
                    "total": len(repl_tasks),
                    "weighted_points": repl_points,
                    "weighted_total": repl_total,
                    "weighted_percent": 100 * repl_rate,
                },
                "direct_raw_diagnostic": {
                    "points": direct_points,
                    "total": direct_total,
                    "percent": 100 * direct_points / direct_total,
                },
                "overall": {
                    "score": overall,
                    "max_score": 100,
                    "one_shot_share": one_share,
                    "repl_share": repl_share,
                },
                "timeouts": timeouts,
                "infrastructure_invalid_count": len(invalid),
                "infrastructure_invalid": invalid,
            }
        )

    if all_mismatches and not allow_suite_mismatch:
        fail(
            f"found {len(all_mismatches)} suite/protocol treatment hash mismatches; rerun the "
            "current treatment or use --allow-suite-mismatch for an explicitly historical calculation"
        )
    if all_invalid and not allow_infrastructure_failures:
        fail(
            f"found {len(all_invalid)} infrastructure-invalid results; rerun them or use "
            "--allow-infrastructure-failures for a provisional calculation"
        )

    models.sort(key=lambda model: (-model["overall"]["score"], model["model"]))
    status = route_status(bool(all_mismatches), bool(all_invalid))
    observed_treatment_hashes = {
        suite_name: {
            fingerprint: sorted(
                {
                    model["observed_treatment_hashes"][suite_name][fingerprint]
                    for model in models
                    if isinstance(
                        model["observed_treatment_hashes"][suite_name][fingerprint], str
                    )
                }
            )
            for fingerprint in ("suite_sha256", "protocol_sha256")
        }
        for suite_name in ("one_shot", "repl")
    }
    return {
        "schema_version": 1,
        "metric_version": manifest["metric_version"],
        "rubric_version": manifest["rubric_version"],
        "status": status,
        "provenance": {
            "weights_manifest": artifact_name(manifest_path),
            "metric_definition_sha256": scoring_definition_hash(manifest),
            "weight_assignment": manifest["assignment"],
            "expected_treatment_hashes": {
                name: {
                    "suite_sha256": suites[name]["expected_sha256"],
                    "protocol_sha256": suites[name]["expected_protocol_sha256"],
                }
                for name in ("one_shot", "repl")
            },
            "observed_treatment_hashes": observed_treatment_hashes,
            "allow_suite_mismatch": allow_suite_mismatch,
            "allow_infrastructure_failures": allow_infrastructure_failures,
            "generated_from": sorted(generated_from),
            "treatment_mismatches": all_mismatches,
            "infrastructure_invalid": all_invalid,
        },
        "normalization": manifest["normalization"],
        "suite_weight_totals": {"one_shot": one_total, "repl": repl_total},
        "models": models,
    }


def markdown(matrix: dict) -> str:
    provenance = matrix["provenance"]

    def format_hashes(values: list[str]) -> str:
        return ", ".join(f"`{value}`" for value in values) or "`(missing)`"

    lines = [
        "# Weighted Correctness Matrix",
        "",
        f"Status: **{matrix['status']}**",
        "",
        "Component correctness scores remain primary. Overall is a secondary 50/50 normalized "
        "summary and contains only binary grader correctness.",
        "",
    ]
    if provenance["treatment_mismatches"]:
        lines.extend(
            [
                "> Historical suite and/or protocol treatment fingerprints differ from the current "
                "weighting manifest. These values are retrospective and are not current-treatment "
                "results.",
                "",
            ]
        )
    if provenance["infrastructure_invalid"]:
        lines.extend(
            [
                "> Infrastructure-invalid task observations are counted as their recorded binary "
                "failures only for this explicitly allowed provisional calculation.",
                "",
            ]
        )
    lines.extend(
        [
            "| Exact model route | Status | One-shot | One-shot weighted | REPL | REPL weighted | "
            "Direct raw | Overall | Timeouts | Infra invalid |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for model in matrix["models"]:
        one = model["one_shot"]
        repl = model["repl"]
        direct = model["direct_raw_diagnostic"]
        lines.append(
            f"| `{model['model']}` | {model['status']} | {one['correct']}/{one['total']} | "
            f"{one['weighted_points']}/{one['weighted_total']} ({one['weighted_percent']:.4f}%) | "
            f"{repl['correct']}/{repl['total']} | "
            f"{repl['weighted_points']}/{repl['weighted_total']} ({repl['weighted_percent']:.4f}%) | "
            f"{direct['points']}/{direct['total']} ({direct['percent']:.4f}%) | "
            f"**{model['overall']['score']:.4f}** | {model['timeouts']} | "
            f"{model['infrastructure_invalid_count']} |"
        )
    lines.extend(
        [
            "",
            "## Provenance",
            "",
            f"- Metric version: `{matrix['metric_version']}`",
            f"- Metric definition hash: `{provenance['metric_definition_sha256']}`",
            f"- Rubric version: `{matrix['rubric_version']}`",
            f"- Weight assignment timing: `{provenance['weight_assignment']['timing']}`",
            "- Weight assignment preregistered: "
            f"`{str(provenance['weight_assignment']['preregistered']).lower()}`",
            "- One-shot expected suite hash: "
            f"`{provenance['expected_treatment_hashes']['one_shot']['suite_sha256']}`",
            "- One-shot observed suite hashes: "
            + format_hashes(
                provenance["observed_treatment_hashes"]["one_shot"]["suite_sha256"]
            ),
            "- One-shot expected protocol hash: "
            f"`{provenance['expected_treatment_hashes']['one_shot']['protocol_sha256']}`",
            "- One-shot observed protocol hashes: "
            + format_hashes(
                provenance["observed_treatment_hashes"]["one_shot"]["protocol_sha256"]
            ),
            "- REPL expected suite hash: "
            f"`{provenance['expected_treatment_hashes']['repl']['suite_sha256']}`",
            "- REPL observed suite hashes: "
            + format_hashes(provenance["observed_treatment_hashes"]["repl"]["suite_sha256"]),
            "- REPL expected protocol hash: "
            f"`{provenance['expected_treatment_hashes']['repl']['protocol_sha256']}`",
            "- REPL observed protocol hashes: "
            + format_hashes(provenance["observed_treatment_hashes"]["repl"]["protocol_sha256"]),
            f"- Treatment mismatch override: `{str(provenance['allow_suite_mismatch']).lower()}`",
            "- Infrastructure failure override: "
            f"`{str(provenance['allow_infrastructure_failures']).lower()}`",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--one-shot-runs", type=Path, default=DEFAULT_ONE_SHOT_RUNS)
    parser.add_argument("--repl-runs", type=Path, default=DEFAULT_REPL_RUNS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument(
        "--model-route",
        action="append",
        default=[],
        help="include only this exact route; repeat to select multiple routes",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help=(
            "validate metric, manifest, suites, and protocol sources without reading run artifacts"
        ),
    )
    parser.add_argument(
        "--allow-suite-mismatch",
        action="store_true",
        help=(
            "allow historical suite or protocol treatment fingerprints and mark output retrospective"
        ),
    )
    parser.add_argument(
        "--allow-infrastructure-failures",
        action="store_true",
        help="allow infrastructure-invalid observations and mark output provisional",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = validate_manifest(args.weights.resolve())
    if args.validate:
        print(
            "Validated weights manifest: "
            f"{manifest['suites']['one_shot']['task_count']} one-shot tasks / "
            f"{manifest['suites']['one_shot']['weight_total']} points, "
            f"{manifest['suites']['repl']['task_count']} REPL cases / "
            f"{manifest['suites']['repl']['weight_total']} points, "
            f"metric-definition={scoring_definition_hash(manifest)}"
        )
        return 0

    requested_routes = set(args.model_route)
    one_shot_runs = select_routes(
        load_artifacts(args.one_shot_runs.resolve(), "one-shot"), requested_routes, "one-shot"
    )
    repl_runs = select_routes(
        load_artifacts(args.repl_runs.resolve(), "REPL"), requested_routes, "REPL"
    )
    matrix = build_matrix(
        manifest,
        args.weights.resolve(),
        one_shot_runs,
        repl_runs,
        args.allow_suite_mismatch,
        args.allow_infrastructure_failures,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(matrix, indent=2) + "\n")
    args.output_markdown.write_text(markdown(matrix))
    print(
        f"Wrote {args.output_json} and {args.output_markdown}: "
        f"{len(matrix['models'])} exact model routes, status={matrix['status']}"
    )
    for model in matrix["models"]:
        print(
            f"  {model['model']}: overall={model['overall']['score']:.4f} "
            f"one-shot={model['one_shot']['weighted_points']}/"
            f"{model['one_shot']['weighted_total']} "
            f"REPL={model['repl']['weighted_points']}/{model['repl']['weighted_total']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
