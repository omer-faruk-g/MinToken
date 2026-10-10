# Settings / env cheat sheet (G3)

Columns: key | where (S = settings.json, E = env, C = command) | effect | doc page (per spec) | verified | cost | item.
**verified** = re-checked against code.claude.com in this install on 2026-10-10. Rows in the second table come from the spec; every key NAME was re-checked against the full docs corpus on 2026-10-10 (last column = first page that defines/mentions it). Default values and version numbers are as stated by the spec/docs — re-check after updates. Nothing here is applied automatically.

## Verified in this install (2026-10-10)
| Key | Where | Effect | Page | Cost | Item |
|---|---|---|---|---|---|
| `hooks.PreToolUse` `updatedInput` + `permissionDecision` | S | rewrites tool input; `allow` skips the prompt, `ask` shows the modified input; deny/ask rules still apply; ignored with `defer` | hooks | — | D1 |
| matcher `"*"` / `""` / omitted | S | matches all | hooks | — | D2 |
| SessionStart `source`, `context_tokens`, `prompt_cache_likely_expired`, `estimated_cache_write_usd`, `seconds_since_last_response` | hook input | resume/fork only, v2.1.251+ | hooks | — | G2/C109 |
| `systemMessage` | hook output | "Warning message shown to the user" (sync hooks); not-in-model-context for SessionStart is [I] | hooks | — | G2 |
| PostToolUseFailure exit 2 | hook | stderr shown to Claude | hooks | — | D2 |
| `statusLine` `{type:"command", command}` | S | runs locally, no API tokens | statusline | — | D3 |
| `context_window.used_percentage`, `current_usage.*`, `prompt_cache.{warm,ttl,expires_at,hit_ratio,misses,last_miss_cause}` | statusline input | prompt_cache v2.1.251+, last_miss_cause v2.1.260+ | statusline | — | D3 |
| `permissions.deny` `Read(<gitignore pattern>)` | S | deny `Read(build/**)` matches `build` at any depth | permissions | Bash grep/find may still show files | B2 |
| `.claudeignore` | file | **no effect** — use Read deny rules | permissions | — | B2 |

