#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken G1 — READ-ONLY settings/env audit. Never writes a file (--dry-run is a no-op).

Reads ~/.claude/settings.json, <cwd>/.claude/settings.json, <cwd>/.claude/settings.local.json,
the managed settings file if readable, their `env` blocks and the current process environment.

Output:
  (1) currently SET keys that matter for tokens/cache (worst first)
  (2) things that are probably ON because of a documented default
  (3) recommendations: C#, current value, why, suggested change (text only), cost
  (4) inventory: hooks, skill frontmatter (model:/effort:/!cmd), CLAUDE.md / MEMORY.md / agent descriptions
  (5) could not verify / could not read
--profile safe|medium|aggressive (also: guvenli|güvenli|orta|agresif) prints SUGGESTIONS only;
apply them yourself or via a diff + explicit approval. One change at a time, then measure
(references/measurement.md). No savings percentage is ever claimed.

Every key name was checked against the full docs corpus (VERIFIED_PAGES below, generated
2026-10-10, 221 pages, changelog to v2.1.296). A check whose key is not in VERIFIED_PAGES is
SKIPPED and listed in section (5), as spec G1 requires.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import claude_home, read_json  # noqa: E402

TRUTHY = {"1", "true", "yes", "on"}


def truthy(v):
    return str(v).strip().lower() in TRUTHY


