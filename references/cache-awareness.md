# Cache awareness (B10 + B15, with v6 corrections)

[D] The cache prefix matches exactly; if the system prompt or tool definitions change, everything after is recomputed.

## B10 — spec text (verbatim)

CACHE'İ BOZAR (bir sonraki istek tam yeniden işlenir): /model değişimi · /effort değişimi · fast mode'u açmak · çıplak araç adını deny etmek · prefix'e yüklenen MCP araçlarının değişmesi/kopup yeniden bağlanması · Claude Code güncellemesi (ertesi başlatmada) · compaction (tasarım gereği).

CACHE'İ BOZMAZ: dosya düzenlemek · CLAUDE.md'yi oturum ortasında düzenlemek (ama uygulanmaz; /clear, /compact veya yeniden başlatmada yüklenir) · output style değiştirmek (aynı şekilde uygulanmaz) · permission mode değiştirmek (opusplan hariç) · skill/komut çağırmak · /recap · /rewind · subagent başlatmak · plugin'in skill/komut/agent/hook'unu açıp kapamak · ertelenmiş MCP araçları.

Kural: model ve effort'u oturumun başında seç; ortada değiştirme. Basit/zor iş karışıksa iki ayrı oturum aç.

## Corrections that override the table above (newer [D] wins)

| Item | Correction | Source |
|---|---|---|
| /effort | Opus 5.5 and Fable 5.1 keep the cache on effort change (API key or subscription). Other models break it and ask first while warm. Still breaks on Bedrock, Google Agent Platform, Claude apps gateway, `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`, HIPAA. | spec DZ-5 |
| Bare tool-name deny | Breaks the cache ONLY when tool search is off; with tool search on, the prefix is kept. Still: MinToken proposes scoped rules only. | spec DZ-5 |
| MCP connect/disconnect | Deferred tools (default): only additions, cache kept. Prefix-loaded: server connect/add breaks; stdio process death does not. | spec DZ-5 |
| Output style | Changing `outputStyle` mid-session applies from the next message and breaks the prefix (v2.1.251+). | C133 |
| Skill with `model:`/`effort:` frontmatter | That turn counts as a model/effort switch. | C82 |
| Images/PDF over the size cap | Oldest images are dropped in bulk -> re-processing from the earliest affected message. | C73/C171 |
| /cd | Does not rebuild the cache (v2.1.169+). | C171 |

Statusline `prompt_cache.last_miss_cause.causes` names the likely cause of the last miss (`tools_changed`, `system_prompt_changed`, `ttl_expired_5m`, `likely_server_side`, ...) [D: statusline page, checked 2026-10-10].

## B15 — TTL buckets

[D] Main conversation TTL: 1 hour on a Claude subscription (within plan usage); 5 minutes with API key, cloud provider, or usage credits. Exceeding the plan and moving to usage credits drops it from 1h to 5m.
Subagent / workflow / teammate / fork / compaction / session-title requests are a separate bucket, default 5 minutes.

Selectable (v2.1.242+): `promptCacheTtl` / `CLAUDE_CODE_PROMPT_CACHE_TTL` (main), `subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` (others), values `5m` or `1h`. 1h cache writes cost more and are wasted in short sessions. `FORCE_PROMPT_CACHING_5M=1` is a debugging switch.

TTL precedence (C171): `FORCE_PROMPT_CACHING_5M` > bucket env > bucket setting > subagent frontmatter `experimental.cacheTtl` > `ENABLE_PROMPT_CACHING_1H`.

Rule: first learn the user's bucket (subscription / API key / usage credits). Only warn "first message after a break is expensive" when that bucket's TTL was actually exceeded.

Check:
```
claude -p "hello" --output-format json
```
→ `usage.cache_creation.ephemeral_1h_input_tokens` / `ephemeral_5m_input_tokens`. Interactive: status line `prompt_cache.ttl` (MinToken D3 shows it) or `/usage` → `Prompt cache (main)`.

## Cheap vs expensive recovery

- Wrong direction → Esc + `/rewind` (returns to a warm, cached prefix) — cheaper than compaction (C114, C171).
- Topic change → `/clear` (zero cost; CLAUDE.md reloads).
- Long session at a natural break → `/compact <what to keep>` while the cache is warm (cheap). Cold `/compact` re-reads everything uncached (C28).
- Returning after 75+ min to a big session → prefer `/clear` + restate, or "resume from summary" (Pro/Max dialog, ~1h idle and ≥100k tokens) (C109/C171).
