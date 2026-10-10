#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Filter long build/test/log output before it enters Claude's context.

Keeps: first/last N lines, ERROR/FAILURE/Exception/WARN lines, the first K frames
of each stack trace. Collapses: repeated lines, download lines, Gradle
UP-TO-DATE/NO-SOURCE/SKIPPED task lines. Shortens UUID/hash/hex/base64 blobs;
originals go to a JSON mapping file.

Usage:
  some_build 2>&1 | python filter_log.py
  python filter_log.py build.log --estimate-tokens
  python filter_log.py build.log --dry-run      # stats only, writes nothing
"""
import argparse
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import cfg_int, load_config, rough_tokens  # noqa: E402

UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
HASH_RE = re.compile(r"\b(?:[0-9a-f]{64}|[0-9a-f]{40}|[0-9A-F]{64}|[0-9A-F]{40})\b")
HEX_RE = re.compile(r"\b(?:0x[0-9a-fA-F]{8,}|[0-9a-f]{16,}|[0-9A-F]{16,})\b")
B64_RE = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])")

IMPORTANT_RE = re.compile(
    r"(ERROR|FAILURE|FAILED|FAIL\b|Exception|Error:|error:|\bError\b|WARN|warning:|"
    r"Caused by|What went wrong|BUILD (SUCCESSFUL|FAILED)|Tests? run:|AssertionError|Traceback|"
    r"^\s*\*\s*(Try|Where|What)|panic:|npm ERR!|(?i:\bfailed\b|\bfailure\b))"
)
FRAME_RE = re.compile(r"^\s+(at\s|\.\.\.\s\d+\s(more|common frames))|^\s+File \".*\", line \d+")
TASK_NOOP_RE = re.compile(r"^> Task \S+ (UP-TO-DATE|NO-SOURCE|SKIPPED|FROM-CACHE)\s*$")
DOWNLOAD_RE = re.compile(r"^\s*(Download(ing|ed)?|Fetching|Resolving|Progress)\b", re.I)


class Shortener:
    def __init__(self):
        self.mapping = {}
        self.count = 0

    def _sub(self, regex, label, text, with_len):
        def repl(m):
            s = m.group(0)
            # base64 heuristic: require a digit and a mixed-case letter to avoid eating words/paths
            if label == "B64" and not (re.search(r"\d", s) and re.search(r"[a-z]", s) and re.search(r"[A-Z]", s)):
                return s
            self.count += 1
            key = f"[{label}:{len(s)}]" if with_len else f"[{label}]"
            self.mapping.setdefault(key, [])
            if s not in self.mapping[key]:
                self.mapping[key].append(s)
            return key
        return regex.sub(repl, text)

    def __call__(self, line):
        line = self._sub(UUID_RE, "UUID", line, False)
        line = self._sub(HASH_RE, "HASH", line, False)
        line = self._sub(B64_RE, "B64", line, True)
        line = self._sub(HEX_RE, "HEX", line, True)
        return line


def normalize(line):
    """Key for 'same line modulo numbers/urls' de-duplication."""
    line = re.sub(r"https?://\S+", "<url>", line)
    return re.sub(r"\d+", "#", line).strip()


def filter_lines(lines, cfg):
    head, tail = cfg_int(cfg, "FILTER_HEAD_LINES"), cfg_int(cfg, "FILTER_TAIL_LINES")
    frames_keep = cfg_int(cfg, "FILTER_STACK_FRAMES")
    n = len(lines)
    keep = set(range(min(head, n))) | set(range(max(0, n - tail), n))
    out = []
    noop_tasks = 0
    downloads = 0
    frame_run = 0
    frames_dropped = 0
    last_norm, repeat = None, 0

    def flush_frames():
        nonlocal frames_dropped
        if frames_dropped:
            out.append(f"\t... {frames_dropped} more frames")
            frames_dropped = 0

    def flush_repeat():
        nonlocal repeat
        if repeat:
            out.append(f"    [previous line repeated {repeat}x]")
            repeat = 0

    for i, line in enumerate(lines):
        if FRAME_RE.match(line):
            frame_run += 1
            if frame_run <= frames_keep:
                out.append(line)
            else:
                frames_dropped += 1
            continue
        flush_frames()
        frame_run = 0
        if TASK_NOOP_RE.match(line):
            noop_tasks += 1
            continue
        if DOWNLOAD_RE.match(line) and i not in keep:
            downloads += 1
            continue
        if i in keep or IMPORTANT_RE.search(line):
            norm = normalize(line)
            if norm == last_norm and i not in keep:
                repeat += 1
                continue
            flush_repeat()
            last_norm = norm
            out.append(line)
    flush_frames()
    flush_repeat()
    summary = []
    if noop_tasks:
        summary.append(f"[{noop_tasks} tasks UP-TO-DATE/NO-SOURCE/SKIPPED/FROM-CACHE collapsed]")
    if downloads:
        summary.append(f"[{downloads} download/progress lines collapsed]")
    return summary + out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", nargs="?", help="log file (default: stdin)")
    p.add_argument("--estimate-tokens", action="store_true", help="print rough chars/4 estimate (NOT a tokenizer)")
    p.add_argument("--mapping", help="where to write the original-value mapping JSON (default: temp dir)")
    p.add_argument("--no-shorten", action="store_true", help="do not replace UUID/hash/hex/base64")
    p.add_argument("--min-lines", type=int, help="pass through output shorter than this (default from config.md)")
    p.add_argument("--dry-run", action="store_true", help="print statistics only; write no mapping file")
    a = p.parse_args(argv)

    cfg = load_config()
    if a.file:
        with open(a.file, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    else:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    lines = raw.splitlines()
    min_lines = a.min_lines if a.min_lines is not None else cfg_int(cfg, "FILTER_MIN_LINES")

    shorten = Shortener()
    result = lines if len(lines) < min_lines else filter_lines(lines, cfg)
    if not a.no_shorten:
        result = [shorten(l) for l in result]  # only shown lines go to the mapping
    text = "\n".join(result)

    mapping_note = ""
    if shorten.mapping and not a.dry_run:
        path = a.mapping or os.path.join(tempfile.gettempdir(), f"mintoken_map_{os.getpid()}.json")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(shorten.mapping, fh, indent=1)
            mapping_note = f"=== {shorten.count} values shortened; originals: {path} ==="
        except OSError:
            mapping_note = f"=== {shorten.count} values shortened; mapping could not be written ==="

    out = sys.stdout
    if hasattr(out, "reconfigure"):
        out.reconfigure(encoding="utf-8", errors="replace")
    if not a.dry_run:
        if len(lines) >= min_lines:
            out.write(f"=== Filtrelenmiş log: {len(lines)} → {len(result)} satır (MINTOKEN_RAW=1 ile ham çıktı) ===\n")
        out.write(text + ("\n" if text else ""))
        if mapping_note:
            out.write(mapping_note + "\n")
    else:
        out.write(f"[dry-run] lines {len(lines)} -> {len(result)}; values to shorten: {shorten.count}\n")
    if a.estimate_tokens:
        out.write(f"=== rough token estimate (chars/4, not a real tokenizer): {rough_tokens(raw)} -> {rough_tokens(text)} ===\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