def getpath(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


# (priority, C#, key, kind, flag(value)->bool, why, suggestion, cost)
# kind: "env" or "set" (settings key, dotted path allowed)
CHECKS = [
    (0, "C110", "DISABLE_PROMPT_CACHING", "env", truthy, "prompt caching OFF: every turn re-bills the whole context", "remove it", "none (it is a debug switch)"),
    (0, "C110", "DISABLE_PROMPT_CACHING_HAIKU", "env", truthy, "caching off for this model family", "remove it", "none"),
    (0, "C110", "DISABLE_PROMPT_CACHING_SONNET", "env", truthy, "caching off for this model family", "remove it", "none"),
    (0, "C110", "DISABLE_PROMPT_CACHING_OPUS", "env", truthy, "caching off for this model family", "remove it", "none"),
    (0, "C110", "DISABLE_PROMPT_CACHING_FABLE", "env", truthy, "caching off for this model family", "remove it", "none"),
    (0, "C110", "FORCE_PROMPT_CACHING_5M", "env", truthy, "pins main TTL to 5 min (debug switch); overrides promptCacheTtl", "remove it", "none"),
    (0, "C110/C127", "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS", "env", truthy, "system-context block uncached, tool search OFF (all MCP schemas up front), effort change breaks cache, auto-mode server review off", "remove unless required by your gateway", "gateway compatibility"),
    (0, "C110", "CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH", "env", truthy, "mid-session system prompt change breaks the cache", "remove it", "plugins refresh only on restart"),
    (1, "C95", "fastMode", "set", truthy, "fast mode persists across sessions; billed from usage credits; first enable re-reads context uncached at fast price", "fastMode=false, fastModePerSessionOptIn=true", "slower responses"),
    (1, "C95", "CLAUDE_CODE_DISABLE_FAST_MODE", "env", lambda v: False, "", "", ""),
    (2, "C97/C129", "ANTHROPIC_DEFAULT_HAIKU_MODEL", "env", lambda v: bool(re.search(r"opus|fable|sonnet", str(v), re.I)), "background jobs (titles, summaries, /goal judge, agent-view rows) run on this model", "point it to a Haiku-class model", "background quality"),
    (3, "C118", "apiKeyHelper", "set", lambda v: bool(v), "gateway/helper credentials: subscription limits do NOT apply, billed per token", "confirm this is intended", "-"),
    (3, "C117/C6", "ANTHROPIC_BASE_URL", "env", lambda v: bool(v) and "api.anthropic.com" not in str(v), "non-first-party host: tool search off -> all MCP schemas in prefix; 1M window may exceed gateway", "set ENABLE_TOOL_SEARCH if gateway forwards tool_reference; trim MCP", "-"),
    (3, "C115", "CLAUDE_CODE_RETRY_WATCHDOG", "env", truthy, "429/529 retried indefinitely (up to ~300 tries)", "unset outside unattended jobs or set ..._MAX_WAIT_MS", "less resilience"),
    (3, "C123", "CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS", "env", lambda v: str(v).strip() == "0", "0 = -p waits forever for background work", "use a finite ceiling + --max-budget-usd", "-"),
    (3, "C99/C155", "autoContinueAtUsageLimit", "set", truthy, "resumes work unattended when the limit resets — spends the new window while you are away", "autoContinueAtUsageLimit=false", "work waits for you"),
    (3, "C66", "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "env", lambda v: bool(v), "raised output cap leaves less room before auto-compaction", "unset (default)", "long single outputs may cut"),
    (3, "C69", "CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS", "env", lambda v: bool(v), "larger full-file reads", "unset; use offset/limit", "-"),
    (3, "C68", "BASH_MAX_OUTPUT_LENGTH", "env", lambda v: str(v).isdigit() and int(v) > 30000, "more inline Bash output per call", "default (~30000) or lower", "Claude may rerun truncated commands"),
    (3, "C68", "bashOutputMaxChars", "set", lambda v: str(v).isdigit() and int(v) > 30000, "more inline Bash output per call", "lower it", "Claude may rerun truncated commands"),
    (3, "C71", "MAX_MCP_OUTPUT_TOKENS", "env", lambda v: str(v).isdigit() and int(v) > 25000, "one MCP call can add tens of thousands of tokens", "25000 or lower", "large results cut/saved to file"),
    (3, "C93/C172", "advisorModel", "set", lambda v: bool(v), "each advisor call re-reads the whole transcript uncached at advisor price", "/advisor off if unused", "lose second opinion"),
    (3, "C98/C119", "switchModelsOnFlag", "set", lambda v: v is True, "flagged request switches model = cold-cache turn, can bill twice", "switchModelsOnFlag=false (ask each time)", "one more prompt"),
    (3, "C98/C172", "fallbackModel", "set", lambda v: bool(v), "availability fallback = cold-cache turn", "keep chain short", "-"),
    (3, "C90/C151", "ultracode", "set", lambda v: bool(v), "every significant task becomes a workflow, limits off", "turn off unless intended", "-"),
    (3, "C147", "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "env", truthy, "teams ~7x tokens in plan mode", "unset when not needed", "no teams"),
    (3, "C158", "autoMode.classifyAllShell", "set", truthy, "every shell command goes through the classifier", "false", "-"),
    (3, "C141", "disableAllHooks", "set", truthy, "info: hooks AND status line AND mods are off", "-", "-"),
    (4, "C25/DZ-9", "DISABLE_AUTOUPDATER", "env", lambda v: False, "", "", ""),
    (4, "C15/C134", "promptCacheTtl", "set", lambda v: False, "", "", ""),
    (4, "C16/C92", "subagentPromptCacheTtl", "set", lambda v: False, "", "", ""),
    (4, "C51/C133", "outputStyle", "set", lambda v: str(v).lower() in ("explanatory", "learning"), "this style intentionally produces longer output", "Default or Concise", "less explanation"),
    (4, "C62", "autoCompactWindow", "set", lambda v: False, "", "", ""),
    (4, "C62", "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "env", lambda v: False, "", "", ""),
    (4, "C62", "CLAUDE_CODE_DISABLE_1M_CONTEXT", "env", lambda v: False, "", "", ""),
    (4, "C96/C170", "model", "set", lambda v: False, "", "", ""),
    (4, "C96/C170", "effortLevel", "set", lambda v: False, "", "", ""),
    (4, "C96", "maxEffortLevel", "set", lambda v: False, "", "", ""),
    (4, "C96", "CLAUDE_CODE_EFFORT_LEVEL", "env", lambda v: False, "", "", ""),
    (4, "C44", "MAX_THINKING_TOKENS", "env", lambda v: True, "ignored (non-zero) by adaptive models: Opus/Sonnet/Haiku 5.5, Fable [D]", "use /effort at session start", "-"),
    (4, "C83/DZ-7", "CLAUDE_CODE_SUBAGENT_MODEL", "env", lambda v: False, "", "", ""),
    (4, "C87/C131", "CLAUDE_CODE_FORK_SUBAGENT", "env", lambda v: False, "", "", ""),
    (4, "C56", "autoMemoryEnabled", "set", lambda v: False, "", "", ""),
    (4, "C58/C169", "includeGitInstructions", "set", lambda v: False, "", "", ""),
    (4, "C52/C126", "skillOverrides", "set", lambda v: False, "", "", ""),
    (4, "C52/C126", "skillListingBudgetFraction", "set", lambda v: False, "", "", ""),
    (4, "C52/C126", "skillListingMaxDescChars", "set", lambda v: False, "", "", ""),
    (4, "C55", "claudeMdExcludes", "set", lambda v: False, "", "", ""),
    (4, "C57", "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD", "env", truthy, "added dirs also load CLAUDE.md and rules", "unset if not needed", "-"),
    (4, "C60/C164", "disableClaudeAiConnectors", "set", lambda v: False, "", "", ""),
    (4, "C60", "ENABLE_CLAUDEAI_MCP_SERVERS", "env", lambda v: False, "", "", ""),
    (4, "C30/C103", "promptSuggestionEnabled", "set", lambda v: False, "", "", ""),
    (4, "C102", "awaySummaryEnabled", "set", lambda v: False, "", "", ""),
    (4, "C34/C148", "crossSessionInbound", "set", lambda v: False, "", "", ""),
    (4, "C35/C156", "CLAUDE_CODE_GOAL_CHECKIN_MINUTES", "env", lambda v: False, "", "", ""),
    (4, "C89/C151", "workflowSizeGuideline", "set", lambda v: False, "", "", ""),
    (4, "C90/C151", "workflowKeywordTriggerEnabled", "set", lambda v: False, "", "", ""),
    (4, "C90", "disableWorkflows", "set", lambda v: False, "", "", ""),
    (4, "C101/C178", "CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION", "env", lambda v: False, "", "", ""),
    (4, "C88", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS", "env", lambda v: False, "", "", ""),
    (4, "C136", "syncClaudeAiPlugins", "set", lambda v: False, "", "", ""),
    (4, "C136", "syncClaudeAiSkills", "set", lambda v: False, "", "", ""),
    (4, "C157", "respondToBashCommands", "set", lambda v: False, "", "", ""),
    (4, "C149", "enableArtifact", "set", lambda v: False, "", "", ""),
    (4, "C149", "CLAUDE_CODE_ARTIFACT_COMMENTS_AUTOREACT", "env", lambda v: False, "", "", ""),
    (4, "C158", "permissions.defaultMode", "set", lambda v: False, "", "", ""),
    (4, "C159", "sandbox.allowUnsandboxedCommands", "set", lambda v: False, "", "", ""),
    (4, "C152", "CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS", "env", lambda v: False, "", "", ""),
    (4, "C169", "CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT", "env", lambda v: False, "", "", ""),
    (4, "C177", "language", "set", lambda v: False, "", "", ""),
    (4, "C164", "skipWebFetchPreflight", "set", lambda v: False, "", "", ""),
    (4, "C173", "MCP_TOOL_TIMEOUT", "env", lambda v: False, "", "", ""),
    (4, "C163", "API_TIMEOUT_MS", "env", lambda v: False, "", "", ""),
    (4, "C116", "CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES", "env", lambda v: False, "", "", ""),
    (4, "C115", "CLAUDE_CODE_MAX_RETRIES", "env", lambda v: False, "", "", ""),
    (4, "C124", "CLAUDE_CODE_RESUME_INTERRUPTED_TURN", "env", lambda v: False, "", "", ""),
    (4, "C176", "worktree.sparsePaths", "set", lambda v: False, "", "", ""),
    (4, "DZ-9", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "env", truthy, "also disables feature-flag fetch -> advisor/Remote Control/some server features off", "keep only if intended", "features off"),
]

DEFAULT_ON = [
    ("C62", "1M context window on Sonnet 5+/Haiku 5.5/Opus 4.7+/Fable; auto-compact ~967K (re-verify the number)", ("autoCompactWindow", "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "CLAUDE_CODE_DISABLE_1M_CONTEXT")),
    ("C96/C170", "default model Opus 5.5, effort medium", ("model", "ANTHROPIC_MODEL")),
    ("C87", "fork mode default in interactive sessions (v2.1.232+)", ("CLAUDE_CODE_FORK_SUBAGENT",)),
    ("C30/C103", "prompt suggestions after each reply", ("promptSuggestionEnabled", "CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION")),
    ("C102", "away summary (recap) request when you return", ("awaySummaryEnabled", "CLAUDE_CODE_ENABLE_AWAY_SUMMARY")),
    ("C56", "auto memory: first 200 lines/25 KB of MEMORY.md each session", ("autoMemoryEnabled", "CLAUDE_CODE_DISABLE_AUTO_MEMORY")),
    ("C60/C164", "claude.ai connectors auto-loaded on subscription login", ("disableClaudeAiConnectors", "ENABLE_CLAUDEAI_MCP_SERVERS", "strictMcpConfig")),
    ("DZ-3/C158", "interactive sessions start in auto mode (v2.1.283+)", ("permissions.defaultMode",)),
    ("C90/C151", "'ultracode' keyword in a prompt starts a workflow", ("workflowKeywordTriggerEnabled", "disableWorkflows")),
    ("C140", "official-marketplace plugin auto-update", ("DISABLE_AUTOUPDATER",)),
    ("C141", "mods enabled (v2.1.287+)", ("disableAllHooks",)),
    ("C136", "claude.ai synced plugins/skills (v2.1.273+)", ("syncClaudeAiPlugins", "syncClaudeAiSkills")),
    ("C149", "artifact comment auto-replies", ("CLAUDE_CODE_ARTIFACT_COMMENTS_AUTOREACT", "enableArtifact")),
    ("C163", "stream watchdogs (retry stalled streams)", ("CLAUDE_ENABLE_STREAM_WATCHDOG",)),
    ("C157", "`!cmd` shell-mode output triggers a model reply", ("respondToBashCommands",)),
]

PROFILES = {
    "safe": [
        ("C30/C103", "promptSuggestionEnabled=false", "none expected"),
        ("C102/C103", "awaySummaryEnabled=false", "no recap when you return"),
        ("C31/C103", "env CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1", "no auto session title"),
        ("C34/C148", "crossSessionInbound=\"hold\"", "messages from other sessions wait"),
        ("C35/C156", "env CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0", "no idle goal check-ins / auto retries"),
        ("C52/C126", "skillOverrides: name-only for skills you never use", "Claude will not auto-discover those skills"),
        ("C59", "turn Chrome default off (/chrome), use --chrome when needed", "browser tools absent by default"),
        ("C60", "disable unused claude.ai connectors", "those connectors disappear"),
        ("C90/C151", "workflowKeywordTriggerEnabled=false", "type /workflow explicitly"),
        ("C95/C172", "fastModePerSessionOptIn=true", "fast mode must be re-enabled per session"),
        ("C99/C155", "autoContinueAtUsageLimit=false", "work waits until you return"),
    ],
    "medium": [
        ("C62", "autoCompactWindow=<you choose, e.g. 200000–400000>", "earlier compaction loses detail"),
        ("C68", "bashOutputMaxChars=<lower, e.g. 15000>", "Claude may rerun truncated commands"),
        ("C71", "env MAX_MCP_OUTPUT_TOKENS=<lower, e.g. 10000>", "large MCP results cut/saved to file"),
        ("C83", "user subagent `Explore` with model: haiku", "exploration quality may drop"),
        ("C89", "workflowSizeGuideline=\"small\"", "smaller fan-out"),
        ("C101", "env CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION=<30–50>", "research stops earlier"),
        ("C58/C169", "includeGitInstructions=false (only if you never use Claude for commits/PRs)", "commit/PR conventions unknown to Claude"),
    ],
    "aggressive": [
        ("C56", "autoMemoryEnabled=false", "no cross-session learning"),
        ("C62", "env CLAUDE_CODE_DISABLE_1M_CONTEXT=1", "200K window"),
        ("C96/C170", "lower effort at session start / maxEffortLevel (managed)", "lower reasoning quality"),
        ("C93/C172", "/advisor off or env CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1", "no second-model advice"),
        ("C90", "disableWorkflows=true", "no workflows"),
        ("C88", "env CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1", "no background tasks"),
        ("C83/DZ-7", "env CLAUDE_CODE_SUBAGENT_MODEL=haiku (+ CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1)", "all subagents on Haiku"),
    ],
}
PROFILE_ALIASES = {"guvenli": "safe", "güvenli": "safe", "orta": "medium", "agresif": "aggressive"}

# Spec G1/H3/I3 keys with no flag rule: reported as SET/unset with their value only.
REPORT_ONLY = [
    ("C110", "ENABLE_PROMPT_CACHING_1H"), ("C93/C172", "CLAUDE_CODE_DISABLE_ADVISOR_TOOL"),
    ("C95", "fastModePerSessionOptIn"), ("C44/C170", "alwaysThinkingEnabled"), ("C62", "autoCompactEnabled"),
    ("C62", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"), ("C62/C170", "modelSettings"), ("C61/DZ-1", "CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH"),
    ("C126", "SLASH_COMMAND_TOOL_CHAR_BUDGET"), ("C117/C173", "ENABLE_TOOL_SEARCH"), ("C31/C103", "CLAUDE_CODE_DISABLE_TERMINAL_TITLE"),
    ("C33", "CLAUDE_CODE_DISABLE_CRON"), ("C90", "CLAUDE_CODE_DISABLE_WORKFLOWS"), ("C151", "CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS"),
    ("DZ-8", "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"), ("DZ-8", "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"),
    ("C83/DZ-7", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"), ("C115", "CLAUDE_CODE_RETRY_WATCHDOG_MAX_WAIT_MS"),
    ("C136", "CLAUDE_CODE_SYNC_SKILLS"), ("C157", "askUserQuestionTimeout"), ("C158", "useAutoModeDuringPlan"),
    ("C158", "permissions.disableAutoMode"), ("C100/DZ-4", "CLAUDE_CODE_AUTO_MODE_SERVER"),
    ("C159", "permissions.blockReadsOutsideWorkingDirectories"), ("C149", "CLAUDE_CODE_ARTIFACT_COMMENTS"),
    ("C153", "disableAgentView"), ("C153", "CLAUDE_CODE_DISABLE_AGENT_VIEW"),
    ("C143", "ENABLE_STOP_REVIEW"), ("C143", "ENABLE_COMMIT_REVIEW"), ("C143", "ENABLE_CODE_SECURITY_REVIEW"),
    ("C143", "SECURITY_GUIDANCE_DISABLE"), ("C169", "CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS"),
    ("C169", "CLAUDE_CODE_DISABLE_CLAUDE_MDS"), ("C169", "CLAUDE_CODE_DISABLE_BUNDLED_SKILLS"),
    ("C169", "CLAUDE_CODE_DISABLE_ATTACHMENTS"), ("C169", "CLAUDE_CODE_ENABLE_TODO_TOOLS"), ("C164", "strictMcpConfig"),
    ("C173", "CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS"), ("C161", "ANTHROPIC_DEFAULT_OPUS_MODEL"),
    ("C161", "ANTHROPIC_DEFAULT_SONNET_MODEL"), ("C165", "allowedProviders"), ("C29", "cleanupPeriodDays"),
    ("DZ-9", "DISABLE_UPDATES"), ("DZ-9", "DISABLE_TELEMETRY"), ("C163", "CLAUDE_ENABLE_STREAM_WATCHDOG"),
    ("C176", "worktree.symlinkDirectories"), ("C54/C135", "enabledPlugins"),
]

# BEGIN VERIFIED (generated; do not edit by hand)
VERIFIED_SOURCE = 'code.claude.com/docs (221 pages, changelog to v2.1.296) on 2026-10-10'
VERIFIED_PAGES = {
    'ANTHROPIC_BASE_URL': ['settings-reference', 'env-vars'],
    'ANTHROPIC_DEFAULT_HAIKU_MODEL': ['env-vars', 'agent-view'],
    'ANTHROPIC_DEFAULT_OPUS_MODEL': ['env-vars', 'amazon-bedrock'],
    'ANTHROPIC_DEFAULT_SONNET_MODEL': ['env-vars', 'amazon-bedrock'],
    'ANTHROPIC_MODEL': ['settings-reference', 'env-vars'],
    'API_TIMEOUT_MS': ['env-vars', 'agent-sdk__python'],
    'BASH_MAX_OUTPUT_LENGTH': ['settings-reference', 'env-vars'],
    'CLAUDE_AUTOCOMPACT_PCT_OVERRIDE': ['env-vars', 'claude-code-on-the-web'],
    'CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD': ['env-vars', 'changelog'],
    'CLAUDE_CODE_ARTIFACT_COMMENTS': ['env-vars'],
    'CLAUDE_CODE_ARTIFACT_COMMENTS_AUTOREACT': ['env-vars'],
    'CLAUDE_CODE_AUTO_COMPACT_WINDOW': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_AUTO_MODE_SERVER': ['env-vars', 'changelog'],
    'CLAUDE_CODE_DISABLE_1M_CONTEXT': ['env-vars', 'amazon-bedrock'],
    'CLAUDE_CODE_DISABLE_ADVISOR_TOOL': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_AGENT_VIEW': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_ATTACHMENTS': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_AUTO_MEMORY': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_BACKGROUND_TASKS': ['env-vars', 'changelog'],
    'CLAUDE_CODE_DISABLE_BUNDLED_SKILLS': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_CLAUDE_MDS': ['env-vars', 'agent-sdk__modifying-system-prompts'],
    'CLAUDE_CODE_DISABLE_CRON': ['env-vars', 'changelog'],
    'CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS': ['env-vars', 'agent-sdk__modifying-system-prompts'],
    'CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS': ['env-vars', 'sub-agents'],
    'CLAUDE_CODE_DISABLE_FAST_MODE': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_TERMINAL_TITLE': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_DISABLE_WORKFLOWS': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_EFFORT_LEVEL': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_ENABLE_AWAY_SUMMARY': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH': ['env-vars'],
    'CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_ENABLE_TODO_TOOLS': ['env-vars', 'agent-sdk__todo-tracking'],
    'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS': ['env-vars', 'agent-teams'],
    'CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS': ['env-vars', 'changelog'],
    'CLAUDE_CODE_FORK_SUBAGENT': ['env-vars', 'changelog'],
    'CLAUDE_CODE_GOAL_CHECKIN_MINUTES': ['env-vars', 'changelog'],
    'CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS': ['env-vars', 'agent-sdk__subagents'],
    'CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH': ['env-vars', 'changelog'],
    'CLAUDE_CODE_MAX_OUTPUT_TOKENS': ['env-vars', 'changelog'],
    'CLAUDE_CODE_MAX_RETRIES': ['env-vars', 'agent-sdk__python'],
    'CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH': ['env-vars', 'agent-sdk__subagents'],
    'CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION': ['env-vars', 'changelog'],
    'CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS': ['env-vars', 'changelog'],
    'CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES': ['env-vars', 'changelog'],
    'CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS': ['env-vars', 'headless'],
    'CLAUDE_CODE_RESUME_INTERRUPTED_TURN': ['env-vars', 'agent-sdk__typescript'],
    'CLAUDE_CODE_RETRY_WATCHDOG': ['env-vars', 'agent-sdk__python'],
    'CLAUDE_CODE_RETRY_WATCHDOG_MAX_WAIT_MS': ['env-vars', 'changelog'],
    'CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT': ['env-vars', 'agent-sdk__modifying-system-prompts'],
    'CLAUDE_CODE_SUBAGENT_MODEL': ['env-vars', 'agent-teams'],
    'CLAUDE_CODE_SUBAGENT_MODEL_FORCE': ['env-vars', 'agent-teams'],
    'CLAUDE_CODE_SYNC_SKILLS': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS': ['env-vars', 'changelog'],
    'CLAUDE_ENABLE_STREAM_WATCHDOG': ['env-vars', 'agent-sdk__python'],
    'DISABLE_AUTOUPDATER': ['settings-reference', 'env-vars'],
    'DISABLE_PROMPT_CACHING': ['env-vars', 'amazon-bedrock'],
    'DISABLE_PROMPT_CACHING_FABLE': ['env-vars', 'model-config'],
    'DISABLE_PROMPT_CACHING_HAIKU': ['env-vars', 'changelog'],
    'DISABLE_PROMPT_CACHING_OPUS': ['env-vars', 'model-config'],
    'DISABLE_PROMPT_CACHING_SONNET': ['env-vars', 'model-config'],
    'DISABLE_TELEMETRY': ['settings-reference', 'env-vars'],
    'DISABLE_UPDATES': ['env-vars', 'changelog'],
    'ENABLE_CLAUDEAI_MCP_SERVERS': ['settings-reference', 'env-vars'],
    'ENABLE_CODE_SECURITY_REVIEW': ['security-guidance'],
    'ENABLE_COMMIT_REVIEW': ['security-guidance'],
    'ENABLE_PROMPT_CACHING_1H': ['settings-reference', 'env-vars'],
    'ENABLE_STOP_REVIEW': ['security-guidance'],
    'ENABLE_TOOL_SEARCH': ['env-vars', 'agent-sdk__tool-search'],
    'FORCE_PROMPT_CACHING_5M': ['settings-reference', 'env-vars'],
    'MAX_MCP_OUTPUT_TOKENS': ['env-vars', 'agent-sdk__mcp'],
    'MAX_THINKING_TOKENS': ['settings-reference', 'env-vars'],
    'MCP_TOOL_TIMEOUT': ['env-vars', 'agent-sdk__mcp'],
    'SECURITY_GUIDANCE_DISABLE': ['security-guidance'],
    'SLASH_COMMAND_TOOL_CHAR_BUDGET': ['env-vars', 'skills'],
    'advisorModel': ['settings-reference', 'env-vars'],
    'allowedProviders': ['settings-reference', 'admin-setup'],
    'alwaysThinkingEnabled': ['settings-reference', 'changelog'],
    'apiKeyHelper': ['settings-reference', 'env-vars'],
    'askUserQuestionTimeout': ['settings-reference', 'env-vars'],
    'autoCompactEnabled': ['settings-reference', 'env-vars'],
    'autoCompactWindow': ['settings-reference', 'env-vars'],
    'autoContinueAtUsageLimit': ['settings-reference', 'commands'],
    'autoMemoryEnabled': ['settings-reference', 'env-vars'],
    'autoMode.classifyAllShell': ['settings-reference', 'settings'],
    'awaySummaryEnabled': ['settings-reference', 'env-vars'],
    'bashOutputMaxChars': ['settings-reference', 'env-vars'],
    'claudeMdExcludes': ['settings-reference', 'changelog'],
    'cleanupPeriodDays': ['settings-reference', 'agent-sdk__session-storage'],
    'crossSessionInbound': ['settings-reference', 'settings'],
    'disableAgentView': ['settings-reference', 'env-vars'],
    'disableAllHooks': ['settings-reference', 'changelog'],
    'disableClaudeAiConnectors': ['settings-reference', 'env-vars'],
    'disableWorkflows': ['settings-reference', 'env-vars'],
    'effortLevel': ['settings-reference', 'env-vars'],
    'enableArtifact': ['settings-reference', 'env-vars'],
    'enabledPlugins': ['settings-reference', 'settings'],
    'fallbackModel': ['settings-reference', 'env-vars'],
    'fastMode': ['settings-reference', 'agent-sdk__typescript'],
    'fastModePerSessionOptIn': ['settings-reference', 'fast-mode'],
    'includeGitInstructions': ['settings-reference', 'env-vars'],
    'language': ['settings-reference', 'agent-sdk__configuration'],
    'maxEffortLevel': ['settings-reference', 'env-vars'],
    'model': ['settings-reference', 'env-vars'],
    'modelSettings': ['settings-reference', 'env-vars'],
    'outputStyle': ['settings-reference', 'agent-sdk__configuration'],
    'permissions.blockReadsOutsideWorkingDirectories': ['settings-reference', 'settings'],
    'permissions.defaultMode': ['settings-reference', 'settings'],
    'permissions.disableAutoMode': ['settings-reference', 'admin-setup'],
    'promptCacheTtl': ['settings-reference', 'env-vars'],
    'promptSuggestionEnabled': ['settings-reference', 'env-vars'],
    'respondToBashCommands': ['settings-reference', 'changelog'],
    'sandbox.allowUnsandboxedCommands': ['settings-reference', 'changelog'],
    'skillListingBudgetFraction': ['settings-reference', 'skills'],
    'skillListingMaxDescChars': ['settings-reference', 'skills'],
    'skillOverrides': ['settings-reference', 'agent-sdk__typescript'],
    'skipWebFetchPreflight': ['settings-reference', 'claude-apps-gateway-deploy'],
    'strictMcpConfig': ['agent-sdk__claude-code-features', 'agent-sdk__typescript'],
    'subagentPromptCacheTtl': ['settings-reference', 'env-vars'],
    'switchModelsOnFlag': ['settings-reference', 'env-vars'],
    'syncClaudeAiPlugins': ['settings-reference', 'settings'],
    'syncClaudeAiSkills': ['settings-reference', 'settings'],
    'ultracode': ['settings-reference', 'agent-sdk__subagents'],
    'useAutoModeDuringPlan': ['settings-reference', 'settings'],
    'workflowKeywordTriggerEnabled': ['settings-reference'],
    'workflowSizeGuideline': ['settings-reference', 'changelog'],
    'worktree.sparsePaths': ['settings-reference', 'changelog'],
    'worktree.symlinkDirectories': ['settings-reference'],
}
# END VERIFIED


def managed_path():
    if sys.platform == "win32":
        return Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ClaudeCode" / "managed-settings.json"
    if sys.platform == "darwin":
        return Path("/Library/Application Support/ClaudeCode/managed-settings.json")
    return Path("/etc/claude-code/managed-settings.json")


def load_sources(home, cwd):
    srcs = []
    for label, p in (("user", home / "settings.json"), ("project", cwd / ".claude" / "settings.json"),
                     ("local", cwd / ".claude" / "settings.local.json"), ("managed", managed_path())):
        d = read_json(p)
        srcs.append((label, p, d))
    return srcs


def lookup(key, kind, srcs, environ):
    """Return list of (source, value). Later sources listed after earlier."""
    hits = []
    for label, _, d in srcs:
        if not d:
            continue
        if kind == "set":
            v = getpath(d, key)
            if v is not None:
                hits.append((label, v))
        else:
            v = (d.get("env") or {}).get(key)
            if v is not None:
                hits.append((f"{label}.env", v))
    if kind == "env" and key in environ:
        hits.append(("process env", environ[key]))
    return hits


def hooks_inventory(srcs, home):
    rows = []
    def scan(origin, hooks):
        for event, groups in (hooks or {}).items():
            for g in groups or []:
                m = g.get("matcher")
                for h in g.get("hooks", []):
                    flags = []
                    if event in ("PreToolUse", "PostToolUse") and m in (None, "", "*"):
                        flags.append("no matcher: runs on every tool call (C78)")
                    if h.get("type") in ("prompt", "agent"):
                        flags.append(f"type={h['type']}: model call per event (C79/C154)")
                    if event == "Stop":
                        flags.append("Stop hook: a block decision forces another turn (C80)")
                    if event in ("SessionStart", "UserPromptSubmit", "UserPromptExpansion"):
                        flags.append("plain stdout enters context (C76/C120)")
                    cmd = str(h.get("command") or h.get("prompt") or "")[:70]
                    rows.append((origin, event, m, h.get("type"), cmd, flags))
    for label, _, d in srcs:
        if d:
            scan(label, d.get("hooks"))
    enabled = {k for k, v in ((srcs[0][2] or {}).get("enabledPlugins") or {}).items() if v}
    inst = (read_json(home / "plugins" / "installed_plugins.json") or {}).get("plugins") or {}
    for name in enabled:
        for rec in inst.get(name, []):
            hj = read_json(Path(rec.get("installPath", "")) / "hooks" / "hooks.json")
            if hj:
                scan(f"plugin:{name}", hj.get("hooks", hj))
    return rows


def skill_dirs(home, cwd):
    dirs = [home / "skills", cwd / ".claude" / "skills"]
    inst = (read_json(home / "plugins" / "installed_plugins.json") or {}).get("plugins") or {}
    for recs in inst.values():
        for rec in recs:
            dirs.append(Path(rec.get("installPath", "")) / "skills")
    return dirs


def frontmatter_scan(home, cwd):
    flagged, total, desc_chars = [], 0, 0
    for d in skill_dirs(home, cwd):
        if not d.is_dir():
            continue
        for p in d.glob("*/SKILL.md"):
            total += 1
            text = p.read_text(encoding="utf-8", errors="replace")
            fm = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
            fm_text = fm.group(1) if fm else ""
            m = re.search(r"^description:\s*(.+)$", fm_text, re.M)
            desc_chars += len(m.group(1)) if m else 0
            hits = [k for k in ("model", "effort") if re.search(rf"^{k}:", fm_text, re.M)]
            if re.search(r"!`[^`]+`", text[fm.end() if fm else 0:]):
                hits.append("!`cmd`")
            if hits:
                flagged.append((str(p), hits))
    return total, desc_chars, flagged


def memory_inventory(home, cwd):
    rows = []
    paths = [home / "CLAUDE.md"]
    cur = cwd.resolve()
    chain = [cur] + list(cur.parents)
    for c in reversed(chain):
        paths += [c / "CLAUDE.md", c / "CLAUDE.local.md", c / ".claude" / "CLAUDE.md"]
    seen = set()
    for p in paths:
        if p in seen or not p.is_file():
            continue
        seen.add(p)
        n = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        rows.append((str(p), n, p.stat().st_size // 4, " <- over 200 lines (C8)" if n > 200 else ""))
    mems = sorted((home / "projects").glob("*/memory/MEMORY.md"), key=lambda p: p.stat().st_size, reverse=True)
    mem_rows = [(str(p), p.stat().st_size) for p in mems[:3]]
    agent_chars = 0
    for d in (home / "agents", cwd / ".claude" / "agents"):
        for p in d.glob("*.md") if d.is_dir() else []:
            m = re.search(r"^description:\s*(.+)$", p.read_text(encoding="utf-8", errors="replace"), re.M)
            agent_chars += len(m.group(1)) if m else 0
    return rows, mem_rows, agent_chars


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--home", help="fake ~/.claude dir (testing)")
    p.add_argument("--cwd", help="project dir (default cwd)")
    p.add_argument("--no-process-env", action="store_true", help="ignore the current process environment (testing)")
    p.add_argument("--profile", help="safe|medium|aggressive (guvenli|orta|agresif): suggestions only")
    p.add_argument("--json", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="no-op: this script never writes")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.profile:
        prof = PROFILE_ALIASES.get(a.profile.lower(), a.profile.lower())
        if prof not in PROFILES:
            print("profile must be safe|medium|aggressive")
            return 2
        order = ["safe", "medium", "aggressive"]
        print(f"=== Profile '{prof}' — SUGGESTIONS ONLY, nothing is written ===")
        print("Apply one change at a time in a NEW session, then re-run the measurement protocol.\n")
        for level in order[: order.index(prof) + 1]:
            print(f"[{level}]")
            for c, change, cost in PROFILES[level]:
                print(f"  {c:<10} {change}\n             cost: {cost}")
        print("\nNo savings figure is claimed; only your own before/after measurement shows the effect.")
        return 0

    home = claude_home(a.home)
    cwd = Path(a.cwd or os.getcwd())
    environ = {} if a.no_process_env else dict(os.environ)
    srcs = load_sources(home, cwd)

    found, recs, skipped = [], [], []
    report_only = [(9, c, key, "env" if key.isupper() else "set", lambda v: False, "", "", "") for c, key in REPORT_ONLY]
    for prio, c, key, kind, flag, why, sugg, cost in CHECKS + report_only:
        if key not in VERIFIED_PAGES:  # G1: unverifiable check -> skip and report
            skipped.append(key)
            continue
        for src, val in lookup(key, kind, srcs, environ):
            bad = bool(why) and flag(val)
            found.append((prio if bad else 9, c, key, src, val, bad))
            if bad:
                recs.append((prio, c, key, val, why, sugg, cost))
    found.sort(key=lambda r: r[0])
    recs.sort(key=lambda r: r[0])
    set_keys = {f[2] for f in found}

    defaults = [(c, text) for c, text, keys in DEFAULT_ON if not (set(keys) & set_keys)]
    hooks = hooks_inventory(srcs, home)
    n_sk, desc_chars, fm_flags = frontmatter_scan(home, cwd)
    mds, mems, agent_chars = memory_inventory(home, cwd)

    if a.json:
        print(json.dumps({"set": [dict(zip(("prio", "c", "key", "source", "value", "flagged"), f)) for f in found],
                          "default_on": defaults,
                          "recommendations": [dict(zip(("prio", "c", "key", "value", "why", "suggest", "cost"), r)) for r in recs],
                          "hooks": hooks, "skills": {"count": n_sk, "desc_rough_tokens": desc_chars // 4, "flagged": fm_flags},
                          "claude_md": mds, "memory_md": mems, "agent_desc_rough_tokens": agent_chars // 4},
                         indent=2, default=str, ensure_ascii=False))
        return 0

    print("=== (1) Set now (flagged '!' first) ===")
    if not found:
        print("  nothing relevant set")
    for prio, c, key, src, val, bad in found:
        print(f"  {'!' if bad else ' '} {c:<10} {key} = {json.dumps(val, ensure_ascii=False)}  [{src}]")
    print("\n=== (2) Probably ON because of a documented default (not overridden in readable files) ===")
    for c, text in defaults:
        print(f"    {c:<10} {text}")
    print("    (unreadable) Chrome 'Enabled by default' -> check with /chrome; claude.ai connectors -> /mcp")
    print("\n=== (3) Recommendations (text only — apply with diff + explicit approval) ===")
    if not recs:
        print("  none from settings/env. See --profile safe for low-cost options.")
    for prio, c, key, val, why, sugg, cost in recs:
        print(f"  {c:<10} {key} = {json.dumps(val, ensure_ascii=False)}\n             why: {why}\n             suggest: {sugg}\n             cost: {cost}")
    print("\n=== (4) Inventory (rough = chars/4) ===")
    print(f"  Hooks: {len(hooks)}")
    for origin, event, m, typ, cmd, flags in hooks:
        print(f"    [{origin}] {event} matcher={m!r} type={typ} :: {cmd}")
        for f in flags:
            print(f"        - {f}")
    print(f"  Skills scanned: {n_sk}; descriptions ~{desc_chars // 4} tokens (rough, every turn: C52/C126)")
    for path, hits in fm_flags:
        print(f"    ! {path}: {', '.join(hits)} (model/effort switch breaks cache; !cmd output enters prompt: C82)")
    for path, n, toks, warn in mds:
        print(f"  {path}: {n} lines, ~{toks} tokens{warn}")
    for path, size in mems:
        print(f"  MEMORY.md {path}: {size} bytes (first 200 lines/25 KB load each session, C56)")
    warn = "  <- above 15,000-token budget (C53/C125)" if agent_chars // 4 > 15000 else ""
    print(f"  Custom agent descriptions: ~{agent_chars // 4} tokens{warn}")
    print("\n=== (5) Could not verify / read ===")
    msrc = srcs[3]
    print(f"  managed settings {msrc[1]}: {'read' if msrc[2] else 'not found or unreadable'} — /status shows the real sources")
    print("  Plugin always-on cost: run `claude plugin details <name>` yourself (C54/C135)")
    print(f"  Key names checked against {VERIFIED_SOURCE}.")
    print(f"  Skipped (name not found in docs): {', '.join(skipped) if skipped else 'none'}")
    print("  Default values and version numbers are from the spec + docs grep; re-check after Claude Code updates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
