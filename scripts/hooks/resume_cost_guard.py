#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken G2 (optional) — SessionStart hook, matcher "resume|fork".

Reads the documented resume fields (code.claude.com/docs/en/hooks, Claude Code
v2.1.251+, checked 2026-10-10): context_tokens, prompt_cache_likely_expired,
estimated_cache_write_usd, seconds_since_last_response.
If the cache is likely expired AND context_tokens >= RESUME_GUARD_TOKEN_THRESHOLD,
emits ONE factual warning (<= RESUME_GUARD_MAX_CHARS) as JSON `systemMessage`.

Why systemMessage: docs describe it as a "Warning message shown to the user".
Plain stdout of a SessionStart hook is ADDED TO CLAUDE'S CONTEXT, so this hook
never prints plain text. That systemMessage is NOT also added to the model's
context for SessionStart is not stated explicitly in the docs [I] — the async-hook
section contrasts it ("unlike a synchronous hook's systemMessage, neither field is
shown to you"), which supports but does not prove it.

  --help     this text
  --dry-run  print the decision in readable form (writes nothing anyway)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from _common import cfg_int, load_config  # noqa: E402


def message(event, cfg):
    if event.get("source") not in ("resume", "fork"):
        return None
    if not event.get("prompt_cache_likely_expired"):
        return None
    tokens = event.get("context_tokens") or 0
    if tokens < cfg_int(cfg, "RESUME_GUARD_TOKEN_THRESHOLD"):
        return None
    usd = event.get("estimated_cache_write_usd")
    idle = event.get("seconds_since_last_response")
    parts = [f"MinToken: cache likely cold; first message re-sends ~{tokens:,} tokens"]
    if isinstance(usd, (int, float)):
        parts.append(f"(est. ${usd:.2f} cache write, list price)")
    if isinstance(idle, (int, float)):
        parts.append(f"after {int(idle) // 60} min idle")
    msg = " ".join(parts) + ". Cheaper: /clear and restate the task, or /compact <focus> first."
    limit = cfg_int(cfg, "RESUME_GUARD_MAX_CHARS")
    return msg if len(msg) <= limit else msg[: limit - 1] + "…"


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    msg = message(event, load_config())
    if "--dry-run" in sys.argv:
        print("no warning" if msg is None else f"systemMessage ({len(msg)} chars): {msg}")
        return 0
    if msg:
        print(json.dumps({"systemMessage": msg}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
