# MinToken

A Claude Code skill that makes hidden token use visible and gives you concrete, reversible ways to reduce it. It works on its own and also patches gaps in Headroom, Graphify, Ponytail, claude-mem, everything-claude-code and SkillSpector when those are installed.

- **No percentage promises.** MinToken never claims "X% savings". It ships a measurement protocol so you get your own before/after number.
- **Nothing changes silently.** Every settings, hook or permission change is shown as a diff first and is written only after an explicit `yes`/`evet`, with a timestamped backup.
- **Labelled claims.** Each technical statement is tagged [D] (verified in the official docs), [G] (observed in tool definitions), [R] (third-party report, unverified) or [I] (inference, unverified).
- **Python standard library only.** No dependencies and no network access. Every script supports `--help` and `--dry-run`.

## Install

```bash
git clone https://github.com/omer-faruk-g/MinToken.git ~/.claude/skills/mintoken
```

Windows (PowerShell):

```powershell
git clone https://github.com/omer-faruk-g/MinToken.git "$env:USERPROFILE\.claude\skills\mintoken"
```

Claude Code picks the skill up automatically. It triggers on questions about token use, usage limits, cost, cache misses, long or stuck sessions, and build or log output over 200 lines. Requires Python 3.7 or later.

### Optional hooks and status line

```bash
python ~/.claude/skills/mintoken/scripts/install_hooks.py --only d1,d3,g2   # shows the diff, writes nothing
python ~/.claude/skills/mintoken/scripts/install_hooks.py --only d1,d3,g2 --apply   # asks for 'yes'/'evet'
python ~/.claude/skills/mintoken/scripts/install_hooks.py --uninstall --apply      # removes every MinToken entry
```

| Id | What it does |
|---|---|
| D1 | PreToolUse hook on the Bash tool. It sends gradle, mvn, `npm test`, pytest and `go test` output through `filter_log.py` before Claude sees it. The exit code is kept, and the raw output comes back if the filter fails. The hook returns `ask`, never `allow`, so permission prompts are not bypassed. Set `MINTOKEN_RAW=1` to skip it. |
| D2 | Optional brake for runaway sessions: it asks after N tool calls in a row, on the Nth re-read of the same file, or when the same error repeats. |
| D3 | Status line in the form `ctx 38% · cache 91% · warm 1h (42m left) · miss 2 (tools_changed)`. |
| G2 | On resume, a one-line warning when the prompt cache has likely expired on a large session. |

## What's inside

| Path | Purpose |
|---|---|
| `SKILL.md` | The rules Claude follows (under 150 lines) |
| `scripts/filter_log.py` | Filters build and log output: errors, the first and last lines, the first stack frames, collapsed repeats. Shortens UUIDs, hashes, hex and base64, and writes the originals to a mapping file. |
| `scripts/suggest_deny_rules.py` | Proposes scoped `Read(build/**)`-style deny rules. Never denies a bare tool name. |
| `scripts/audit_tools.py` | Audits the six tools above (installed, missing, general state), measures hook injections, and browses the drain catalog |
| `scripts/audit_config.py` | Read-only audit of settings, env, hooks, skill frontmatter and CLAUDE.md. `--profile safe\|medium\|aggressive` prints suggestions only. |
| `scripts/measure_sessions.py` | Read-only replay of your local transcripts: context per request (median, p90, share above 200K), per-session totals, and what D1 would remove. Use `--since DATE` to compare before and after a change. |
| `scripts/install_hooks.py` | Installs and uninstalls the hooks: diff first, explicit confirmation, backup |
| `references/hidden-drains*.md` | 178 labelled hidden token consumers (C1–C178), written in Turkish |
| `references/cache-awareness.md` | What breaks the prompt cache and what doesn't, plus the TTL buckets |
| `references/settings-cheatsheet.md` | Every settings key and env var MinToken mentions, each name checked against the docs |
| `references/measurement.md` | Before/after measurement protocol |

```bash
python scripts/audit_tools.py --drains all      # C1–C114
python scripts/audit_tools.py --drains3         # C115–C178
python scripts/audit_tools.py --drain 110       # one item
python scripts/audit_config.py                  # what is set, what is on by default, what to consider
python scripts/measure_sessions.py              # where your tokens actually go (from local transcripts)
```

## Verification status

Every settings key and env var name used by `audit_config.py` (129 of them) was checked against the complete Claude Code docs corpus on 2026-10-10: 221 pages, changelog through v2.1.296. Default values and version numbers come from the docs as read on that date, so re-check them after Claude Code updates. Items labelled [R] or [I] remain unverified, and the skill says so wherever they appear.

## Türkçe özet

MinToken, Claude Code'da görünmeyen token tüketimini görünür kılan ve her biri için geri alınabilir bir azaltma yolu sunan bir skill'dir. Yüzde tasarruf vaat etmez; ne kadar düştüğünü `references/measurement.md` protokolüyle kendi ölçümün gösterir. Ayarlara ve hook'lara onayın olmadan dokunmaz: önce diff gösterir, "evet" yazmadan yazmaz ve yedek alır. Kurulum için yukarıdaki `git clone` komutunu kullan.

## License

Copyright (C) 2026 Omer-F.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. It is distributed WITHOUT ANY WARRANTY. See [LICENSE](LICENSE) for the full text.
