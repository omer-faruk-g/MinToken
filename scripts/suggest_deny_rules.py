#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken B2 — propose SCOPED permissions.deny Read rules for build/cache folders.

Scans a project for folders/files Claude rarely needs to read (build/, .gradle/,
out/, run/, logs/, .idea/, node_modules/, __pycache__, *.log, *.jar, *.class ...)
and proposes `Read(<pattern>)` deny rules. Never proposes a bare tool name.

Docs (code.claude.com/docs/en/permissions, checked 2026-10-10):
  * Read/Edit rules use gitignore syntax; as a deny rule `Read(build/**)` matches a
    `build` directory at any depth under the current directory.
  * `.claudeignore` has NO effect — move its entries into Read deny rules.
  * Read deny covers Claude's file tools; a Bash `grep -r`/`find` may still show
    those files (spec C176).
  * Scoped rules do not touch the cached prefix; bare tool-name denies remove the
    tool and can break the cache when tool search is off (spec B2/DZ-5).

Default is DRY-RUN (diff only). Write: --apply + explicit 'evet'/'yes'.
Target: <project>/.claude/settings.json (or --target local -> settings.local.json).
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_json, write_with_consent  # noqa: E402

DIRS = ["build", ".gradle", "out", "run", "logs", ".idea", "node_modules", "__pycache__",
        "dist", "target", ".venv", "venv", ".next", "coverage", "graphify-out", ".pytest_cache", ".mypy_cache"]
FILE_GLOBS = {".log": "*.log", ".jar": "*.jar", ".class": "*.class", ".pyc": "*.pyc", ".map": "*.map"}
SKIP_WALK = {".git"}
SCOPED_RE = re.compile(r"^[A-Za-z]+\(.+\)$")


def scan(root, max_entries=200000):
    found_dirs, found_exts, seen = set(), set(), 0
    for cur, dirs, files in os.walk(root):
        for d in list(dirs):
            if d in DIRS:
                found_dirs.add(d)
                dirs.remove(d)  # do not descend into it
            elif d in SKIP_WALK:
                dirs.remove(d)
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in FILE_GLOBS:
                found_exts.add(ext)
        seen += len(files) + len(dirs)
        if seen > max_entries:
            break
    return found_dirs, found_exts


def propose(found_dirs, found_exts):
    rules = [f"Read({d}/**)" for d in sorted(found_dirs)]
    rules += [f"Read({FILE_GLOBS[e]})" for e in sorted(found_exts)]
    return rules


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project", nargs="?", default=".", help="project root (default: cwd)")
    p.add_argument("--target", choices=["project", "local"], default="project")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="diff only (default)")
    p.add_argument("--confirm", help="'evet'/'yes' — only after the user confirmed in chat")
    a = p.parse_args(argv)

    root = os.path.abspath(a.project)
    found_dirs, found_exts = scan(root)
    rules = propose(found_dirs, found_exts)
    bad = [r for r in rules if not SCOPED_RE.match(r)]
    assert not bad, f"refusing unscoped rules: {bad}"

    claudeignore = os.path.join(root, ".claudeignore")
    if os.path.exists(claudeignore):
        print("NOTE: .claudeignore found — per docs it has no effect. Consider moving its entries to Read() deny rules.\n")
    if not rules:
        print(f"No build/cache folders found under {root}. Nothing to propose.")
        return 0

    path = os.path.join(root, ".claude", "settings.json" if a.target == "project" else "settings.local.json")
    current = read_json(path)
    if current is None and os.path.exists(path):
        print(f"ERROR: {path} is not valid JSON; refusing to touch it.")
        return 1
    current = current or {}
    new = dict(current)
    perms = dict(new.get("permissions") or {})
    deny = list(perms.get("deny") or [])
    added = [r for r in rules if r not in deny]
    perms["deny"] = deny + added
    new["permissions"] = perms

    print(f"Scanned {root}\nProposed scoped rules ({len(added)} new):")
    for r in added:
        print(f"  {r}")
    print()
    write_with_consent(path, current, new, a.apply and not a.dry_run, a.confirm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
