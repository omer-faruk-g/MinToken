# Measurement protocol (Section E) — your own before/after, no target percentage

1. Pick 3 standard tasks (e.g. a small bug fix, a build + read the error, a code read/explain).
2. MinToken and hooks OFF: `/clear` → do the task → record the `/usage` Session block (total cost estimate, per-model input/output/cache read/cache write, `Prompt cache (main)` line).
3. MinToken and hooks ON: same tasks, same order, record the same values.
4. Compare: total cost estimate, output tokens, cache write (miss signal), tool-output-driven input. One run is noisy: at least 3 repetitions.
5. Report: "measured change: X → Y". Whatever the result is, write it; do not fit it to a target percentage.

Note: `/usage` cost is a local estimate from list prices; on a subscription the plan bars matter, not billing [D]. Usage from other devices and claude.ai is NOT included in `/usage` [D] — if the plan is shared, real consumption can be higher.
Reference from the docs: enterprise average ~$13 per developer per active day [D] — a reference, not a target.

## G5 addendum — after applying a profile

- Settings apply at session start (C8): measure in a NEW session.
- Change one setting, measure one setting, if possible.
- Record the `/usage` `Prompt cache (main)` miss / likely-cause text (v2.1.260+) and the behaviour flags (long context, cache miss).
- Result as "measured change: X → Y".

## DZ-2 — headless/SDK measurement rules [D]

- In `-p` / SDK JSON output, `usage` does NOT count subagents. For the full picture use `modelUsage` or `total_cost_usd`.
- Per-message `output_tokens` is a placeholder; read the output total from the result message.
- Parallel tool calls repeat the same message id → de-duplicate by id.
- `total_cost_usd` is a client-side estimate, not a bill.
- `model_usage` covers main loop + subagents + compaction + Workflow agents; NOT the auto-mode classifier or token-count requests (C175).

```
claude -p "<task>" --output-format json
```

## I2 — bisect order [D]

1. `claude --safe-mode` (clean baseline: no CLAUDE.md, skills, plugins, hooks, MCP, auto memory).
2. `claude plugin details <name>` — plugin always-on cost.
3. `/context` — MCP / Skills / Memory rows.
4. `/usage` — `Prompt cache (main)` row and behaviour flags (≥10%).
5. `/usage` — Loops rows.
6. `/skill-doctor`, `/doctor` — unused skills/MCP/plugins.

Org level: OTel `claude_code.token.usage` (`type`: input/output/cacheRead/cacheCreation; `query_source`: main/subagent/auxiliary). MinToken NEVER suggests `OTEL_LOG_RAW_API_BODIES` (it logs the full conversation).

## Results log

| Date | Task | Config | Cost est. | Output tok | Cache write | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |
