# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared helpers for MinToken scripts (stdlib only, no network)."""
import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = Path(__file__).resolve().parent.parent
REF_DIR = SKILL_DIR / "references"
CONFIG_PATH = REF_DIR / "config.md"

_DEFAULTS = {
    "MAX_CONSECUTIVE_TOOLS": "20",
    "MAX_SAME_ERROR": "2",
    "MAX_REREAD": "3",
    "CONTEXT_SIZE_WARN": "100000",
    "FILTER_HEAD_LINES": "5",
    "FILTER_TAIL_LINES": "5",
    "FILTER_STACK_FRAMES": "3",
    "FILTER_MIN_LINES": "20",
    "RESUME_GUARD_TOKEN_THRESHOLD": "50000",
    "RESUME_GUARD_MAX_CHARS": "300",
    "HOOK_PERMISSION_DECISION": "ask",
    "AUDIT_AGENT_DESC_WARN": "15000",
    "HOOK_INJECT_WARN_TOKENS": "2000",
}


def load_config():
    """Read `KEY = value` lines from references/config.md; env MINTOKEN_<KEY> overrides."""
    cfg = dict(_DEFAULTS)
    try:
        for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Z][A-Z0-9_]+)\s*=\s*(\S+)", line.strip())
            if m:
                cfg[m.group(1)] = m.group(2)
    except OSError:
        pass
    for k in list(cfg):
        if os.environ.get("MINTOKEN_" + k):
            cfg[k] = os.environ["MINTOKEN_" + k]
    return cfg


def cfg_int(cfg, key):
    try:
        return int(cfg[key])
    except (KeyError, ValueError):
        return int(_DEFAULTS[key])


def read_json(path):
    """Return parsed JSON or None; never raises on missing/invalid files."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def claude_home(override=None):
    if override:
        return Path(override)
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        return Path(os.environ["CLAUDE_CONFIG_DIR"])
    return Path.home() / ".claude"


def rough_tokens(text):
    """chars/4 — a rough estimate, NOT a tokenizer."""
    return (len(text) + 3) // 4


def settings_diff(path, old, new):
    import difflib
    a = json.dumps(old, indent=2, ensure_ascii=False).splitlines() if old is not None else []
    b = json.dumps(new, indent=2, ensure_ascii=False).splitlines()
    return "\n".join(difflib.unified_diff(a, b, f"{path} (current)", f"{path} (proposed)", lineterm=""))


def write_with_consent(path, old, new, apply, confirm):
    """Print diff; write only if apply AND the user typed yes/evet (tty) or passed --confirm evet.

    Returns True if written. Always makes a timestamped backup first.
    """
    import shutil
    import time
    path = Path(path)
    diff = settings_diff(path, old, new)
    if not diff:
        print("No change needed.")
        return False
    print(diff)
    if not apply:
        print("\n[dry-run] Nothing written. Re-run with --apply to write (explicit 'evet'/'yes' required).")
        return False
    answer = (confirm or "").strip().lower()
    if not answer and sys.stdin.isatty():
        try:
            answer = input(f"\nWrite these changes to {path}? Type 'evet' or 'yes': ").strip().lower()
        except EOFError:
            answer = ""
    if answer not in ("evet", "yes"):
        print("Not confirmed. Nothing written.")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        bak = path.with_name(path.name + f".mintoken-bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, bak)
        print(f"Backup: {bak}")
    path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Written: {path}")
    return True
