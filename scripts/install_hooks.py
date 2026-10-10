#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken D4 — install/uninstall optional hooks and status line into settings.json.

Default is DRY-RUN: shows the unified diff and writes nothing.
Writing requires --apply AND an explicit 'evet'/'yes' (typed at the prompt, or
--confirm evet after the user said so in chat). A timestamped backup is made first.

Components (pick with --only, default d1,d3):
  d1  PreToolUse  matcher "Bash"              -> hooks/pretool_bash_filter.py
  d2  UserPromptSubmit + PreToolUse "*" + PostToolUseFailure -> hooks/session_counter.py
  d3  statusLine                               -> statusline_mintoken.py
  g2  SessionStart matcher "resume|fork"       -> hooks/resume_cost_guard.py

Examples:
  python install_hooks.py                       # dry-run diff for d1,d3
  python install_hooks.py --only d1,d2,d3,g2    # dry-run diff for everything
  python install_hooks.py --apply               # asks for 'evet'
  python install_hooks.py --uninstall --apply   # removes every MinToken entry
"""
import argparse
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _common import claude_home, read_json, write_with_consent  # noqa: E402

MARK = "mintoken"


def cmd(script):
    py = sys.executable.replace("\\", "/")
    path = os.path.join(HERE, script).replace("\\", "/")
    return f'"{py}" "{path}"'


def entries(components):
    """[(event, matcher_or_None, script, timeout)]"""
    e = []
    if "d1" in components:
        e.append(("PreToolUse", "Bash", "hooks/pretool_bash_filter.py", 10))
    if "d2" in components:
        e += [("UserPromptSubmit", None, "hooks/session_counter.py", 5),
              ("PreToolUse", "*", "hooks/session_counter.py", 5),
              ("PostToolUseFailure", "*", "hooks/session_counter.py", 5)]
    if "g2" in components:
        e.append(("SessionStart", "resume|fork", "hooks/resume_cost_guard.py", 5))
    return e


def is_ours(hook):
    return MARK in str(hook.get("command", "")).lower()


def strip_ours(settings):
    s = copy.deepcopy(settings)
    hooks = s.get("hooks") or {}
    for event in list(hooks):
        groups = []
        for g in hooks[event]:
            kept = [h for h in g.get("hooks", []) if not is_ours(h)]
            if kept:
                g = dict(g, hooks=kept)
                groups.append(g)
        if groups:
            hooks[event] = groups
        else:
            del hooks[event]
    if "hooks" in s and not s["hooks"]:
        del s["hooks"]
    if MARK in str((s.get("statusLine") or {}).get("command", "")).lower():
        del s["statusLine"]
    return s


def add(settings, components, force_statusline):
    s = strip_ours(settings)  # idempotent: re-adding replaces old MinToken entries
    hooks = s.setdefault("hooks", {})
    for event, matcher, script, timeout in entries(components):
        group = {"hooks": [{"type": "command", "command": cmd(script), "timeout": timeout}]}
        if matcher is not None:
            group = {"matcher": matcher, **group}
        hooks.setdefault(event, []).append(group)
    if not hooks:
        del s["hooks"]
    if "d3" in components:
        if s.get("statusLine") and not force_statusline:
            print(f"NOTE: a statusLine already exists ({s['statusLine'].get('command')!r}); "
                  "keeping it. Use --force-statusline to replace.\n")
        else:
            s["statusLine"] = {"type": "command", "command": cmd("statusline_mintoken.py")}
    return s


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", default="d1,d3", help="comma list of d1,d2,d3,g2 (default d1,d3)")
    p.add_argument("--settings", help="settings.json path (default ~/.claude/settings.json)")
    p.add_argument("--apply", action="store_true", help="actually write (still needs explicit confirmation)")
    p.add_argument("--dry-run", action="store_true", help="show diff only (this is the default)")
    p.add_argument("--confirm", help="'evet'/'yes' — only pass after the user confirmed in chat")
    p.add_argument("--uninstall", action="store_true", help="remove all MinToken hooks/status line")
    p.add_argument("--force-statusline", action="store_true", help="replace an existing statusLine")
    a = p.parse_args(argv)

    path = a.settings or str(claude_home() / "settings.json")
    current = read_json(path)
    if current is None and os.path.exists(path):
        print(f"ERROR: {path} is not valid JSON; refusing to touch it.")
        return 1
    current = current or {}
    comps = {c.strip().lower() for c in a.only.split(",") if c.strip()}
    bad = comps - {"d1", "d2", "d3", "g2"}
    if bad:
        print(f"Unknown component(s): {', '.join(sorted(bad))}")
        return 2
    new = strip_ours(current) if a.uninstall else add(current, comps, a.force_statusline)
    if not a.uninstall:
        print("Safety: D1/D2 return permissionDecision 'ask' (never 'allow'), so no permission prompt is "
              "bypassed. Start a new session to be sure they are active. Escape hatch: MINTOKEN_RAW=1.\n")
    write_with_consent(path, current, new, a.apply and not a.dry_run, a.confirm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
