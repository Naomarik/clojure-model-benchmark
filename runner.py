#!/usr/bin/env python3
"""Run the bundled Clojure eval through a noninteractive CLI (OpenCode or Claude Code)."""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SUITE = ROOT / "suites/eval_clojure.py"
RUNS_DIR = ROOT / "artifacts/runs"
SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
PROTOCOL_HASH_DOMAIN = b"clojure-model-benchmark-protocol-v1"
PROTOCOL_PATHS = (
    ROOT / "runner.py",
    ROOT / "suites/eval_clojure.py",
    ROOT / ".opencode/agent/benchmark.md",
    ROOT / ".opencode/opencode.json",
)


def protocol_hash() -> str:
    """Hash the canonical one-shot treatment using length-delimited entries."""
    digest = hashlib.sha256()

    def update(value: bytes) -> None:
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)

    update(PROTOCOL_HASH_DOMAIN)
    for path in sorted(PROTOCOL_PATHS, key=lambda item: item.relative_to(ROOT).as_posix()):
        update(path.relative_to(ROOT).as_posix().encode())
        update(path.read_bytes())
    return digest.hexdigest()


def load_suite(path: Path):
    spec = importlib.util.spec_from_file_location("canonical_eval_clojure", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import suite: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def suite_provenance(path: Path) -> str:
    """Use a stable repository-relative path without leaking host paths."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def agent_system_prompt(name: str) -> str:
    """Read an OpenCode agent file and return its body without YAML frontmatter.

    Both transports use the same instruction text so runs stay comparable.
    """
    text = (ROOT / f".opencode/agent/{name}.md").read_text()
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            text = text[end + 4:]
    return text.strip()


def extract_claude_text(stdout: str) -> tuple[str, dict]:
    """Extract the final assistant text from `claude -p --output-format json`."""
    start = stdout.find("{")
    if start < 0:
        raise RuntimeError("Claude Code returned no JSON result")
    payload = json.loads(stdout[start:])
    if payload.get("is_error"):
        raise RuntimeError(f"Claude Code error: {str(payload.get('result'))[:500]}")
    result = payload.get("result")
    if not isinstance(result, str) or not result:
        raise RuntimeError("Claude Code returned no assistant text")
    return result, payload


def ask_claude(model: str, prompt: str, timeout: float, effort: str | None) -> tuple[str, str]:
    command = [
        "claude", "-p", "--output-format", "json",
        "--model", model,
        "--tools", "",
        "--no-session-persistence",
        "--setting-sources", "",
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--system-prompt", agent_system_prompt("benchmark"),
    ]
    if effort:
        command += ["--effort", effort]
    command.append(prompt)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Claude Code exited {completed.returncode}: {detail[-500:]}")
    text, _ = extract_claude_text(completed.stdout)
    return text, completed.stdout


def extract_text(stdout: str) -> str:
    """Collect assistant text parts from OpenCode's JSONL event stream."""
    parts = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part", {})
        if event.get("type") == "text" and isinstance(part.get("text"), str):
            parts.append(part["text"])
        elif part.get("type") == "text" and isinstance(part.get("text"), str):
            parts.append(part["text"])
    if not parts:
        raise RuntimeError("OpenCode returned no assistant text events")
    return "".join(parts)


def extract_export_text(stdout: str) -> str:
    """Extract final assistant text from `opencode export` output."""
    start = stdout.find("{")
    if start < 0:
        raise RuntimeError("OpenCode export returned no JSON object")
    exported = json.loads(stdout[start:])
    for message in reversed(exported.get("messages", [])):
        if message.get("info", {}).get("role") != "assistant":
            continue
        parts = [
            part.get("text", "")
            for part in message.get("parts", [])
            if part.get("type") == "text"
        ]
        if parts:
            return "".join(parts)
    raise RuntimeError("OpenCode export contained no assistant text")


def ask(model: str, prompt: str, timeout: float) -> tuple[str, str]:
    env = os.environ.copy()
    env.update({
        "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
        "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
    })
    command = [
        "opencode", "run", "--pure", "--format", "json",
        "--agent", "benchmark", "--model", model, "--dir", str(ROOT), prompt,
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"OpenCode exited {completed.returncode}: {detail[-500:]}")
    try:
        return extract_text(completed.stdout), completed.stdout
    except RuntimeError:
        session_id = None
        for line in completed.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("sessionID"):
                session_id = event["sessionID"]
                break
        if not session_id:
            raise
        exported = subprocess.run(
            ["opencode", "export", session_id],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=min(timeout, 60),
        )
        if exported.returncode != 0:
            raise RuntimeError(
                f"OpenCode returned no text and export failed: {exported.stderr.strip()}"
            )
        text = extract_export_text(exported.stdout)
        raw = completed.stdout + "\n# opencode export fallback\n" + exported.stdout
        return text, raw


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Model ID for the chosen transport")
    parser.add_argument(
        "--transport", choices=("opencode", "claude"), default="opencode",
        help="Noninteractive CLI to drive: OpenCode or Claude Code",
    )
    parser.add_argument(
        "--effort", choices=("low", "medium", "high", "xhigh", "max"),
        help="Claude Code effort level (claude transport only; omit for CLI default)",
    )
    parser.add_argument("--label", required=True, help="Filesystem-safe run label")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--timeout", type=float, default=300.0, help="Seconds per task")
    parser.add_argument("--concurrency", type=int, default=1, help="Parallel task requests")
    parser.add_argument("--only", action="append", help="Run only named task(s)")
    args = parser.parse_args()
    if not SAFE_LABEL.fullmatch(args.label):
        parser.error("--label must contain only letters, numbers, dots, dashes, or underscores")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    if args.effort and args.transport != "claude":
        parser.error("--effort only applies to --transport claude")

    suite_path = args.suite.resolve()
    provenance = suite_provenance(suite_path)
    suite_bytes = suite_path.read_bytes()
    suite_sha256 = hashlib.sha256(suite_bytes).hexdigest()
    suite = load_suite(suite_path)
    selected = [task for task in suite.TASKS if not args.only or task[0] in args.only]
    if args.only and len(selected) != len(set(args.only)):
        known = {task[0] for task in suite.TASKS}
        missing = sorted(set(args.only) - known)
        raise SystemExit(f"unknown task(s): {', '.join(missing)}")

    snapshot = {
        "canonical_suite": provenance,
        "canonical_suite_sha256": suite_sha256,
        "protocol_sha256": protocol_hash(),
        "total": len(suite.TASKS),
        "tasks": [{"task": name, "prompt": prompt} for name, prompt, _ in suite.TASKS],
    }
    write_json(ROOT / "artifacts/tests.json", snapshot)

    out_path = RUNS_DIR / f"{args.label}.json"
    result = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": args.label,
        "transport": (
            "opencode run --pure --format json --agent benchmark"
            if args.transport == "opencode"
            else "claude -p --output-format json --tools ''"
        ),
        "model": args.model,
        "effort": args.effort,
        "canonical_suite": provenance,
        "canonical_suite_sha256": suite_sha256,
        "protocol_sha256": protocol_hash(),
        "temperature": 0 if args.transport == "opencode" else None,
        "concurrency": args.concurrency,
        "fresh_session_per_task": True,
        "score": 0,
        "total": len(selected),
        "results": [],
    }
    write_json(out_path, result)

    print(f"Running {len(selected)} tasks: {args.model} ({args.label})", flush=True)
    def evaluate(task):
        name, prompt, checker = task
        started = time.perf_counter()
        raw_events = None
        try:
            if args.transport == "claude":
                response, raw_events = ask_claude(args.model, prompt, args.timeout, args.effort)
            else:
                response, raw_events = ask(args.model, prompt, args.timeout)
            passed, detail = checker(response)
        except Exception as error:  # noqa: BLE001 - failures belong in the artifact
            response = None
            passed = False
            detail = f"request error: {type(error).__name__}: {error}"
        elapsed = time.perf_counter() - started
        return {
            "task": name,
            "passed": bool(passed),
            "detail": detail,
            "elapsed_s": elapsed,
            "response": response,
            "opencode_jsonl": raw_events,
        }

    completed_results = {}
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {executor.submit(evaluate, task): task[0] for task in selected}
        for future in as_completed(futures):
            item = future.result()
            completed_results[item["task"]] = item
            result["results"] = [
                completed_results[name]
                for name, _, _ in selected
                if name in completed_results
            ]
            result["score"] = sum(entry["passed"] for entry in result["results"])
            write_json(out_path, result)
            status = "PASS" if item["passed"] else "FAIL"
            print(
                f"  {status} {item['task']:<26} {item['elapsed_s']:6.1f}s  {item['detail']}",
                flush=True,
            )

    print(f"Score: {result['score']}/{result['total']}", flush=True)
    print(f"Wrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