## From the spec — names re-checked against the docs on 2026-10-10 (221 pages, changelog to v2.1.296)
| Key | Where | Effect | Page | Cost | Item | Found in docs |
|---|---|---|---|---|---|---|
| `promptCacheTtl` / `CLAUDE_CODE_PROMPT_CACHE_TTL` | S/E | main TTL 5m/1h (v2.1.242+) | prompt-caching | 1h writes cost more | C15/C134 | promptCacheTtl: settings-reference; CLAUDE_CODE_PROMPT_CACHE_TTL: settings-reference |
| `subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` | S/E | subagent/workflow TTL | prompt-caching | same | C16/C92 | subagentPromptCacheTtl: settings-reference; CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL: settings-reference |
| `FORCE_PROMPT_CACHING_5M`, `DISABLE_PROMPT_CACHING*`, `ENABLE_PROMPT_CACHING_1H` | E | debug / cache off / 1h | prompt-caching, env-vars | — | C110 | FORCE_PROMPT_CACHING_5M: settings-reference; DISABLE_PROMPT_CACHING: env-vars; ENABLE_PROMPT_CACHING_1H: settings-reference |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | E | tool search off, cache side effects | env-vars | gateway compat | C110/C127 | CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS: env-vars |
| `CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH` | E | mid-session prompt change | env-vars | — | C110 | CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH: env-vars |
| `outputStyle` | S | style text every request; change breaks prefix | output-styles | Concise = less explanation | C51/C133 | outputStyle: settings-reference |
| `skillOverrides`, `skillListingBudgetFraction`, `skillListingMaxDescChars`, `SLASH_COMMAND_TOOL_CHAR_BUDGET` | S/E | shrink skill listing | skills | skill not auto-discovered | C52/C126 | skillOverrides: settings-reference; skillListingBudgetFraction: settings-reference; skillListingMaxDescChars: settings-reference; SLASH_COMMAND_TOOL_CHAR_BUDGET: env-vars |
| `claudeMdExcludes` | S | skip unrelated CLAUDE.md | memory | — | C55 | claudeMdExcludes: settings-reference |
| `autoMemoryEnabled` / `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | S/E | auto memory off | memory | no cross-session learning | C56 | autoMemoryEnabled: settings-reference; CLAUDE_CODE_DISABLE_AUTO_MEMORY: settings-reference |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | E | --add-dir also loads CLAUDE.md/rules | memory | — | C57 | CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD: env-vars |
| `includeGitInstructions` / `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS` | S/E | drop commit/PR instructions | settings | Claude lacks commit conventions | C58/C169 | includeGitInstructions: settings-reference; CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS: settings-reference |
| `disableClaudeAiConnectors`, `ENABLE_CLAUDEAI_MCP_SERVERS`, `strictMcpConfig` | S/E | claude.ai connectors off | mcp | connectors gone | C60/C164 | disableClaudeAiConnectors: settings-reference; ENABLE_CLAUDEAI_MCP_SERVERS: settings-reference; strictMcpConfig: agent-sdk__claude-code-features |
| `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH` | E | 2,048 default; descriptions loaded through tool search are cut at 16,384 (changelog) — both apply, no conflict | mcp | broken tool use if too short | C61/DZ-1 | CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH: env-vars |
| `autoCompactWindow`, `modelSettings.<m>.autoCompactWindow`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `CLAUDE_CODE_DISABLE_1M_CONTEXT`, `/autocompact` | S/E/C | compaction threshold (~967K on 1M models — re-verify) | model-config | earlier compaction loses detail | C62/C170 | autoCompactWindow: settings-reference; modelSettings.: settings-reference; CLAUDE_CODE_AUTO_COMPACT_WINDOW: settings-reference; CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: env-vars; CLAUDE_CODE_DISABLE_1M_CONTEXT: env-vars |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | E | higher = less room before compaction | env-vars | — | C66 | CLAUDE_CODE_MAX_OUTPUT_TOKENS: env-vars |
| `BASH_MAX_OUTPUT_LENGTH` (≤150,000), `bashOutputMaxChars` (≤128,000) | E/S | inline Bash output cap (~30,000 default) | tools-reference | reruns of truncated commands | C68/DZ-6 | BASH_MAX_OUTPUT_LENGTH: settings-reference; bashOutputMaxChars: settings-reference |
| `taskOutputMaxChars` | S | REMOVED in v2.1.277 — do not suggest | — | — | DZ-6 | taskOutputMaxChars: settings-reference |
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | E | larger full reads | env-vars | expensive | C69 | CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS: env-vars |
| `MAX_MCP_OUTPUT_TOKENS` | E | MCP result cap (25,000; warn 10,000) | mcp | results cut | C71/C173 | MAX_MCP_OUTPUT_TOKENS: env-vars |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | E | parallel read-only tools (10) | env-vars | slower | C75 | CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY: env-vars |
| `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` | E | subagent model (env no longer beats frontmatter since v2.1.251 unless _FORCE, v2.1.257+) | sub-agents | quality | C83/DZ-7 | CLAUDE_CODE_SUBAGENT_MODEL: env-vars; CLAUDE_CODE_SUBAGENT_MODEL_FORCE: env-vars |
| `CLAUDE_CODE_FORK_SUBAGENT` | E | fork mode on/off | sub-agents | — | C87/C131 | CLAUDE_CODE_FORK_SUBAGENT: env-vars |
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (20), `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (3) | E | limits; `..._PER_SESSION` is a no-op since v2.1.224 | sub-agents | — | DZ-8 | CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS: env-vars; CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH: env-vars |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | E | no background tasks | env-vars | feature loss | C88 | CLAUDE_CODE_DISABLE_BACKGROUND_TASKS: env-vars |
| `workflowSizeGuideline`, `disableWorkflows`/`CLAUDE_CODE_DISABLE_WORKFLOWS`, `workflowKeywordTriggerEnabled`, `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` | S/E | workflow size/trigger | workflows | — | C89/C90/C151 | workflowSizeGuideline: settings-reference; disableWorkflows: settings-reference; CLAUDE_CODE_DISABLE_WORKFLOWS: settings-reference; workflowKeywordTriggerEnabled: settings-reference; CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS: env-vars |
| `CLAUDE_CODE_DISABLE_ADVISOR_TOOL`, `advisorModel`, `/advisor` | E/S/C | advisor re-reads transcript uncached | advisor | no second opinion | C93/C172 | CLAUDE_CODE_DISABLE_ADVISOR_TOOL: settings-reference; advisorModel: settings-reference |
| `/goal` "or stop after N turns", `CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0` | C/E | bound goal loops | goal | — | C94/C156 | CLAUDE_CODE_GOAL_CHECKIN_MINUTES: env-vars |
| `fastMode`, `fastModePerSessionOptIn`, `CLAUDE_CODE_DISABLE_FAST_MODE` | S/E | fast mode persistence | fast-mode | slower | C95/C172 | fastMode: settings-reference; fastModePerSessionOptIn: settings-reference; CLAUDE_CODE_DISABLE_FAST_MODE: settings-reference |
| `effortLevel`, `maxEffortLevel`, `CLAUDE_CODE_EFFORT_LEVEL` | S/E | effort (top-level `effortLevel` ignored on Opus 5.5+) | model-config | quality | C96/C170 | effortLevel: settings-reference; maxEffortLevel: settings-reference; CLAUDE_CODE_EFFORT_LEVEL: settings-reference |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | E | background-job model | model-config | — | C97/C129/C161 | ANTHROPIC_DEFAULT_HAIKU_MODEL: env-vars |
| `fallbackModel`, `switchModelsOnFlag` | S | fallback = cold-cache turn | model-config | availability | C98/C119/C172 | fallbackModel: settings-reference; switchModelsOnFlag: settings-reference |
| `autoContinueAtUsageLimit` | S | unattended resume at reset | settings | work waits | C99/C155 | autoContinueAtUsageLimit: settings-reference |
| `CLAUDE_CODE_AUTO_MODE_SERVER`, `permissions.defaultMode`, `permissions.disableAutoMode`, `autoMode.classifyAllShell`, `useAutoModeDuringPlan` | E/S | auto-mode classifier | permission-modes | safety vs prompts | C100/C158/DZ-4 | CLAUDE_CODE_AUTO_MODE_SERVER: env-vars; permissions.defaultMode: settings-reference; permissions.disableAutoMode: settings-reference; autoMode.classifyAllShell: settings-reference; useAutoModeDuringPlan: settings-reference |
| `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` | E | WebSearch cap (200) | tools-reference | research stops | C101/C178 | CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION: env-vars |
| `awaySummaryEnabled`/`CLAUDE_CODE_ENABLE_AWAY_SUMMARY`, `promptSuggestionEnabled`/`CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION`, `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` | S/E | background helper requests | settings, interactive-mode | features gone | C102/C103/C157 | awaySummaryEnabled: settings-reference; CLAUDE_CODE_ENABLE_AWAY_SUMMARY: settings-reference; promptSuggestionEnabled: settings-reference; CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION: settings-reference; CLAUDE_CODE_DISABLE_TERMINAL_TITLE: settings-reference |
| `crossSessionInbound` (accept/hold/refuse) | S | idle-session wake-ups | agent-view | messages wait | C34/C148 | crossSessionInbound: settings-reference |
| `CLAUDE_CODE_RETRY_WATCHDOG(_MAX_WAIT_MS)`, `CLAUDE_CODE_MAX_RETRIES`, `CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES` | E | retry multipliers | env-vars, changelog | resilience | C115/C116 | CLAUDE_CODE_RETRY_WATCHDOG: env-vars; CLAUDE_CODE_MAX_RETRIES: env-vars; CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES: env-vars |
| `ANTHROPIC_BASE_URL`, `ENABLE_TOOL_SEARCH` | E | gateway: tool search off unless set | llm-gateway | — | C117/C173 | ANTHROPIC_BASE_URL: settings-reference; ENABLE_TOOL_SEARCH: env-vars |
| `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` | E | -p background wait (0 = unlimited) | headless | — | C123 | CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS: env-vars |
| `CLAUDE_CODE_RESUME_INTERRUPTED_TURN(_MAX_AGE_MS)` | E | resume half turn | env-vars | stale prompt rerun | C124 | CLAUDE_CODE_RESUME_INTERRUPTED_TURN: env-vars |
| `syncClaudeAiPlugins`, `syncClaudeAiSkills`, `CLAUDE_CODE_SYNC_SKILLS` | S/E | synced plugins/skills | plugins | lose synced items | C136 | syncClaudeAiPlugins: settings-reference; syncClaudeAiSkills: settings-reference; CLAUDE_CODE_SYNC_SKILLS: settings-reference |
| `diagnostics` (LSP plugin) | plugin S | per-edit diagnostics | plugins | fewer type errors surfaced | C138 | diagnostics: env-vars |
| `disableAllHooks` | S | hooks + status line + mods off | hooks | MinToken hooks off too | C141 | disableAllHooks: settings-reference |
| `ENABLE_STOP_REVIEW`, `ENABLE_COMMIT_REVIEW`, `ENABLE_CODE_SECURITY_REVIEW`, `SECURITY_GUIDANCE_DISABLE` | E | security-guidance plugin reviews | plugins | less review | C143 | ENABLE_STOP_REVIEW: security-guidance; ENABLE_COMMIT_REVIEW: security-guidance; ENABLE_CODE_SECURITY_REVIEW: security-guidance; SECURITY_GUIDANCE_DISABLE: security-guidance |
| `enableArtifact`, `CLAUDE_CODE_DISABLE_ARTIFACT`, `CLAUDE_CODE_ARTIFACT_COMMENTS(_AUTOREACT)` | S/E | artifacts / auto-replies | artifacts | feature gone | C149 | enableArtifact: settings-reference; CLAUDE_CODE_DISABLE_ARTIFACT: settings-reference; CLAUDE_CODE_ARTIFACT_COMMENTS: env-vars |
| `disableAgentView` / `CLAUDE_CODE_DISABLE_AGENT_VIEW`, `autoVerify` (launch.json) | S/E | desktop agent view / auto-verify | desktop | feature gone | C153 | disableAgentView: settings-reference; CLAUDE_CODE_DISABLE_AGENT_VIEW: settings-reference; autoVerify: desktop |
| `respondToBashCommands`, `askUserQuestionTimeout` | S | `!cmd` triggers reply; unanswered question timeout | interactive-mode | — | C157 | respondToBashCommands: settings-reference; askUserQuestionTimeout: settings-reference |
| `sandbox.allowUnsandboxedCommands`, `permissions.blockReadsOutsideWorkingDirectories` | S | sandbox escape round-trips | sandboxing | safety trade-off | C159 | sandbox.allowUnsandboxedCommands: settings-reference; permissions.blockReadsOutsideWorkingDirectories: settings-reference |
| `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS`, `CLAUDE_CODE_DISABLE_ATTACHMENTS`, `CLAUDE_CODE_ENABLE_TODO_TOOLS` | E | shrink prompt | env-vars | behaviour/quality | C169 | CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT: env-vars; CLAUDE_CODE_DISABLE_CLAUDE_MDS: env-vars; CLAUDE_CODE_DISABLE_BUNDLED_SKILLS: settings-reference; CLAUDE_CODE_DISABLE_ATTACHMENTS: settings-reference; CLAUDE_CODE_ENABLE_TODO_TOOLS: env-vars |
| `language` | S | small fixed instruction each request | settings | — | C177 | language: settings-reference |
| `skipWebFetchPreflight` | S | skip domain pre-check | tools-reference | safety | C164 | skipWebFetchPreflight: settings-reference |
| `MCP_TOOL_TIMEOUT`, `CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS`, `MCP_TIMEOUT` | E | MCP timeouts | mcp | — | C173 | MCP_TOOL_TIMEOUT: env-vars; CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS: env-vars; MCP_TIMEOUT: env-vars |
| `DISABLE_AUTOUPDATER`, `DISABLE_UPDATES`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | E | update/traffic switches (NONESSENTIAL also kills feature flags → advisor/Remote Control) | env-vars | features | C25/DZ-9 | DISABLE_AUTOUPDATER: settings-reference; DISABLE_UPDATES: env-vars; CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: settings-reference |
| `worktree.sparsePaths`, `worktree.symlinkDirectories` | S | large-repo worktrees | large-codebases | — | C176 | worktree.sparsePaths: settings-reference; worktree.symlinkDirectories: settings-reference |

