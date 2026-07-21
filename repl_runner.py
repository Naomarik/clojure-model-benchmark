#!/usr/bin/env python3
"""Run isolated, stateful Clojure debugging cases through OpenCode or Claude Code."""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from repl_cases import CASE_BY_SLUG, CASES, ReplCase

ROOT = Path(__file__).resolve().parent
CASES_ROOT = ROOT / "repl-cases"
RUNS_ROOT = ROOT / "artifacts/repl-runs"
BB = os.environ.get("BB") or shutil.which("bb") or "bb"
CLASSPATH = os.pathsep.join(("src", "resources"))
SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
PROTOCOL_HASH_DOMAIN = b"clojure-model-benchmark-protocol-v1"


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for base in (root / "src", root / "resources"):
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def source_diff(baseline: Path, workspace: Path) -> str:
    relative_paths = set()
    for root in (baseline, workspace):
        for base_name in ("src", "resources"):
            base = root / base_name
            if base.exists():
                relative_paths.update(
                    path.relative_to(root) for path in base.rglob("*") if path.is_file()
                )
    chunks = []
    for relative in sorted(relative_paths):
        before_path, after_path = baseline / relative, workspace / relative
        before = before_path.read_text().splitlines(keepends=True) if before_path.exists() else []
        after = after_path.read_text().splitlines(keepends=True) if after_path.exists() else []
        chunks.extend(difflib.unified_diff(
            before, after, fromfile=f"a/{relative}", tofile=f"b/{relative}"
        ))
    return "".join(chunks)


def suite_hash() -> str:
    digest = hashlib.sha256()
    paths = [ROOT / "repl_cases.py", ROOT / ".opencode/agent/repl-benchmark.md"]
    paths.extend(sorted(path for path in CASES_ROOT.rglob("*") if path.is_file()))
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def protocol_hash() -> str:
    """Hash the canonical REPL treatment using length-delimited entries."""
    digest = hashlib.sha256()
    paths = [
        ROOT / "repl_runner.py",
        ROOT / "repl_eval.py",
        ROOT / "repl_cases.py",
        ROOT / ".opencode/agent/repl-benchmark.md",
        ROOT / ".opencode/opencode.json",
    ]
    paths.extend(path for path in CASES_ROOT.rglob("*") if path.is_file())

    def update(value: bytes) -> None:
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)

    update(PROTOCOL_HASH_DOMAIN)
    for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix()):
        update(path.relative_to(ROOT).as_posix().encode())
        update(path.read_bytes())
    return digest.hexdigest()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def receive_prompt(sock: socket.socket) -> str:
    data = bytearray()
    while not data.endswith(b"=> "):
        chunk = sock.recv(65536)
        if not chunk:
            break
        data.extend(chunk)
    return data.decode(errors="replace")


def socket_eval(port: int, code: str) -> str:
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.settimeout(8)
        receive_prompt(sock)
        sock.sendall(code.encode() + b"\n")
        return receive_prompt(sock)


def wait_ready(port: int, process: subprocess.Popen, timeout: float = 8) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"REPL exited early with {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=.2):
                return
        except OSError:
            time.sleep(.05)
    raise RuntimeError("REPL did not become ready")


