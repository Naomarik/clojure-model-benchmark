#!/usr/bin/env python3
"""Small logged client for a Babashka socket REPL."""

import hashlib
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for base in (root / "src", root / "resources"):
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def receive_prompt(sock: socket.socket) -> str:
    chunks = []
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
        if b"=> " in chunk and b"".join(chunks).rstrip().endswith(b"=>"):
            break
        if b"".join(chunks).endswith(b"=> "):
            break
    return b"".join(chunks).decode(errors="replace")


def main() -> int:
    code = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else sys.stdin.read().strip()
    if not code:
        raise SystemExit("usage: repl-eval 'FORM'")
    host = os.environ["REPL_HOST"]
    port = int(os.environ["REPL_PORT"])
    started = time.perf_counter()
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.settimeout(8)
        receive_prompt(sock)
        sock.sendall(code.encode() + b"\n")
        response = receive_prompt(sock)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "code": code,
        "response": response,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "source_sha256": tree_hash(Path(os.environ["REPL_WORKSPACE"])),
    }
    log_path = Path(os.environ["REPL_EVAL_LOG"])
    with log_path.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")
    print(response, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
