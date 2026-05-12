#!/usr/bin/env python3
"""
Codex — PostToolUse Hook
Fires after every Write/Edit to the project's source root. Generates a
plain-language explanation of the changed file and updates the .codex/src/
mirror. Appends to codex.log.

Source root defaults to "src". Override per-project by creating
.codex/config.json with {"src_root": "your_dir"}.

Input: JSON on stdin from Claude Code
Required env: ANTHROPIC_API_KEY
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

CODEX_ROOT = ".codex"
LOG_PATH = os.path.join(CODEX_ROOT, "codex.log")


def get_src_root() -> str:
    """
    Read src_root from .codex/config.json if present, otherwise fall back
    to "src". Called once in main() so the hook always uses the project's
    configured root rather than the hardcoded default.
    """
    config_path = os.path.join(CODEX_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("src_root", "src")
    except (FileNotFoundError, json.JSONDecodeError):
        return "src"

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_diff(file_path: str) -> str:
    """Get git diff for the file. Falls back to full file content if no diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", file_path],
            capture_output=True, text=True, timeout=10
        )
        diff = result.stdout.strip()
        if diff:
            return diff
        # No diff means file is new/untracked — return full content
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return f"[New file — full content]\n{content}"
    except Exception as e:
        return f"[Could not retrieve diff: {e}]"


def get_explanation_path(file_path: str, src_root: str) -> Path:
    """
    Map <src_root>/auth/service.ps1 → .codex/<src_root>/auth/service.md
    Strip extension, add .md, swap root prefix.
    """
    p = Path(file_path)
    try:
        relative = p.relative_to(src_root)
    except ValueError:
        return None
    explanation_path = Path(CODEX_ROOT) / src_root / relative.with_suffix(".md")
    return explanation_path


def load_existing_explanation(path: Path) -> str:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def call_claude(file_path: str, diff: str, existing: str) -> str:
    """Call Anthropic API to generate the explanation."""
    import urllib.request
    import urllib.error

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "[Error: ANTHROPIC_API_KEY not set in environment]"

    existing_section = ""
    if existing:
        existing_section = f"""
The current explanation file for this source file is below.
Preserve the change log section and update the rest to reflect the new state.

<existing_explanation>
{existing[:3000]}
</existing_explanation>
"""

    prompt = f"""You are the Codex explanation engine. A source file was just written or edited.
Produce a plain-language technical explanation of this file for a developer who wants to understand
the system, not just the syntax.

File: {file_path}

Changes (git diff or full content if new):
<diff>
{diff[:4000]}
</diff>
{existing_section}

Write the explanation using this exact structure:

## {file_path}

### What This File Does
One paragraph. System-level description. What role does this file play in the running system?

### Why It Exists
What operational reality or constraint forced this file into being? What problem is it solving?

### What It Protects Against
What failure mode, edge case, or risk does this code defend against? If none, say so.

### Invariants
What conditions must always be true for this file to work correctly? List them.

### New Patterns (if any)
If this edit introduces a pattern not seen in the file before, name it and explain it briefly.
If no new patterns, omit this section.

### Change Log
Append one line: `- YYYY-MM-DD: <one sentence describing what changed>`
If an existing change log is present above, keep all prior entries and add the new one at the top.

Write in plain, direct prose. No padding. Be specific to this actual file, not generic."""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return f"[API error {e.code}: {body[:300]}]"
    except Exception as e:
        return f"[Request failed: {e}]"


def append_log(file_path: str, summary: str):
    """Append a structured entry to codex.log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = (
        f"\n[{timestamp}] WRITE {file_path}\n"
        f"  → {summary}\n"
    )
    os.makedirs(CODEX_ROOT, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)


def extract_one_liner(explanation: str) -> str:
    """Pull the first sentence of 'What This File Does' for the log."""
    for line in explanation.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            # First non-heading, non-list line
            sentence = line.split(".")[0].strip()
            if sentence:
                return sentence[:200]
    return "Explanation generated"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        # Not valid JSON — bail silently (non-blocking exit)
        sys.exit(0)

    # Extract file path from the tool response
    # PostToolUse input shape: tool_input.file_path (Write) or tool_input.path (Edit)
    tool_input = event.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path", "")

    if not file_path:
        sys.exit(0)

    src_root = get_src_root()

    # Only process files inside the configured source root
    if not file_path.startswith(src_root + os.sep) and not file_path.startswith(src_root + "/"):
        sys.exit(0)

    # Resolve explanation output path
    explanation_path = get_explanation_path(file_path, src_root)
    if explanation_path is None:
        sys.exit(0)

    # Get what changed
    diff = get_diff(file_path)

    # Load existing explanation if any
    existing = load_existing_explanation(explanation_path)

    # Generate explanation via Claude API
    explanation = call_claude(file_path, diff, existing)

    # Write explanation file
    explanation_path.parent.mkdir(parents=True, exist_ok=True)
    with open(explanation_path, "w", encoding="utf-8") as f:
        f.write(explanation)

    # Append to log
    one_liner = extract_one_liner(explanation)
    append_log(file_path, one_liner)

    # Exit 0 — non-blocking, let Claude continue
    sys.exit(0)


if __name__ == "__main__":
    main()
