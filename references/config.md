# MinToken Configuration Reference

These thresholds are read by MinToken scripts. Edit this file to customize behavior.
All changes take effect on next script run (no restart needed).

## Language Settings

```
INTERNAL_LANG = en
# Language for plan/comments/notes inside sessions.
# [I] Non-ASCII identifiers may increase token count; not formally measured.

USER_LANG = auto
# Language for user-facing replies. "auto" = detect from user message.

TR_TOKEN_MULTIPLIER = 1.5
# Rough multiplier for estimating Turkish vs English token count.
# [I] Not formally measured; used only as a planning heuristic.
# Label all estimates using this as "rough estimate".
```

## Session Hygiene Thresholds

```
MAX_CONSECUTIVE_TOOLS = 20
# Stop and ask direction after this many consecutive tool calls without a user message.
# Exact counting requires the optional D2 hook; model keeps approximate count otherwise.

MAX_SAME_ERROR = 2
# Stop and change method after the same error occurs this many times.

MAX_REREAD = 3
# Stop and ask after reading the same file this many times in one session.
```

## Context Warnings

```
CONTEXT_SIZE_WARN = 100000
# Token threshold at which MinToken recommends /compact or /clear.
# [I] This is a "hygiene threshold", not an official pricing tier.
# Actual context size: use /context.

AUDIT_AGENT_DESC_WARN = 15000
# Token threshold for total subagent description size before warning.
# [D] Documented: 15,000 token warning threshold.

HOOK_INJECT_WARN_TOKENS = 2000
# A4/C76: warn when a single SessionStart/UserPromptSubmit hook injection
# (e.g. claude-mem context) exceeds this many tokens (chars/4, rough).
# [I] User-adjustable hygiene threshold, not an official number.
```

## Filter Settings

```
FILTER_HEAD_LINES = 5
# Lines to keep at start of filtered log output.

FILTER_TAIL_LINES = 5
# Lines to keep at end of filtered log output.

FILTER_STACK_FRAMES = 3
# Number of stack trace frames to keep (rest replaced with "... N more").

FILTER_MIN_LINES = 20
# Only filter output longer than this many lines.
```

## Hook Behaviour

```
HOOK_PERMISSION_DECISION = ask
# D1 returns updatedInput together with permissionDecision "ask": you see the
# rewritten (filtered) command and approve it. MinToken never returns "allow"
# (docs: "allow" skips the permission prompt).
# "none" omits the decision — whether updatedInput is applied without a
# decision is NOT documented [unverified]. Env override: MINTOKEN_HOOK_PERMISSION_DECISION.
```

Every key in this file can be overridden per run with env `MINTOKEN_<KEY>`.

## Hook Thresholds (for install_hooks.py)

```
RESUME_GUARD_TOKEN_THRESHOLD = 50000
# Minimum context_tokens for resume_cost_guard.py to emit a warning.
# Only relevant if G2 hook is installed.

RESUME_GUARD_MAX_CHARS = 300
# Maximum characters for resume cost warning message.
```
