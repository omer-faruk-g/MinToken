#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken — measure real usage from local Claude Code transcripts (READ-ONLY).

Complements the /usage protocol in references/measurement.md (Section E / G5) with
numbers you can re-run at any time, e.g. before and after a settings change:

  (1) context size per API request: median / p90 / max, share of requests above
      100K / 200K / 400K and the share of input-side tokens they carry (C2, C62)
  (2) totals per session: requests, peak context, input-side tokens, main model
  (3) build/test output replay: what the D1 hook would rewrite and how much
      filter_log.py would remove; runs D1 skips (pipes, &&) and PowerShell runs

Source: ~/.claude/projects/*/*.jsonl. Requests are de-duplicated by message id
(parallel tool calls repeat it — spec DZ-2). Token counts in (1)/(2) come from the
transcript `usage` fields; sizes in (3) are chars/4 (rough, not a tokenizer).
Report results as "measured change: X -> Y" — never as a promised percentage.

  --since YYYY-MM-DD   only transcripts modified on/after this date (before/after a change)
  --last N             only the N most recently modified transcripts
  --projects DIR       transcripts root (default: ~/.claude/projects)
  --json               machine-readable output
  --dry-run            no-op: this script never writes anything
"""
import argparse
import contextlib
import datetime
import io
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "hooks"))
from _common import claude_home, load_config  # noqa: E402

BUILD_RE = re.compile(r"(gradlew|gradle\b|mvnw?\b|npm\s+(run\s+)?test|pytest|go\s+test|cargo\s+(build|test)|dotnet\s+(build|test))")


def lp(p):
    """Windows long-path safe open path (transcript paths often exceed 260 chars)."""
    s = os.path.abspath(str(p))
    return "\\\\?\\" + s if os.name == "nt" and not s.startswith("\\\\?\\") else s


def mtime(p):
    try:
        return os.stat(lp(p)).st_mtime
    except OSError:
        return 0


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def filtered_len(text):
    import filter_log
    buf = io.StringIO()
    old = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(text.encode("utf-8")), encoding="utf-8")
    try:
        with contextlib.redirect_stdout(buf):
            filter_log.main(["--mapping", os.devnull])
    finally:
        sys.stdin = old
    return len(buf.getvalue())


def scan(files):
    import pretool_bash_filter as d1
    cfg = load_config()
    ctx, sessions, seen_ids = [], [], set()
    builds = {"d1": [], "bash_skipped": [], "powershell": []}
    for f in files:
        if f.stem in seen_ids:  # same session id copied under two project dirs
            continue
        seen_ids.add(f.stem)
        seen, sizes, models, uses, results = set(), [], {}, {}, []
        try:
            fh = open(lp(f), encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for raw in fh:
                if '"assistant"' not in raw and '"tool_result"' not in raw:
                    continue
                try:
                    o = json.loads(raw)
                except ValueError:
                    continue
                msg = o.get("message") or {}
                if o.get("type") == "assistant":
                    mid = msg.get("id")
                    if mid and mid not in seen:
                        seen.add(mid)
                        u = msg.get("usage") or {}
                        sizes.append(sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")))
                        models[msg.get("model")] = models.get(msg.get("model"), 0) + 1
                    for c in msg.get("content") or []:
                        if isinstance(c, dict) and c.get("type") == "tool_use":
                            uses[c.get("id")] = (c.get("name"), c.get("input") or {})
                elif o.get("type") == "user" and isinstance(msg.get("content"), list):
                    for c in msg["content"]:
                        if isinstance(c, dict) and c.get("type") == "tool_result":
                            name, inp = uses.get(c.get("tool_use_id"), (None, {}))
                            cmd = inp.get("command") or ""
                            if name in ("Bash", "PowerShell") and BUILD_RE.search(cmd):
                                results.append((name, cmd, text_of(c.get("content")), len(sizes)))
        if not sizes or all(s == 0 for s in sizes):
            continue
        ctx += sizes
        sessions.append({"transcript": f.parent.name[-40:], "requests": len(sizes), "peak": max(sizes),
                         "input_side": sum(sizes), "model": max(models, key=models.get)})
        for name, cmd, text, at in results:
            later = max(0, len(sizes) - at)  # later requests that re-send this result
            if name == "PowerShell":
                builds["powershell"].append({"cmd": cmd[:80], "tok": len(text) // 4})
            elif d1.decide({"tool_name": "Bash", "tool_input": {"command": cmd}}, cfg) is not None:
                after = filtered_len(text) // 4
                builds["d1"].append({"cmd": cmd[:80], "tok": len(text) // 4, "after": after, "resent": later})
            else:
                builds["bash_skipped"].append({"cmd": cmd[:80], "tok": len(text) // 4})
    return ctx, sessions, builds


def summarize(ctx):
    if not ctx:
        return {}
    s, tot = sorted(ctx), sum(ctx)
    q = lambda p: s[int(p * (len(s) - 1))]
    out = {"requests": len(s), "median": q(.5), "p90": q(.9), "max": s[-1], "input_side_total": tot, "above": {}}
    for th in (100_000, 200_000, 400_000):
        big = [c for c in s if c > th]
        out["above"][th] = {"requests_pct": len(big) * 100 // len(s), "tokens_pct": sum(big) * 100 // tot if tot else 0}
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--since", help="YYYY-MM-DD: only transcripts modified on/after this date")
    p.add_argument("--last", type=int, help="only the N most recent transcripts")
    p.add_argument("--projects", help="transcripts root (default ~/.claude/projects)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="no-op: this script never writes")
    a = p.parse_args(argv)

    root = Path(a.projects) if a.projects else claude_home() / "projects"
    files = sorted(root.glob("*/*.jsonl"), key=mtime, reverse=True)
    if a.since:
        cut = datetime.datetime.strptime(a.since, "%Y-%m-%d").timestamp()
        files = [f for f in files if mtime(f) >= cut]
    if a.last:
        files = files[: a.last]
    ctx, sessions, builds = scan(files)
    summ = summarize(ctx)
    if a.json:
        print(json.dumps({"context": summ, "sessions": sessions, "builds": builds}, indent=1))
        return 0
    if not summ:
        print(f"No usable transcripts under {root} (filters: since={a.since}, last={a.last}).")
        return 0
    print(f"=== (1) Context per API request — {summ['requests']} requests in {len(sessions)} transcripts ===")
    print(f"  median {summ['median']:,} | p90 {summ['p90']:,} | max {summ['max']:,} tokens (transcript usage fields)")
    for th, v in summ["above"].items():
        print(f"  >{th // 1000}K: {v['requests_pct']}% of requests carry {v['tokens_pct']}% of input-side tokens")
    print("  Cached re-reads still count toward plan limits [D: C2]. Big here -> C62 autoCompactWindow, B4 /clear.")
    print("\n=== (2) Sessions (largest first) ===")
    for s in sorted(sessions, key=lambda x: -x["input_side"])[:10]:
        print(f"  ...{s['transcript']}: {s['requests']} req, peak {s['peak']:,}, total {s['input_side']:,}, {s['model']}")
    d = builds["d1"]
    print("\n=== (3) Build/test output replay (chars/4, rough) ===")
    print(f"  D1 would rewrite {len(d)} runs: ~{sum(x['tok'] for x in d):,} -> ~{sum(x['after'] for x in d):,} tok when first read; "
          f"~{sum((x['tok'] - x['after']) * x['resent'] for x in d):,} tok fewer across later re-sends")
    print(f"  D1 skips (pipes/&&/redirects): {len(builds['bash_skipped'])} runs, ~{sum(x['tok'] for x in builds['bash_skipped']):,} tok")
    print(f"  PowerShell tool (not covered by D1): {len(builds['powershell'])} runs, ~{sum(x['tok'] for x in builds['powershell']):,} tok")
    print("\nCompare two windows, e.g. before/after a change:  --since 2026-10-11  vs. the full history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
