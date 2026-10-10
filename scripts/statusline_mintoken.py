#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken D3 — status line: "ctx 38% · cache 91% · warm 1h (42m left) · miss 2".

Field names checked against code.claude.com/docs/en/statusline (2026-10-10):
context_window.used_percentage, context_window.current_usage.{input_tokens,
cache_creation_input_tokens, cache_read_input_tokens}, prompt_cache.{warm, ttl,
expires_at, hit_ratio, misses, last_miss_cause.causes} (prompt_cache: v2.1.251+).
Docs: "The status line runs locally and does not consume API tokens."

  --help     this text
  --dry-run  same as normal run (the script never writes files)
"""
import json
import sys
import time


def render(data, now=None):
    now = now or time.time()
    parts = []
    cw = data.get("context_window") or {}
    pct = cw.get("used_percentage")
    if pct is None:
        cu = cw.get("current_usage") or {}
        size = cw.get("context_window_size") or 0
        used = sum(cu.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        pct = 100 * used / size if size and used else None
    parts.append(f"ctx {int(pct)}%" if pct is not None else "ctx -")

    pc = data.get("prompt_cache")
    if pc:
        hr = pc.get("hit_ratio")
        if hr is not None:
            parts.append(f"cache {round(hr * 100)}%")
        ttl = pc.get("ttl") or "?"
        exp = pc.get("expires_at")
        if pc.get("warm"):
            left = f" ({max(0, int((exp - now) // 60))}m left)" if isinstance(exp, (int, float)) else ""
            parts.append(f"warm {ttl}{left}")
        elif pc.get("caching_observed") is False:
            parts.append("cache off?")
        else:
            parts.append(f"cold {ttl}")
        if pc.get("misses"):
            cause = ((pc.get("last_miss_cause") or {}).get("causes") or [None])[0]
            parts.append(f"miss {pc['misses']}" + (f" ({cause})" if cause else ""))
    return " · ".join(parts)


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    out = sys.stdout
    if hasattr(out, "reconfigure"):
        out.reconfigure(encoding="utf-8", errors="replace")
    out.write(render(data) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
