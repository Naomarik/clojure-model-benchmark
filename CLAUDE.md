# Benchmark conventions

- **Claude-transport runs always use `--effort low`.** Claude Code has no way
  to disable reasoning entirely; `low` is the minimum effort level, so it is
  the canonical setting for all published Claude runs (one-shot and REPL).
  The effort level is recorded in every run artifact; runs made at any other
  effort must not be mixed into published tables.
- Claude runs use `--transport claude` on `runner.py` / `repl_runner.py`.
  See `docs/CLAUDE_TRANSPORT.md` for the parity notes and known differences
  vs the OpenCode transport (no temperature control, different harness).
- Canonical Claude model IDs for published runs: `claude-fable-5`,
  `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5`.
