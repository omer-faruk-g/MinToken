# Tool overhead (rough estimates — labelled)

All numbers here are **rough**: file bytes / 4, not a tokenizer. Real numbers: `/context` (Skills, MCP tools, Memory files lines), `claude plugin details <name>` ("Always-on" line), `/usage` attribution.

Two different costs — do not mix them up:
1. **Always-on**: the skill/agent/command *description* listed every turn (C7, C52, C53, C135).
2. **When invoked**: the SKILL.md body, which then stays in context for the rest of the session (C64) and is partly re-attached after compaction (first 5,000 tokens per skill, 25,000 total — C63).

Example snapshot measured on the author's machine (2026-10-10). Run `python scripts/audit_tools.py` to get yours:

| Tool | Detected | Always-on (rough) | When invoked (rough) | Notes |
|---|---|---|---|---|
| Ponytail (6 skills) | yes | part of ~472 tok for all 19 user skill descriptions | ~4,600 tok for all six SKILL.md bodies | README says rules are injected every turn and into subagents [R] — verify with /context |
| Graphify | yes | (in the 472 above) | ~11,300 tok SKILL.md body | big body: invoke only when needed |
| claude-mem | yes (plugin) | SessionStart injection measured from the latest transcript: ~721 tok (rough) per session start/clear/compact | — | observer model calls use your plan (provider=claude, auth=subscription) [R] |
| everything-claude-code | yes | 9 agents + 15 commands + its skills: descriptions every turn | per agent/command | 15 commands ≥ warning threshold |
| SkillSpector | yes (CLI) | 0 (CLI, not loaded into context) | 0 | run with --no-llm |
| Headroom | no | — | — | MinToken D1 hook + filter_log.py replace it |
| MinToken | yes | its description (~120 tok) | SKILL.md ≤150 lines | references/ load only on demand |

Re-run `python scripts/audit_tools.py` after installing or removing tools; this table is a snapshot.
