#!/usr/bin/env python3
"""Prove every fixture is buggy and every reference overlay passes."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from repl_cases import CASES
from repl_runner import BB, CASES_ROOT, CLASSPATH, overlay_reference


def run(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BB, "--classpath", CLASSPATH, *args], cwd=workspace,
        capture_output=True, text=True, timeout=60,
    )


def main() -> None:
    for case in CASES:
        with tempfile.TemporaryDirectory(prefix=f"validate-{case.slug}-") as tmp:
            workspace = Path(tmp) / "workspace"
            shutil.copytree(CASES_ROOT / case.slug / "public", workspace)
            loaded = run(workspace, "-e", case.bootstrap)
            if loaded.returncode != 0:
                raise SystemExit(f"{case.slug}: fixture does not load\n{loaded.stderr}")
            grader = str(CASES_ROOT / case.slug / "grader/grader.clj")
            buggy = run(workspace, grader)
            if buggy.returncode == 0:
                raise SystemExit(f"{case.slug}: buggy fixture unexpectedly passed")
            overlay_reference(case, workspace)
            reference = run(workspace, grader)
            if reference.returncode != 0:
                raise SystemExit(
                    f"{case.slug}: reference failed\n{reference.stdout}\n{reference.stderr}"
                )
            print(f"PASS {case.slug}: loads, buggy fails, reference passes")


if __name__ == "__main__":
    main()
