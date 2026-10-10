---
name: mintoken
description: "Independent token/usage reduction skill: filter long build/log output, set scoped deny rules, audit installed token tools (Headroom/Graphify/Ponytail/claude-mem/ECC/SkillSpector), explain hidden token drains and cache behavior. Use when the user asks about token use, usage limits, cost, slow or expensive turns, cache misses, long or stuck sessions, or build/log output over 200 lines."
aliases: [token-saver, token-tasarruf]
---

# MinToken

MinToken has no external dependencies; it also patches the gaps of Headroom/Graphify/Ponytail/claude-mem/ECC/SkillSpector when installed.
Scripts: Python stdlib only, no network, all support `--help` and `--dry-run`. Paths below are relative to this skill's directory.

## Ground rules
- **Labels.** [D] verified in official docs · [G] observed in tool definitions/environment · [R] third-party report — unverified · [I] inference — unverified. Never present [R]/[I] as fact; say "unverified".
- **Verify before writing.** Before writing a settings key, env var, hook schema or slash command, re-read the docs page (index: `https://code.claude.com/docs/llms.txt`). Claude Code changes between releases; never write from memory.
- **No percentage claims.** Never promise "X% savings". Use `references/measurement.md` so the user gets their own "measured change: X → Y".
- **Consent.** Never change settings.json, hooks, permissions or any config without showing a diff and getting an explicit "yes/evet". Never install/remove other skills, plugins or tools. Managed/org policy: report only.
- **Make the invisible visible.** Most waste is where the user does not look: status line, `/usage`, `/context`, the drain catalog.
- Prefer hedged wording ("prefer / if possible / by default") over absolutes. Every suggestion states its cost (lost feature/accuracy).

## Tools: installed → patch the gap · missing → do the job (A1–A6)
Run `python scripts/audit_tools.py` (read-only, 3 sections).

| Tool | Installed | Not installed |
|---|---|---|
| Headroom | HEADROOM_BEACON (telemetry default on [R]); OUTPUT_SHAPER default off [R]; model routing enterprise-only [R]; prefix not compressed → B4 | `filter_log.py` + D1 hook; keep only needed fields of 100+ line JSON/grep |
| Graphify | deny `Read(graphify-out/**)`; graph.json > 500 KB → `graphify query`, keep node name + path; `--code-only` | Grep → Read(offset/limit); narrow `find … \| head -20`; LSP plugin [D] |
| Ponytail | injected every turn + subagents [R]; `/ponytail lite` or `off` for trivial edits | YAGNI ladder: needed? exists? stdlib? installed dep? one line? → minimum code (security/validation/a11y exempt) |
| claude-mem | observer = model calls on your plan [R]; check CLAUDE_MEM_ONLINE_OPTIN; measure SessionStart injection | 1–2 line dated notes in CLAUDE.md, < 200 lines [D]; loads at start / after /clear, /compact [D] |
| ECC | ≥15 agents/rules/commands → descriptions every turn; unscoped rules load every session [D]; MCP schemas deferred now [D]; source repo mismatch [G] | compact → B4, memory → A4, routing → `references/model-routing.md`, MCP → B7 |
| SkillSpector | `skillspector scan <dir> --no-llm` before installs | read README/files: network, hooks, file access, deps, obfuscation |

