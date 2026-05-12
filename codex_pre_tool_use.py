#!/usr/bin/env python3
"""
Codex — PreToolUse Hook
Fires before every Write/Edit to the project's source root. If a .codex
explanation exists for the target file, prints it to stdout so Claude has
prior context before making changes.

Stdout with exit 0 is injected into Claude's context by Claude Code — this
is how the hint reaches Claude without blocking execution.

If no explanation exists (first write), exits 0 silently.

Input: JSON on stdin from Claude Code
No API calls. No external dependencies beyond stdlib.
"""

import json
import os
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

CODEX_ROOT = ".codex"


def get_src_root() -> str:
    """
    Read src_root from .codex/config.json if present, otherwise fall back
    to "src". Matches the logic in codex_post_tool_use.py exactly so both
    hooks operate on the same directory.
    """
    config_path = os.path.join(CODEX_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("src_root", "src")
    except (FileNotFoundError, json.JSONDecodeError):
        return "src"


def get_explanation_path(file_path: str, src_root: str) -> Path:
    """
    Map <src_root>/auth/service.ps1 → .codex/<src_root>/auth/service.md
    Matches the logic in codex_post_tool_use.py exactly.
    Returns None if the file is not under src_root.
    """
    p = Path(file_path)
    try:
        relative = p.relative_to(src_root)
    except ValueError:
        return None
    return Path(CODEX_ROOT) / src_root / relative.with_suffix(".md")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = event.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path", "")

    if not file_path:
        sys.exit(0)

    src_root = get_src_root()

    if not file_path.startswith(src_root + os.sep) and not file_path.startswith(src_root + "/"):
        sys.exit(0)

    explanation_path = get_explanation_path(file_path, src_root)
    if explanation_path is None:
        sys.exit(0)

    if not explanation_path.exists():
        # First write — no prior context to inject
        sys.exit(0)

    try:
        context = explanation_path.read_text(encoding="utf-8")
    except Exception:
        sys.exit(0)

    print(f"[Codex] Prior understanding of {file_path}:")
    print(context)
    print("[End Codex context]")

    sys.exit(0)


if __name__ == "__main__":
    main()
