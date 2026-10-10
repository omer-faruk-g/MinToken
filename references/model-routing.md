# Model routing — simple decision table

Choose model and effort at SESSION START. Switching mid-session re-reads the whole history without cache (C17, C20; effort exception for Opus 5.5 / Fable 5.1 — see cache-awareness.md). If a day mixes trivial and hard work, use two sessions.

| Task | Main session | Subagent (`model:` in agent file) | Effort |
|---|---|---|---|
| Typo, rename, one-line fix, config edit | Sonnet or Haiku | — (do it inline) | low |
| Read/explain a few files, small bug | Sonnet | Haiku for search-only | low/medium |
| Build/test run + read errors | Sonnet | Haiku with `tools: Bash, Read, Grep` | low |
| Wide codebase exploration | Sonnet | Explore with `model: haiku` (C83) | low |
| Multi-file feature, refactor | Sonnet or Opus | Sonnet | medium |
| Architecture, hard debugging, security review | Opus | Sonnet for leg work | medium/high |

Facts behind the table (spec labels):
- Default model is Opus 5.5 (Pro/Max/Team/Enterprise/API); default effort medium on 5.5 models [D: C96/C170]. Forgetting Opus as default is a typical cause of unexpected spend [D: C43].
- Subagents inherit the session model unless `model:` is set; order: call parameter > frontmatter > `CLAUDE_CODE_SUBAGENT_MODEL` > main model; `_FORCE=1` makes the env var win (v2.1.257+) [D: DZ-7].
- Thinking cannot be turned off on Opus/Sonnet/Haiku 5.5 and Fable; non-zero `MAX_THINKING_TOKENS` is ignored by adaptive models → use `/effort` [D: C44/C170].
- `max` effort tends to over-think [D: C96].
- Background jobs (titles, summaries, /goal judge) use the Haiku slot; if `ANTHROPIC_DEFAULT_HAIKU_MODEL` points to an expensive model, all of them are expensive [D: C97/C129].
- Fast mode is billed from usage credits on subscriptions; fast-mode page (checked 2026-10-10): $8/$40 per MTok on Opus 5.5, $10/$50 on Opus 5 / 4.8 (DZ-11) — re-check before quoting.

Subagent template (C84 — suggestion; removing tools a task needs makes it fail):
```yaml
---
name: quick-search
description: Search the codebase and report file paths + one-line findings.
model: haiku
tools: Read, Grep, Glob
maxTurns: 15
effort: low
---
Return only paths and a ≤10-line summary.
```
