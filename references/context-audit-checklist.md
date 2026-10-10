# Reading /context and /usage (checklist)

## /context — what is in the window now
| Row | Fixed or growing | If large |
|---|---|---|
| System prompt / tools | fixed per session | bare-name denies remove tools (C160); `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT` etc. only as an approved, reversible trial (C169) |
| MCP tools | fixed | deferred by default: only names + server instructions [D]. Big here → tool search off (gateway `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`, `ENABLE_TOOL_SEARCH=false/auto`) or `alwaysLoad` (C5, C6, C127, C173). Close unused servers in `/mcp`. |
| Skills | fixed | descriptions only; trim with `skillOverrides` name-only / `disable-model-invocation` (C52, C126, C167) |
| Memory files | fixed | CLAUDE.md chain + MEMORY.md; keep CLAUDE.md < 200 lines; `claudeMdExcludes` for unrelated parents (C8, C55, C56) |
| Custom agents | fixed | > 15,000 tokens of descriptions → startup warning (C53, C125) |
| Messages | grows | tool output is the usual culprit → filter_log.py / D1 hook, offset/limit, `/compact <focus>` or `/clear` |

Rule of thumb: if a fresh session (after `/clear`) is already big, the problem is fixed load (rows 1–5). If it grows fast, it is tool output (row 6). `/clear` and still thrashing → compare Messages vs startup rows (H2).

## /usage — why the limit went
1. Session block: model split, input/output, cache read/write. High cache write with few turns = misses.
2. `Prompt cache (main)` (v2.1.251+): requests, % from cache, misses, likely cause (v2.1.260+).
3. Behaviour flags ≥10% (long context, cache miss) — Pro/Max/Team/Enterprise.
4. Attribution: skill / subagent / plugin / MCP server shares.
5. Loops rows: most expensive /loop jobs (v2.1.242+).
6. Remember: claude.ai and other devices are NOT in `/usage` [D]. Ask "did you use claude.ai heavily?"

Then walk the drain catalog: `python scripts/audit_tools.py --drains all`, and settings: `python scripts/audit_config.py`.

## Hygiene threshold
`CONTEXT_SIZE_WARN` (config.md, default 100000) is a hygiene threshold, not a price tier (B13). Above it, suggest `/compact <focus>` at a natural break or `/clear` on topic change.