## Corrections DZ-1..DZ-12 (differ from v4/v5)
- **DZ-1** MCP description cap: 2,048 by default (mcp, settings-reference); tool-search-loaded descriptions are cut at 16,384 (changelog). Checked 2026-10-10: not a conflict, two cases.
- **DZ-2** `-p` `usage` excludes subagents → use `modelUsage`/`total_cost_usd` (measurement.md).
- **DZ-3** v2.1.283+ interactive sessions default to auto mode.
- **DZ-4** Auto-mode classifier: server-side review by default since v2.1.278 for API/Enterprise/cloud/gateway (no classifier charge); client fallback is billed; Pro/Max/Team: classifier calls do not count toward limits (w32). C37's "unverified" is superseded.
- **DZ-5** Effort/bare-deny/MCP cache rules refined (cache-awareness.md).
- **DZ-6** `bashOutputMaxChars` cap 128,000; `taskOutputMaxChars` removed.
- **DZ-7** Subagent model resolution order; `_FORCE`.
- **DZ-8** 200-subagent cap removed; concurrency 20, depth 3; `--max-budget-usd` covers subagents.
- **DZ-9** `DISABLE_AUTOUPDATER` only stops background checks.
- **DZ-10** apiKeyHelper fails "within three attempts"; cache 5 min (`CLAUDE_CODE_API_KEY_HELPER_TTL_MS`).
- **DZ-11** Fast-mode price, checked on fast-mode page 2026-10-10: $8/$40 per MTok on Opus 5.5, $10/$50 on Opus 5 and Opus 4.8. Not a conflict (different models). Re-check before quoting.
- **DZ-12** Sonnet 5 promo price ended 31 Aug — verify current pricing.
