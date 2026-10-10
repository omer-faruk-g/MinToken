#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken D1 — PreToolUse hook (matcher: Bash).

If the Bash command is a plain build/test runner (gradlew, gradle, mvn, npm test,
pytest, go test ...), rewrite it so its output goes through filter_log.py before
Claude sees it. The runner's exit code is preserved; if the filter fails, the
raw output is printed instead.

Safety (verified against code.claude.com/docs/en/hooks, 2026-10-10):
  * `updatedInput` must be paired with a permissionDecision. "allow" SKIPS the
    permission prompt, so MinToken never returns it. Default is "ask": the user
    sees the rewritten command and approves it (deny/ask rules still apply).
  * HOOK_PERMISSION_DECISION=none (config.md / env MINTOKEN_HOOK_PERMISSION_DECISION)
    omits the decision. Whether updatedInput is applied without a decision is NOT
    documented — unverified, use at your own risk.
Escape hatch: MINTOKEN_RAW=1 -> hook does nothing.

  --help       this text
  --dry-run    read hook JSON from stdin, print what would be returned (human readable)
"""
import json
import os
import re
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from _common import load_config  # noqa: E402

FILTER = os.path.join(os.path.dirname(HERE), "filter_log.py").replace("\\", "/")
RUNNER_RE = re.compile(
    r"^(?:[A-Z_][A-Z0-9_]*=\S+\s+)*"                       # optional VAR=val prefixes
    r"(?:\./gradlew(?:\.bat)?|gradlew(?:\.bat)?|gradle|\./mvnw|mvnw|mvn|"
    r"npm\s+(?:run\s+)?test|npx\s+(?:jest|vitest)|yarn\s+test|pnpm\s+test|"
    r"pytest|python3?\s+-m\s+pytest|go\s+test|cargo\s+(?:build|test)|dotnet\s+(?:build|test))\b"
)
# Only simple commands: no pipes, redirects, chaining, subshells, or background.
UNSAFE_RE = re.compile(r"[|;&<>`$()]|\n")


def build_command(cmd):
    py = sys.executable.replace("\\", "/")
    inner = cmd.strip()
    # Exit code from PIPESTATUS[0] (the runner). tee keeps a raw copy: if the filter
    # fails (PIPESTATUS[2] != 0) the raw output is printed instead. Runs in a subshell
    # so `exit` never closes the caller's shell.
    return (
        "( __mt_log=$(mktemp); "
        f"{{ {inner} ; }} 2>&1 | tee \"$__mt_log\" | {shlex.quote(py)} {shlex.quote(FILTER)} 2>/dev/null; "
        "__mt_ps=(\"${PIPESTATUS[@]}\"); "
        "[ \"${__mt_ps[2]}\" != 0 ] && cat \"$__mt_log\"; "
        "rm -f \"$__mt_log\"; exit \"${__mt_ps[0]}\" )"
    )


def decide(event, cfg):
    """Return the hook output dict, or None to leave the call untouched."""
    if os.environ.get("MINTOKEN_RAW") == "1":
        return None
    if event.get("tool_name") != "Bash":
        return None
    tool_input = event.get("tool_input") or {}
    cmd = tool_input.get("command") or ""
    if tool_input.get("run_in_background") or "MINTOKEN_RAW=1" in cmd or "filter_log.py" in cmd:
        return None
    if UNSAFE_RE.search(cmd) or not RUNNER_RE.match(cmd.strip()):
        return None
    new_input = dict(tool_input)
    new_input["command"] = build_command(cmd)
    out = {"hookEventName": "PreToolUse", "updatedInput": new_input}
    decision = cfg.get("HOOK_PERMISSION_DECISION", "ask").lower()
    if decision == "ask":
        out["permissionDecision"] = "ask"
        out["permissionDecisionReason"] = "MinToken: output will be filtered (MINTOKEN_RAW=1 for raw)."
    return {"hookSpecificOutput": out}


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0  # never break the tool call on bad input
    result = decide(event, load_config())
    if "--dry-run" in sys.argv:
        print("no change" if result is None else json.dumps(result, indent=2))
        return 0
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
