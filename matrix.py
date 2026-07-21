#!/usr/bin/env python3
"""Build Markdown and JSON matrices from completed benchmark runs."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "artifacts/runs"


def main() -> None:
    runs = []
    for path in sorted(RUNS.glob("*.json")):
        run = json.loads(path.read_text())
        run["artifact"] = str(path.relative_to(ROOT))
        runs.append(run)
    if not runs:
        raise SystemExit("no run artifacts found")

    suite_hashes = {run.get("canonical_suite_sha256") for run in runs}
    if len(suite_hashes) != 1:
        raise SystemExit("run artifacts use different one-shot suite hashes")
    task_names = [item["task"] for item in runs[0]["results"]]
    expected_tasks = set(task_names)
    if len(expected_tasks) != len(task_names):
        raise SystemExit("first run artifact contains duplicate tasks")
    for run in runs:
        names = [item["task"] for item in run["results"]]
        if len(names) != run["total"] or len(set(names)) != len(names):
            raise SystemExit(f"{run['label']}: incomplete or duplicate task results")
        if set(names) != expected_tasks:
            raise SystemExit(f"{run['label']}: task set differs from other runs")
        if run["score"] != sum(bool(item["passed"]) for item in run["results"]):
            raise SystemExit(f"{run['label']}: stored score does not match task results")
    matrix = {
        "generated_from": [run["artifact"] for run in runs],
        "suite_sha256": next(iter(suite_hashes)),
        "models": [
            {
                "label": run["label"],
                "model": run["model"],
                "score": run["score"],
                "total": run["total"],
                "status": (
                    "unsupported-no-text"
                    if run["results"] and all(
                        item["response"] is None
                        and "no assistant text events" in item["detail"]
                        for item in run["results"]
                    )
                    else "completed"
                ),
                "elapsed_s": sum(item["elapsed_s"] for item in run["results"]),
                "tasks": {item["task"]: item["passed"] for item in run["results"]},
            }
            for run in runs
        ],
    }
    (ROOT / "artifacts/matrix.json").write_text(json.dumps(matrix, indent=2) + "\n")

    lines = [
        "# Clojure Model Benchmark Matrix",
        "",
        "| Model | Score | Pass rate | Elapsed |",
        "|---|---:|---:|---:|",
    ]
    for run in runs:
        unsupported = run["results"] and all(
            item["response"] is None and "no assistant text events" in item["detail"]
            for item in run["results"]
        )
        rate = 100 * run["score"] / run["total"] if run["total"] else 0
        elapsed = sum(item["elapsed_s"] for item in run["results"])
        score = "unsupported" if unsupported else f"{run['score']}/{run['total']}"
        rate_text = "N/A" if unsupported else f"{rate:.1f}%"
        lines.append(f"| `{run['model']}` | {score} | {rate_text} | {elapsed:.1f}s |")
    lines.extend(["", "| Task | " + " | ".join(run["label"] for run in runs) + " |",
                  "|---|" + "---:|" * len(runs)])
    for task in task_names:
        cells = []
        for run in runs:
            item = next(result for result in run["results"] if result["task"] == task)
            unsupported = all(
                result["response"] is None
                and "no assistant text events" in result["detail"]
                for result in run["results"]
            )
            cells.append("N/A" if unsupported else ("PASS" if item["passed"] else "FAIL"))
        lines.append(f"| `{task}` | " + " | ".join(cells) + " |")
    (ROOT / "artifacts/MATRIX.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