def start_repl(workspace: Path, log_handle):
    port = free_port()
    process = subprocess.Popen(
        [BB, "--classpath", CLASSPATH, "socket-repl", f"127.0.0.1:{port}"],
        cwd=workspace,
        stdin=subprocess.PIPE,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        wait_ready(port, process)
    except Exception:
        stop_group(process)
        raise
    return process, port


def stop_group(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)


def agent_system_prompt() -> str:
    """Return the repl-benchmark agent instructions without YAML frontmatter."""
    text = (ROOT / ".opencode/agent/repl-benchmark.md").read_text()
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            text = text[end + 4:]
    return text.strip()


def extract_claude_text(stdout: str) -> str:
    start = stdout.find("{")
    if start < 0:
        return ""
    try:
        payload = json.loads(stdout[start:])
    except json.JSONDecodeError:
        return ""
    result = payload.get("result")
    return result if isinstance(result, str) else ""


def run_agent_cli(command: list[str], workspace: Path, env: dict, timeout: float,
                  transport: str) -> dict:
    process = subprocess.Popen(
        command, cwd=workspace, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    extractor = extract_claude_text if transport == "claude" else extract_text
    return {
        "exit_code": None if timed_out else process.returncode,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
        "assistant_text": extractor(stdout),
    }


def prepare_workspace(case: ReplCase, root: Path) -> Path:
    workspace = root / "workspace"
    shutil.copytree(CASES_ROOT / case.slug / "public", workspace)
    agent_dir = workspace / ".opencode/agent"
    agent_dir.mkdir(parents=True)
    shutil.copy2(ROOT / ".opencode/agent/repl-benchmark.md", agent_dir)
    project_config = ROOT / ".opencode/opencode.json"
    if project_config.exists():
        shutil.copy2(project_config, workspace / ".opencode/opencode.json")
    shutil.copy2(ROOT / "repl_eval.py", workspace / "repl-eval")
    (workspace / "repl-eval").chmod(0o755)
    return workspace


def overlay_reference(case: ReplCase, workspace: Path) -> None:
    reference = CASES_ROOT / case.slug / "reference"
    for path in reference.rglob("*"):
        if path.is_file():
            target = workspace / path.relative_to(reference)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def grade(case: ReplCase, workspace: Path) -> dict:
    grader = CASES_ROOT / case.slug / "grader/grader.clj"
    completed = subprocess.run(
        [BB, "--classpath", CLASSPATH, str(grader)],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def repl_usage(case: ReplCase, events: list[dict], initial_hash: str) -> dict:
    diagnostic_words = ("meta", "source", "methods", "macroexpand", "@", "class", "type")
    project_events = [
        event for event in events
        if case.namespace in event.get("code", "")
        and not event.get("code", "").lstrip().startswith("(require")
    ]
    post_edit = [event for event in project_events if event.get("source_sha256") != initial_hash]
    diagnostic = [event for event in project_events
                  if any(word in event.get("code", "") for word in diagnostic_words)]
    points = sum((bool(events), bool(project_events), bool(diagnostic), bool(post_edit)))
    return {
        "score": points,
        "max_score": 4,
        "connected": bool(events),
        "project_evaluation": bool(project_events),
        "diagnostic_evaluation": bool(diagnostic),
        "post_edit_evaluation": bool(post_edit),
        "meaningful": bool(project_events and post_edit),
        "evaluations": events,
    }


def extract_text(stdout: str) -> str:
    parts = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part", {})
        if isinstance(part, dict) and part.get("type") == "text":
            parts.append(part.get("text", ""))
        elif event.get("type") == "text" and isinstance(part, dict):
            parts.append(part.get("text", ""))
    return "".join(parts)


def run_case(case: ReplCase, model: str, timeout_override: float | None = None,
             transport: str = "opencode", effort: str | None = None) -> dict:
    started = time.perf_counter()
    process = None
    with tempfile.TemporaryDirectory(prefix=f"repl-bench-{case.slug}-") as tmp:
        runtime = Path(tmp)
        workspace = prepare_workspace(case, runtime)
        baseline = runtime / "baseline"
        eval_log = runtime / "evaluations.jsonl"
        server_log = runtime / "server.log"
        initial_hash = tree_hash(workspace)
        with server_log.open("w") as server_output:
            try:
                process, port = start_repl(workspace, server_output)
                bootstrap_response = socket_eval(port, case.bootstrap)
                if "Exception" in bootstrap_response or "Could not" in bootstrap_response:
                    raise RuntimeError(f"bootstrap failed: {bootstrap_response}")
                for relative, content in (case.mutate_after_bootstrap or {}).items():
                    (workspace / relative).write_text(content)
                initial_hash = tree_hash(workspace)
                shutil.copytree(workspace, baseline)

                prompt = (
                    case.prompt + "\n\n"
                    "The REPL is already running. Evaluate one form at a time with "
                    "`./repl-eval '(FORM ...)'`. Work only in this directory; grader tests "
                    "are unavailable. Do not merely propose a patch: edit the source and verify it."
                )
                env = os.environ.copy()
                env.update({
                    "REPL_HOST": "127.0.0.1",
                    "REPL_PORT": str(port),
                    "REPL_EVAL_LOG": str(eval_log),
                    "REPL_WORKSPACE": str(workspace),
                })
                if transport == "claude":
                    command = [
                        "claude", "-p", "--output-format", "json",
                        "--model", model,
                        "--no-session-persistence",
                        "--setting-sources", "",
                        "--disable-slash-commands",
                        "--strict-mcp-config",
                        "--system-prompt", agent_system_prompt(),
                        "--tools", "Bash,Read,Edit,Glob,Grep",
                        "--allowedTools", "Bash(./repl-eval:*)", "Read", "Edit", "Glob", "Grep",
                        "--permission-mode", "dontAsk",
                    ]
                    if effort:
                        command += ["--effort", effort]
                    command.append(prompt)
                else:
                    env.update({
                        "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
                        "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
                    })
                    command = [
                        "opencode", "run", "--pure", "--format", "json",
                        "--agent", "repl-benchmark", "--model", model,
                        "--dir", str(workspace), prompt,
                    ]
                timeout = timeout_override or case.timeout
                opencode = run_agent_cli(command, workspace, env, timeout, transport)
            except Exception as error:  # failures belong in the case artifact
                opencode = {
                    "exit_code": None, "timed_out": False,
                    "stdout": "", "stderr": f"{type(error).__name__}: {error}",
                    "assistant_text": "",
                }
            finally:
                stop_group(process)

        if not baseline.exists():
            shutil.copytree(workspace, baseline)
        grader = grade(case, workspace)
        events = read_events(eval_log)
        usage = repl_usage(case, events, initial_hash)
        return {
            "case": case.slug,
            "difficulty": case.difficulty,
            "prompt": case.prompt,
            "elapsed_s": time.perf_counter() - started,
            "correctness": {"score": int(grader["passed"]), "max_score": 1, **grader},
            "repl_usage": usage,
            "opencode": opencode,
            "initial_tree_sha256": initial_hash,
            "final_tree_sha256": tree_hash(workspace),
            "source_diff": source_diff(baseline, workspace),
            "server_log": server_log.read_text() if server_log.exists() else "",
        }


def smoke_case(case: ReplCase) -> dict:
    process = None
    with tempfile.TemporaryDirectory(prefix=f"repl-smoke-{case.slug}-") as tmp:
        runtime = Path(tmp)
        workspace = prepare_workspace(case, runtime)
        eval_log = runtime / "evaluations.jsonl"
        with (runtime / "server.log").open("w") as output:
            try:
                process, port = start_repl(workspace, output)
                before = socket_eval(port, case.bootstrap)
                overlay_reference(case, workspace)
                env = os.environ.copy()
                env.update({
                    "REPL_HOST": "127.0.0.1", "REPL_PORT": str(port),
                    "REPL_EVAL_LOG": str(eval_log),
                    "REPL_WORKSPACE": str(workspace),
                })
                client = subprocess.run(
                    [str(workspace / "repl-eval"),
                     f"(do (require '{case.namespace} :reload) {case.bootstrap} :reloaded)"],
                    cwd=workspace, env=env, capture_output=True, text=True, timeout=15,
                )
                after = client.stdout
                if client.returncode != 0:
                    raise RuntimeError(f"repl-eval failed: {client.stderr}")
            finally:
                stop_group(process)
        result = grade(case, workspace)
        result.update({
            "case": case.slug, "bootstrap": before, "reload": after,
            "evaluations": read_events(eval_log),
        })
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case", choices=CASE_BY_SLUG)
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--label")
    parser.add_argument(
        "--transport", choices=("opencode", "claude"), default="opencode",
        help="Noninteractive CLI to drive: OpenCode or Claude Code",
    )
    parser.add_argument(
        "--effort", choices=("low", "medium", "high", "xhigh", "max"),
        help="Claude Code effort level (claude transport only; omit for CLI default)",
    )
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--smoke", action="store_true", help="Use references without a model")
    args = parser.parse_args()
    selected = CASES if args.all else [CASE_BY_SLUG[args.case]]

    if args.smoke:
        results = [smoke_case(case) for case in selected]
        for result in results:
            print(f"{'PASS' if result['passed'] else 'FAIL'} {result['case']}")
        return 0 if all(result["passed"] for result in results) else 1

    if not args.model or not args.label:
        parser.error("--model and --label are required unless --smoke is used")
    if not SAFE_LABEL.fullmatch(args.label):
        parser.error("--label must contain only letters, numbers, dots, dashes, or underscores")
    if args.timeout is not None and args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.effort and args.transport != "claude":
        parser.error("--effort only applies to --transport claude")
    artifact_path = RUNS_ROOT / f"{args.label}.json"
    artifact = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": args.label,
        "model": args.model,
        "transport": args.transport,
        "effort": args.effort,
        "suite": "agentic-clojure-repl",
        "suite_sha256": suite_hash(),
        "protocol_sha256": protocol_hash(),
        "results": [],
    }
    write_json(artifact_path, artifact)
    for case in selected:
        print(f"Running {case.slug} ({case.difficulty})", flush=True)
        result = run_case(case, args.model, args.timeout, args.transport, args.effort)
        artifact["results"].append(result)
        write_json(artifact_path, artifact)
        print(
            f"  correctness={result['correctness']['score']}/1 "
            f"repl={result['repl_usage']['score']}/4 "
            f"elapsed={result['elapsed_s']:.1f}s",
            flush=True,
        )
    print(f"Wrote {artifact_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
