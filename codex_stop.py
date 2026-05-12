#!/usr/bin/env python3
"""
Codex — Stop Hook
Fires when Claude Code finishes a session turn. Reads the session transcript
and produces a plain-language session summary in .codex/sessions/YYYY-MM-DD.md

Input: JSON on stdin from Claude Code
Required env: ANTHROPIC_API_KEY
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

CODEX_ROOT = ".codex"
SESSIONS_DIR = os.path.join(CODEX_ROOT, "sessions")

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_transcript(transcript_path: str) -> str:
    """Read the session transcript JSONL and extract text content."""
    if not transcript_path or not os.path.exists(transcript_path):
        return ""

    lines = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                    role = entry.get("role", "")
                    content = entry.get("content", "")
                    # Content can be string or list of blocks
                    if isinstance(content, str) and content.strip():
                        lines.append(f"[{role}] {content[:500]}")
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "").strip()
                                if text:
                                    lines.append(f"[{role}] {text[:500]}")
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception:
        return ""

    return "\n".join(lines[-200:])  # Last 200 entries max — keep context window sane


def read_log_tail() -> str:
    """Read recent codex.log entries for the summary."""
    log_path = os.path.join(CODEX_ROOT, "codex.log")
    if not os.path.exists(log_path):
        return ""
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Return last 3000 chars — recent session entries
        return content[-3000:] if len(content) > 3000 else content
    except Exception:
        return ""


def load_existing_summary(session_path: Path) -> str:
    """Load today's existing summary if it exists (session may span multiple stops)."""
    if session_path.exists():
        with open(session_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def call_claude(transcript: str, log_tail: str, existing: str, date_str: str) -> str:
    """Call Anthropic API to generate the session summary."""
    import urllib.request
    import urllib.error

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return f"# Session {date_str}\n\n[Error: ANTHROPIC_API_KEY not set — summary could not be generated]"

    existing_section = ""
    if existing:
        existing_section = f"""
An earlier summary exists for today's session. Merge new information into it rather than starting fresh.
Preserve all prior content and extend it.

<existing_summary>
{existing[:2000]}
</existing_summary>
"""

    prompt = f"""You are Codex. A Claude Code session just ended. Write a summary that serves two purposes:
accurate documentation of what was built and decided, and a teaching resource that closes the
learning loop so the developer can explain what was built and continue confidently next session.

Session date: {date_str}

Recent tool log entries (files written/edited):
<log>
{log_tail}
</log>

Session transcript (recent exchanges):
<transcript>
{transcript[:4000]}
</transcript>
{existing_section}

Write using this exact structure:

# Session {date_str}

## What Was Built or Changed
Plain English. What exists now that did not before, or works differently.
Be specific — name files, features, and behaviours.

## Key Decisions
What choices were made? Include alternatives that were considered and rejected.

## Files Touched
| File | What Changed |
|------|-------------|
| path/to/file.ext | One-line description |

## What You Should Be Able to Explain
Write 3-5 specific questions the developer must answer without looking at the code.
Write as actual questions grounded in what this session built — not topics or bullet summaries.
Example format: "Why does offboard-user.ps1 write the log to Desktop rather than the project root?"

## What To Read Before Next Session
Which .codex/src/ files are most relevant to pick up where this left off?
For each: name the file and one sentence on why it matters for what comes next.
Derive from the files touched this session and the open questions below.

## Open Questions and Risks
Anything uncertain, fragile, or needing follow-up. If none, write "None identified."

Write in plain, direct prose. No padding. Specific to this actual session."""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1500,
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
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return f"# Session {date_str}\n\n[API error {e.code}: {body[:300]}]"
    except Exception as e:
        return f"# Session {date_str}\n\n[Request failed: {e}]"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    # CRITICAL: Prevent infinite loop. If a previous Stop hook already fired
    # this session, bail immediately.
    if event.get("stop_hook_active"):
        sys.exit(0)

    transcript_path = event.get("transcript_path", "")
    date_str = datetime.now().strftime("%Y-%m-%d")
    session_path = Path(SESSIONS_DIR) / f"{date_str}.md"

    # Read inputs
    transcript = read_transcript(transcript_path)
    log_tail = read_log_tail()
    existing = load_existing_summary(session_path)

    # If nothing happened this session, skip (no log entries, no transcript)
    if not transcript and not log_tail:
        sys.exit(0)

    # Generate summary
    summary = call_claude(transcript, log_tail, existing, date_str)

    # Write session file
    Path(SESSIONS_DIR).mkdir(parents=True, exist_ok=True)
    with open(session_path, "w", encoding="utf-8") as f:
        f.write(summary)

    # Exit 0 — allow Claude to stop normally
    sys.exit(0)


if __name__ == "__main__":
    main()
