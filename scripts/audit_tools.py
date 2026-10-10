#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MinToken audit — READ-ONLY. Three sections:
  (1) installed token tools and what MinToken fixes for them
  (2) tools NOT installed and what MinToken does instead
  (3) general state: skill/agent/rule/command counts, MCP servers + prefix risk, TTL-bucket hints
All sizes are ROUGH estimates (bytes/4). Real numbers: /context and /usage.

Drain catalog:
  --drains            C1–C50   (references/hidden-drains.md)
  --drains2           C51–C114 (references/hidden-drains-2.md)
  --drains all        C1–C114 (114 items, as the spec's verification step 12 requires)
  --drains3           C115–C178 (references/hidden-drains-3.md; spec v5/v6 additions)
  --drain N           single item, N = 1..178

Testing: --home DIR (fake ~/.claude), --cwd DIR, --simulate headroom,graphify,... ,
--simulate none (pretend nothing is installed). Never writes anything; --dry-run is a no-op.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import REF_DIR, claude_home, read_json  # noqa: E402

DRAIN_FILES = [(1, 50, "hidden-drains.md"), (51, 114, "hidden-drains-2.md"), (115, 178, "hidden-drains-3.md")]
TOOLS = ["headroom", "graphify", "ponytail", "claude-mem", "ecc", "skillspector"]


# ---------- drains ----------
def load_drains():
    items = {}
    for _, _, name in DRAIN_FILES:
        try:
            text = (REF_DIR / name).read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            m = re.match(r"^C(\d+) ", line)
            if m:
                items[int(m.group(1))] = line
    return items


def print_drains(lo, hi):
    items = load_drains()
    for n in range(lo, hi + 1):
        if n in items:
            print(items[n])


# ---------- detection ----------
def rough(path):
    try:
        return Path(path).stat().st_size // 4
    except OSError:
        return 0


def count_md(d):
    d = Path(d)
    if not d.is_dir():
        return 0
    return sum(1 for p in d.rglob("*.md") if p.is_file())


def detect(home, cwd, simulate):
    """Return {tool: details-dict or None}."""
    settings = read_json(home / "settings.json") or {}
    plugins = " ".join(k.lower() for k, v in (settings.get("enabledPlugins") or {}).items() if v)
    skills = home / "skills"
    found = {}

    def sim(tool):
        if simulate is None:
            return None
        return tool in simulate

    # Headroom
    s = sim("headroom")
    if s if s is not None else (shutil.which("headroom") or importlib.util.find_spec("headroom")
                                or any(k.startswith("HEADROOM_") for k in os.environ)):
        found["headroom"] = {
            "HEADROOM_BEACON": os.environ.get("HEADROOM_BEACON", "<unset: telemetry beacon default ON [R: README]>"),
            "HEADROOM_OUTPUT_SHAPER": os.environ.get("HEADROOM_OUTPUT_SHAPER", "<unset: default off [R]>"),
        }
    # Graphify
    s = sim("graphify")
    if s if s is not None else (shutil.which("graphify") or (skills / "graphify").is_dir()):
        g = cwd / "graphify-out" / "graph.json"
        deny = json.dumps(settings.get("permissions", {}).get("deny", [])) + json.dumps(
            (read_json(cwd / ".claude" / "settings.json") or {}).get("permissions", {}).get("deny", []))
        found["graphify"] = {
            "graph.json": f"{g.stat().st_size // 1024} KB" if g.exists() else "none in cwd",
            "graphify-out denied": "yes" if "graphify-out" in deny else "NO",
            "SKILL.md body when invoked (rough tokens)": rough(skills / "graphify" / "SKILL.md"),
        }
    # Ponytail
    s = sim("ponytail")
    pt = sorted(p.name for p in skills.glob("ponytail*")) if skills.is_dir() else []
    if s if s is not None else (pt or "ponytail" in plugins):
        found["ponytail"] = {"skills": ", ".join(pt) or "(plugin)",
                             "SKILL.md bodies when invoked (rough tokens)": sum(rough(skills / n / "SKILL.md") for n in pt)}
    # claude-mem
    s = sim("claude-mem")
    cm_dir = Path.home() / ".claude-mem"
    if s if s is not None else ("claude-mem" in plugins or cm_dir.is_dir()):
        cms = read_json(cm_dir / "settings.json") or {}
        found["claude-mem"] = {
            "CLAUDE_MEM_ONLINE_OPTIN": os.environ.get("CLAUDE_MEM_ONLINE_OPTIN", cms.get("CLAUDE_MEM_ONLINE_OPTIN", "<unset>")),
            "provider/auth": f"{cms.get('CLAUDE_MEM_PROVIDER', '?')}/{cms.get('CLAUDE_MEM_CLAUDE_AUTH_METHOD', '?')}",
            "cloud sync configured": "yes" if cms.get("CLAUDE_MEM_CLOUD_SYNC_TOKEN") else "no",  # value never printed
        }
    # everything-claude-code
    s = sim("ecc")
    agents = home / "agents"
    ecc_marks = {"planner.md", "architect.md", "code-reviewer.md"}
    has_ecc = agents.is_dir() and ecc_marks <= {p.name for p in agents.glob("*.md")}
    if s if s is not None else (has_ecc or "everything-claude-code" in plugins):
        found["ecc"] = {"agents": count_md(agents), "rules": count_md(home / "rules"),
                        "commands": count_md(home / "commands"),
                        "skills": sum(1 for p in skills.glob("*/SKILL.md")) if skills.is_dir() else 0}
    # SkillSpector
    s = sim("skillspector")
    if s if s is not None else shutil.which("skillspector"):
        found["skillspector"] = {"binary": shutil.which("skillspector") or "(simulated)"}
    return found


INSTALLED_FIX = {
    "headroom": [
        "Set HEADROOM_BEACON=off if you do not want the telemetry beacon [R: README].",
        "HEADROOM_OUTPUT_SHAPER=1 is off by default [R]; enable only after measuring (references/measurement.md).",
        "Automatic model routing is enterprise-only, not in open source [R].",
        "It does not compress the frozen prefix -> session hygiene rules (B4) still apply.",
    ],
    "graphify": [
        "Add Read(graphify-out/**) deny if missing (python suggest_deny_rules.py) — writes there can disturb cache [R: README].",
        "graph.json > 500 KB: never Read it; use `graphify query` and keep only node name + path.",
        "LLM extraction of docs/PDF costs tokens; for code prefer --code-only.",
    ],
    "ponytail": [
        "Rules are injected every turn and into every subagent [R: README].",
        "For one-line/typo/rename work suggest `/ponytail lite` or `/ponytail off`.",
        "Its benchmark (FastAPI+React, Haiku, n=4) is not evidence for Java/Fabric [R].",
    ],
    "claude-mem": [
        "Its observer makes model calls -> hidden usage [R: README]; with provider=claude/subscription it draws on YOUR plan.",
        "CLAUDE_MEM_ONLINE_OPTIN=true may send session data to a hosted service — check.",
        "SessionStart injects context every session: measure with /context; for short sessions net gain may be zero.",
    ],
    "ecc": [
        "15+ agents/rules/commands/skills: each description sits in context every turn (C52/C53/C135).",
        "Unscoped rules/ load into every session [D].",
        "README '200k->70k MCP' warning reflects old behaviour: MCP schemas are deferred by default now [D].",
        "Repo is under WorldFlowAI but README install commands point to affaan-m/everything-claude-code [G]: verify the source.",
    ],
    "skillspector": [
        "Run with --no-llm (LLM mode sends file contents to a provider [R: README]).",
        "Scan new skills/plugins before installing: skillspector scan <dir> --no-llm",
    ],
}
NOT_INSTALLED = {
    "headroom": "filter_log.py + D1 PreToolUse hook (install_hooks.py); keep only needed fields of 100+ line JSON/grep output; model routing -> references/model-routing.md",
    "graphify": "Grep -> Read(offset/limit); light discovery `find . -name '*.java' -not -path '*/build/*' | head -20`; consider a code-intelligence (LSP) plugin [D: costs]",
    "ponytail": "YAGNI ladder in SKILL.md: needed? exists? stdlib? installed dep? one line? then minimum code. Security/validation/a11y exempt",
    "claude-mem": "1–2 line dated notes in CLAUDE.md, rotate oldest after 50, total < 200 lines [D]; CLAUDE.md loads at session start / after /clear or /compact [D]",
    "ecc": "strategic compact -> B4; memory -> A4; model routing -> model-routing.md; MCP management -> B7",
    "skillspector": "Before installing a skill/MCP/hook, read README + files: network/telemetry, hooks, files touched, deps, base64/obfuscated commands; report doubts",
}
NAMES = {"headroom": "Headroom", "graphify": "Graphify", "ponytail": "Ponytail", "claude-mem": "claude-mem",
         "ecc": "everything-claude-code", "skillspector": "SkillSpector"}


def mcp_servers(home, cwd):
    out = []
    cj = read_json(home.parent / ".claude.json") if home == claude_home() else read_json(home / ".claude.json")
    cj = cj or {}
    for name, cfg in (cj.get("mcpServers") or {}).items():
        out.append(("user", name, cfg))
    proj = (cj.get("projects") or {}).get(str(cwd).replace("\\", "/")) or (cj.get("projects") or {}).get(str(cwd)) or {}
    for name, cfg in (proj.get("mcpServers") or {}).items():
        out.append(("local", name, cfg))
    for name, cfg in ((read_json(cwd / ".mcp.json") or {}).get("mcpServers") or {}).items():
        out.append(("project", name, cfg))
    return out


def hook_injections(home, n_files=5):
    """A4/C76: measure what SessionStart/UserPromptSubmit hooks injected in the latest transcripts.

    Transcript lines with attachment.type == "hook_success" carry the hook's stdout/content [G: observed
    transcript format]. Sizes are chars/4, rough.
    """
    try:
        from _common import cfg_int, load_config
        warn_at = cfg_int(load_config(), "HOOK_INJECT_WARN_TOKENS")
    except Exception:
        warn_at = 2000
    def mtime(p):
        try:
            return p.stat().st_mtime
        except OSError:  # e.g. Windows paths over 260 chars
            return 0
    files = sorted((home / "projects").glob("*/*.jsonl"), key=mtime, reverse=True)[:n_files]
    per_event = {}
    for f in files:
        try:
            fh = f.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for raw in fh:
                if '"hook_success"' not in raw:
                    continue
                try:
                    att = json.loads(raw).get("attachment") or {}
                except ValueError:
                    continue
                ev = att.get("hookEvent")
                if ev not in ("SessionStart", "UserPromptSubmit", "UserPromptExpansion", "PostToolUse", "PreToolUse"):
                    continue
                text = att.get("stdout") or att.get("content") or ""
                try:  # JSON output: only additionalContext reaches the model
                    obj = json.loads(text)
                    text = ((obj.get("hookSpecificOutput") or {}).get("additionalContext") or "") if isinstance(obj, dict) else text
                except ValueError:
                    pass
                src = "claude-mem" if "claude-mem" in text else "other"
                key = (ev, src)
                cnt, total, mx = per_event.get(key, (0, 0, 0))
                per_event[key] = (cnt + 1, total + len(text), max(mx, len(text)))
    out = []
    for (ev, src), (cnt, total, mx) in sorted(per_event.items()):
        if mx == 0:
            continue
        warn = f"  <- above HOOK_INJECT_WARN_TOKENS={warn_at}" if mx // 4 > warn_at else ""
        out.append(f"Hook injection {ev} ({src}): {cnt}x in last {len(files)} transcripts, max ~{mx // 4} tokens each (rough){warn}")
    if not out:
        out.append("Hook injections: none found in the latest transcripts")
    return out


def general(home, cwd):
    lines = []
    skills = home / "skills"
    n_sk = sum(1 for _ in skills.glob("*/SKILL.md")) if skills.is_dir() else 0
    desc_chars = 0
    for p in skills.glob("*/SKILL.md") if skills.is_dir() else []:
        m = re.search(r"^description:\s*(.+)$", p.read_text(encoding="utf-8", errors="replace"), re.M)
        desc_chars += len(m.group(1)) if m else 0
    lines.append(f"User skills: {n_sk} (descriptions ~{desc_chars // 4} tokens, rough) — listed every turn [C7/C52]")
    for d in ("agents", "rules", "commands", "skills"):
        n = count_md(home / d) if d != "skills" else n_sk
        pn = count_md(cwd / ".claude" / d)
        warn = "  <- 15+, consider pruning" if n + pn >= 15 else ""
        lines.append(f"{d}: user {n}, project .claude/ {pn}{warn}")
    if (home / "rules").is_dir() or (cwd / ".claude" / "rules").is_dir():
        lines.append("rules/ without `paths:` load into every session [D: memory]")
    servers = mcp_servers(home, cwd)
    if servers:
        for scope, name, cfg in servers:
            risk = " alwaysLoad=TRUE (schema in prefix every turn, C5)" if cfg.get("alwaysLoad") else ""
            lines.append(f"MCP [{scope}] {name}{risk}")
    else:
        lines.append("MCP servers in ~/.claude.json / .mcp.json: none (claude.ai connectors and plugin MCPs not visible here -> /mcp)")
    env = os.environ
    if env.get("ANTHROPIC_BASE_URL") and "api.anthropic.com" not in env["ANTHROPIC_BASE_URL"]:
        lines.append("ANTHROPIC_BASE_URL set: tool search may be OFF -> all MCP schemas in prefix (C6/C117)")
    if env.get("CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"):
        lines.append("CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS set: tool search stays OFF (C127)")
    if env.get("ENABLE_TOOL_SEARCH"):
        lines.append(f"ENABLE_TOOL_SEARCH={env['ENABLE_TOOL_SEARCH']} (false/auto may load schemas up front, C173)")
    if env.get("CLAUDE_CODE_USE_VERTEX"):
        lines.append("Vertex (Google Cloud Agent Platform): models earlier than Claude 4.5 have no tool search -> MCP schemas in prefix (B7/C6) [D: prompt-caching]")
    if env.get("CLAUDE_CODE_USE_FOUNDRY"):
        lines.append("Microsoft Foundry: an Azure-hosted deployment that rejects tool search loads MCP schemas up front (B7/C6) [D: prompt-caching]")
    lines.append("Prefix-loaded MCP schemas happen with: alwaysLoad servers, ENABLE_TOOL_SEARCH=auto below threshold or false, "
                 "custom gateway, pre-4.5 Vertex models, Azure-hosted Foundry [D]. Real size: /context 'MCP tools'.")
    for line in hook_injections(home):
        lines.append(line)
    # TTL bucket hints (B15)
    if any(env.get(k) for k in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")):
        bucket = "cloud provider -> main TTL 5m by default [D]"
    elif env.get("ANTHROPIC_API_KEY"):
        bucket = "ANTHROPIC_API_KEY set -> likely API-key billing, main TTL 5m [D]"
    else:
        bucket = "no API key/cloud env -> likely subscription, main TTL 1h (5m once on usage credits) [D]"
    lines.append("TTL bucket hint: " + bucket + ". Verify: statusline prompt_cache.ttl or /usage.")
    return lines


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--drains", nargs="?", const="1", help="list C1–C50; 'all' = C1–C114 (spec step 12)")
    p.add_argument("--drains2", action="store_true", help="list C51–C114")
    p.add_argument("--drains3", action="store_true", help="list C115–C178 (spec v5/v6)")
    p.add_argument("--drain", type=int, help="print one item (1–178)")
    p.add_argument("--home", help="fake ~/.claude directory (testing)")
    p.add_argument("--cwd", help="project dir (default: cwd)")
    p.add_argument("--simulate", help="comma list of tools to pretend installed, or 'none'")
    p.add_argument("--json", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="no-op: this script never writes")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.drain is not None:
        item = load_drains().get(a.drain)
        print(item or f"No item C{a.drain} (valid: 1–178)")
        return 0 if item else 1
    if a.drains or a.drains2 or a.drains3:
        if a.drains == "all":
            print_drains(1, 114)
        elif a.drains:
            print_drains(1, 50)
        if a.drains2:
            print_drains(51, 114)
        if a.drains3:
            print_drains(115, 178)
        return 0

    home = claude_home(a.home)
    cwd = Path(a.cwd or os.getcwd())
    simulate = None
    if a.simulate:
        simulate = set() if a.simulate.strip().lower() == "none" else {s.strip().lower() for s in a.simulate.split(",")}
    found = detect(home, cwd, simulate)
    gen = general(home, cwd)
    if a.json:
        print(json.dumps({"installed": found, "not_installed": [t for t in TOOLS if t not in found], "general": gen},
                         indent=2, default=str))
        return 0

    print("=== (1) Installed token tools — MinToken patches their gaps ===")
    if not found:
        print("  (none detected)")
    for t in TOOLS:
        if t in found:
            print(f"\n- {NAMES[t]}: " + "; ".join(f"{k}={v}" for k, v in found[t].items()))
            for fix in INSTALLED_FIX[t]:
                print(f"    * {fix}")
    print("\n=== (2) Not installed — MinToken does the job itself ===")
    missing = [t for t in TOOLS if t not in found]
    if not missing:
        print("  (all six detected)")
    for t in missing:
        print(f"- {NAMES[t]}: {NOT_INSTALLED[t]}")
    print("\n=== (3) General state (rough estimates; real numbers: /context, /usage, /mcp) ===")
    for line in gen:
        print(f"- {line}")
    print("\nSettings/env audit: python audit_config.py   |   Drain catalog: --drains all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
