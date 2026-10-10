#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken D2 (optional) — deterministic runaway brake.

Register for three events (install_hooks.py does this):
  UserPromptSubmit          -> reset the consecutive-tool counter
  PreToolUse  (matcher "*") -> count tool calls; at MAX_CONSECUTIVE_TOOLS, or on the
                               MAX_REREAD-th Read of the same file, return
                               permissionDecision "ask" so the USER decides to continue
  PostToolUseFailure        -> on the MAX_SAME_ERROR-th identical error, exit 2 so
                               Claude sees "stop, find root cause" on stderr

Docs checked 2026-10-10 (code.claude.com/docs/en/hooks): matcher "*" matches all;
"ask" shows the reason in the permission prompt; PostToolUseFailure exit 2 shows
stderr to Claude. UNVERIFIED: the exact PostToolUseFailure error field name — this
script reads `error`, falling back to the whole payload minus ids.
State: one small JSON per session in the temp dir. Thresholds: references/config.md.

  --help     this text
  --dry-run  process stdin event, print the decision, do not save state
"""
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from _common import cfg_int, load_config  # noqa: E402


def state_path(session_id):
    safe = hashlib.sha1(str(session_id).encode()).hexdigest()[:16]
    return os.path.join(tempfile.gettempdir(), f"mintoken_counter_{safe}.json")


def load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"tools": 0, "reads": {}, "errors": {}}


def handle(event, state, cfg):
    """Mutates state; returns (stdout_obj_or_None, stderr_text_or_None, exit_code)."""
    name = event.get("hook_event_name")
    if name == "UserPromptSubmit":
        state["tools"] = 0
        return None, None, 0
    if name == "PreToolUse":
        state["tools"] = state.get("tools", 0) + 1
        reason = None
        limit = cfg_int(cfg, "MAX_CONSECUTIVE_TOOLS")
        if state["tools"] >= limit and state["tools"] % limit == 0:
            reason = f"MinToken: {state['tools']} tool calls without a user message. Continue?"
        if event.get("tool_name") == "Read":
            fp = (event.get("tool_input") or {}).get("file_path", "")
            reads = state.setdefault("reads", {})
            reads[fp] = reads.get(fp, 0) + 1
            if reads[fp] == cfg_int(cfg, "MAX_REREAD"):
                reason = f"MinToken: {os.path.basename(fp)} read {reads[fp]} times this session. Continue?"
        if reason:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                           "permissionDecisionReason": reason}}, None, 0
        return None, None, 0
    if name == "PostToolUseFailure":
        err = event.get("error")
        if err is None:
            err = {k: v for k, v in event.items() if k not in ("session_id", "tool_use_id", "prompt_id", "transcript_path")}
        key = hashlib.sha1(json.dumps(err, sort_keys=True, default=str).encode()).hexdigest()[:12]
        errors = state.setdefault("errors", {})
        errors[key] = errors.get(key, 0) + 1
        if errors[key] == cfg_int(cfg, "MAX_SAME_ERROR"):
            return None, ("MinToken: same error seen twice. Do not retry blindly: state the root cause "
                          "in 3 lines, then change method or ask the user."), 2
    return None, None, 0


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    path = state_path(event.get("session_id", "nosession"))
    state = load_state(path)
    out, err, code = handle(event, state, load_config())
    if "--dry-run" in sys.argv:
        print(json.dumps({"stdout": out, "stderr": err, "exit": code, "state": state}, indent=2))
        return 0
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except OSError:
        pass
    if out:
        print(json.dumps(out))
    if err:
        print(err, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