## Working rules (B1–B15)
- **B1** Internal notes/plans/comments/CLAUDE.md notes in English; reply in the user's language, short. ASCII identifiers.
- **B2** Only scoped deny rules (`Read(build/**)`) via `scripts/suggest_deny_rules.py`. Never deny a bare tool name. `.claudeignore` has no effect [D].
- **B3** Never read 200+ raw lines of build/log output: `cmd 2>&1 | python scripts/filter_log.py` (or D1 hook). Raw: `MINTOKEN_RAW=1`.
- **B4** Suggest, in one sentence (you cannot run slash commands): topic changed → `/clear` (rename first); 15+ turns or bloated → `/compact <keep what>` at a natural break; wrong path → `/rewind` [D]. Do not repeat a suggestion.
- **B5** 20 tool calls without a user message → stop, 3-line summary, ask. Same error twice → stop, root cause, change method. Same file 3rd read → stop. Deterministic version: D2 hook.
- **B6** Failed Edit → widen old_string once; second failure → root cause in 3 lines, change method or ask. Vague task → one clarifying question before touching code; big task → plan mode.
- **B7** MCP schemas are deferred by default [D]; only names + server instructions sit in context. Real numbers: `/context`, `/mcp`. CLIs (gh, aws) are cheaper than MCP [D].
- **B8** Subagents start cold (own CLAUDE.md/MCP/skills, no parent cache) [D]. Not for short work; narrow task, summary only, `model: haiku` for simple jobs, prompt ≤ 10 lines. Do give them heavy-output work (tests, logs).
- **B9** Prefer Edit over Write; show only changed parts; 1–2 sentence wrap-up.
- **B10/B15** Cache breakers and TTL buckets → `references/cache-awareness.md`. Pick model/effort at session start.
- **B11** Task lists only for 3+ steps; take only what you need from WebFetch/WebSearch.
- **B12** "Why did my limit run out?" → `/usage` flags + attribution first, then drains. `/usage` excludes claude.ai and other devices [D] — ask.
- **B13** No "long-context price tier" claim. `CONTEXT_SIZE_WARN` (config.md) is a hygiene threshold.
- **B14** The tokenizer cannot be changed; reduce the worst content (B1, filter_log.py). `--estimate-tokens` = chars/4, rough.

## Hidden drain catalog (178 items, Turkish, labelled)
- C1–C50 `references/hidden-drains.md` · C51–C114 `references/hidden-drains-2.md` · C115–C178 `references/hidden-drains-3.md`
- `python scripts/audit_tools.py --drains` (C1–50) · `--drains2` (C51–114) · `--drains all` (C1–114) · `--drains3` (C115–178) · `--drain N` (1–178)
- Read only the item you need; do not load whole catalogs into context.

## Scripts
| Script | Purpose |
|---|---|
| `scripts/filter_log.py` | filter build/log/stack traces; UUID/HASH/HEX/B64 shortening with mapping file; `--estimate-tokens` (rough) |
| `scripts/suggest_deny_rules.py` | propose scoped `Read(...)` deny rules; diff; writes only with `--apply` + explicit yes |
| `scripts/audit_tools.py` | 6-tool audit (installed / missing / general) + drain catalog |
| `scripts/audit_config.py` | read-only settings/env/hooks/skills/CLAUDE.md audit; `--profile safe/medium/aggressive` (suggestions only) |
| `scripts/install_hooks.py` | diff for D1/D2/D3/G2 into `~/.claude/settings.json`; dry-run default; backup; `--uninstall` |
| `scripts/statusline_mintoken.py` | D3 status line: `ctx 38% · cache 91% · warm 1h (42m left) · miss 2 (cause)` |
| `scripts/hooks/pretool_bash_filter.py` | D1 PreToolUse(Bash): pipes gradle/mvn/npm test/pytest/go test output through filter_log.py; exit code via PIPESTATUS[0]; raw output if the filter fails; returns `ask`, never `allow` |
| `scripts/hooks/session_counter.py` | D2 optional runaway brake (tool count, re-reads, repeated errors) |
| `scripts/hooks/resume_cost_guard.py` | G2 optional SessionStart(resume/fork) cold-cache warning via `systemMessage`, ≤300 chars |

Hook caveats: D1 only sees the **Bash** tool (not PowerShell). These are command hooks: no model calls, no context cost except what they print.

## Typical flows
1. "Tokens/limit going fast" → B12 → `python scripts/audit_config.py` → `python scripts/audit_tools.py` → relevant drains → suggest one change → measure.
2. Long build output → filter_log.py now; offer `install_hooks.py --only d1` (diff + approval).
3. Before installing a new tool → A6 (scan or manual review).
4. Settings tuning → `audit_config.py --profile safe` → user picks → diff → explicit yes → new session → measure.

## Platform-level items (MinToken cannot change them)
TTL values, plan pool shared with claude.ai/other devices, limit weighting, tokenizer, classifier/background requests, managed policy. MinToken handles them by **monitoring** (D3 status line, `/usage` guide in `references/context-audit-checklist.md`), **warning** (G2, audits) and **setting suggestions** (`references/settings-cheatsheet.md`, profiles). Thresholds: `references/config.md`. Tool sizes: `references/tool-overhead.md`.
