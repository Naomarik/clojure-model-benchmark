# Claude Code Transport

Both runners support `--transport claude`, which drives Claude Code's
noninteractive mode (`claude -p`) instead of OpenCode. The goal is an
apples-to-apples comparison of Claude models against the OpenCode-routed
models already in the development snapshot.

## Requirements

- Claude Code 2.1.216 or newer on `PATH`, authenticated (`claude` login or
  `ANTHROPIC_API_KEY`).
- Everything else matches the standard prerequisites (Python, Babashka).

## Parity with the OpenCode treatment

- **Same instructions.** The system prompt is the body of the same
  `.opencode/agent/benchmark.md` / `repl-benchmark.md` files (frontmatter
  stripped), so both transports see identical task instructions.
- **One-shot suite:** all tools disabled (`--tools ""`), fresh session per
  task, `--no-session-persistence`.
- **REPL suite:** built-in tools limited to `Bash,Read,Edit,Glob,Grep`, with
  permissions allowing only `Bash(./repl-eval:*)` plus read/edit/glob/grep
  (`--permission-mode dontAsk` denies everything else), mirroring the
  OpenCode agent permission block.
- **Hermetic sessions:** `--setting-sources ""`, `--disable-slash-commands`,
  and `--strict-mcp-config` keep user/project settings, skills, and MCP
  servers out of the run.

## Known differences (report alongside results)

- Claude Code does not expose a temperature control; the artifact records
  `"temperature": null` for claude-transport runs.
- Reasoning depth is controlled by `--effort` (`low`–`max`); reasoning cannot
  be disabled entirely. **Published runs always use `--effort low`** (the
  minimum) — see `CLAUDE.md`. The effort level is recorded in each artifact.
- Harness differs (Claude Code vs OpenCode), so scores are comparable within
  a transport and indicative across transports.

## Running the Claude model matrix

```bash
for m in claude-fable-5 claude-opus-4-8 claude-sonnet-5 claude-haiku-4-5; do
  python3 runner.py --transport claude --effort low --model "$m" --label "$m" --concurrency 4
  python3 repl_runner.py --all --transport claude --effort low --model "$m" --label "$m-repl"
done
```

Artifacts land in `artifacts/runs/` and `artifacts/repl-runs/` with the same
schema as OpenCode runs (the per-case agent output is stored under the
existing `opencode` key for matrix-tool compatibility), so `matrix.py`,
`repl_matrix.py`, and `overall_matrix.py` work unchanged.
