#!/usr/bin/env python3
"""Build separate correctness and REPL-use matrices for agentic runs."""

import json
from pathlib import Path

from repl_cases import CASE_BY_SLUG

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "artifacts/repl-runs"


def main() -> None:
    runs = [json.loads(path.read_text()) for path in sorted(RUNS.glob("*.json"))]
    if not runs:
        raise SystemExit("no agentic REPL run artifacts found")
    suite_hashes = {run.get("suite_sha256") for run in runs}
    if len(suite_hashes) != 1:
        raise SystemExit("run artifacts use different agentic suite hashes")
    expected_cases = set(CASE_BY_SLUG)
    for run in runs:
        names = [item["case"] for item in run["results"]]
        if len(names) != len(expected_cases) or set(names) != expected_cases:
            raise SystemExit(f"{run['label']}: incomplete, duplicate, or unknown cases")
    matrix = {
        "suite": "agentic-clojure-repl",
        "suite_sha256": next(iter(suite_hashes)),
        "models": [],
    }
    lines = [
        "# Agentic Clojure REPL Matrix", "",
        "Correctness and meaningful REPL use are reported separately.", "",
        "| Label | Model | Correct | REPL use | Timeouts | Elapsed |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for run in runs:
        results = run["results"]
        correct = sum(item["correctness"]["score"] for item in results)
        repl = sum(item["repl_usage"]["score"] for item in results)
        timeouts = sum(bool(item["opencode"]["timed_out"]) for item in results)
        elapsed = sum(item["elapsed_s"] for item in results)
        row = {
            "label": run["label"], "model": run["model"],
            "correctness": correct, "correctness_max": len(results),
            "repl_use": repl, "repl_use_max": 4 * len(results),
            "timeouts": timeouts,
            "elapsed_s": elapsed,
            "cases": {item["case"]: {
                "correct": bool(item["correctness"]["score"]),
                "repl_use": item["repl_usage"]["score"],
            } for item in results},
        }
        matrix["models"].append(row)
        lines.append(
            f"| {run['label']} | `{run['model']}` | {correct}/{len(results)} | "
            f"{repl}/{4 * len(results)} | {timeouts} | {elapsed:.1f}s |"
        )
    case_names = [item["case"] for item in runs[0]["results"]]
    lines.extend([
        "", "## Per-Case Results", "",
        "Cells show `correctness/repl-use`.", "",
        "| Case | " + " | ".join(run["label"] for run in runs) + " |",
        "|---|" + "---:|" * len(runs),
    ])
    for case_name in case_names:
        cells = []
        for run in runs:
            item = next(result for result in run["results"] if result["case"] == case_name)
            marker = "T" if item["opencode"]["timed_out"] else ""
            cells.append(
                f"{item['correctness']['score']}/{item['repl_usage']['score']}{marker}"
            )
        lines.append(f"| `{case_name}` | " + " | ".join(cells) + " |")
    (ROOT / "artifacts/repl-matrix.json").write_text(json.dumps(matrix, indent=2) + "\n")
    (ROOT / "artifacts/REPL_MATRIX.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
