#!/usr/bin/env python3
"""
Codex — Retroactive Generator
Backfills .codex/ explanations and session summaries for an existing project
that did not have Codex installed from the start.

Usage:
    python retro.py [--force] [repo_path]

    repo_path  — absolute path to the git repo root (default: current directory)
    --force    — overwrite existing .codex/ files (default: skip already-done files)

Output:
    .codex/<src_root>/<name>.md   — one explanation per source file
    .codex/sessions/YYYY-MM-DD.md — one session summary per calendar day

Required env: ANTHROPIC_API_KEY

The script reads .codex/config.json for src_root (defaults to "src").
Binary files (detected by null bytes or known binary extensions) are skipped.
Re-runs are cheap by default — only missing files are generated.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

MODEL = "claude-haiku-4-5-20251001"
MAX_DIFF_CHARS = 6000
MAX_LOG_CHARS = 3000
CODEX_ROOT = ".codex"

MAX_TOKENS_FILE = 1024
MAX_TOKENS_SESSION = 1500

# Extensions that are always binary — skip without reading content
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".wasm",
    ".mp3", ".mp4", ".wav", ".ogg", ".mov", ".avi",
    ".ttf", ".otf", ".woff", ".woff2",
    ".pyc", ".pyo", ".class",
    ".lock",  # package lock files are text but useless to explain
}

# ── Repo helpers ──────────────────────────────────────────────────────────────

def git(*args, cwd: str) -> str:
    """
    Run a git command in the given directory. Returns stdout as a string.
    Uses bytes-level decode with errors="replace" so git diff output containing
    non-UTF-8 sequences (binary patches, Windows cp1252 filenames, etc.) never
    crashes the script. Return code is intentionally ignored — callers treat
    empty output as "nothing to report" (e.g. HEAD~1 on a single-commit repo).
    """
    r = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        timeout=60,
        cwd=cwd,
    )
    return (r.stdout or b"").decode("utf-8", errors="replace").strip()


def get_src_root(repo_path: str) -> str:
    config_path = os.path.join(repo_path, CODEX_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("src_root", "src")
    except (FileNotFoundError, json.JSONDecodeError):
        return "src"


def is_binary(file_path: str) -> bool:
    """
    Return True if the file should be skipped.
    Checks extension first (cheap), then scans the first 8 KB for null bytes
    (the standard heuristic git itself uses to detect binary content).
    """
    if Path(file_path).suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            return b"\x00" in f.read(8192)
    except Exception:
        return False


def get_source_files(repo_path: str, src_root: str) -> list:
    """
    Return all text files that git tracks inside src_root, relative to repo_path.
    Binary files are filtered out here so callers never have to handle them.
    """
    output = git("ls-files", src_root, cwd=repo_path)
    if not output:
        return []
    all_files = [p for p in output.splitlines() if p.strip()]
    text_files = []
    for rel_path in all_files:
        full_path = os.path.join(repo_path, rel_path)
        if not is_binary(full_path):
            text_files.append(rel_path)
    return text_files


def get_commits(repo_path: str) -> list:
    """
    Return all commits oldest-first as dicts with hash, date (YYYY-MM-DD),
    author, and subject.
    """
    log = git(
        "log", "--reverse",
        "--format=%H|%ad|%an|%s",
        "--date=short",
        cwd=repo_path,
    )
    commits = []
    for line in log.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0],
                "date": parts[1],
                "author": parts[2],
                "subject": parts[3],
            })
    return commits


# ── Anthropic API ─────────────────────────────────────────────────────────────

def call_api(prompt: str, max_tokens: int) -> str:
    """
    Call the Anthropic API and return the response text.
    Retries up to 3 times on 429 (rate limit) with exponential backoff.
    Other HTTP errors and network failures are returned as error strings
    so the caller can write them to the output file and continue.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return "[Error: ANTHROPIC_API_KEY not set in environment]"

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    backoff = 5
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["content"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                print(f" [rate limited, retrying in {backoff}s]", end="", flush=True)
                time.sleep(backoff)
                backoff *= 2
                continue
            body = e.read().decode("utf-8", errors="replace")
            return f"[API error {e.code}: {body[:300]}]"
        except Exception as e:
            return f"[Request failed: {e}]"

    return "[API error: max retries exceeded on 429]"


# ── File explanations ─────────────────────────────────────────────────────────

def explain_file(repo_path: str, rel_path: str) -> str:
    """
    Generate a plain-language explanation for a source file using its full
    git history: the commit that introduced it, all subsequent commits that
    touched it, and the current content.

    Note: git("diff", "HEAD~1", "HEAD", ...) returns empty string on a
    single-commit repo because HEAD~1 does not exist. The git() helper ignores
    the non-zero exit code, and the prompt handles the empty case explicitly.
    """
    intro_diff = git("log", "--follow", "--diff-filter=A", "-p", "--", rel_path, cwd=repo_path)
    latest_diff = git("diff", "HEAD~1", "HEAD", "--", rel_path, cwd=repo_path)
    file_log = git(
        "log", "--follow", "--format=%ad %s", "--date=short", "--", rel_path,
        cwd=repo_path,
    )
    current_content = ""
    full_path = os.path.join(repo_path, rel_path)
    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                current_content = f.read()
        except Exception:
            pass

    prompt = f"""You are the Codex explanation engine. Generate a plain-language technical explanation
of the source file below for a developer who wants to understand the system, not just the syntax.

File path: {rel_path}

Commit history for this file (newest first):
<log>
{file_log[:MAX_LOG_CHARS]}
</log>

Introductory diff (commit that first added this file):
<intro_diff>
{intro_diff[:MAX_DIFF_CHARS]}
</intro_diff>

Most recent diff:
<latest_diff>
{latest_diff[:MAX_DIFF_CHARS] if latest_diff else "[No recent diff — file unchanged since introduction]"}
</latest_diff>

Current file content:
<content>
{current_content[:MAX_DIFF_CHARS]}
</content>

Write the explanation using this exact structure:

## {rel_path}

### What This File Does
One paragraph. System-level description. What role does this file play in the running system?

### Why It Exists
What operational reality or constraint forced this file into being? What problem does it solve?

### What It Protects Against
What failure mode, edge case, or risk does this code defend against? If none, say so.

### Invariants
What conditions must always be true for this file to work correctly? List them.

### Key Patterns
Name and briefly explain any notable design patterns or conventions this file uses.

### Change Log
One line per commit that touched this file: `- YYYY-MM-DD: <one sentence>`
List newest first.

Write in plain, direct prose. No padding. Be specific to this actual file."""

    return call_api(prompt, MAX_TOKENS_FILE)


# ── Session summaries ─────────────────────────────────────────────────────────

def summarise_session(repo_path: str, date: str, commits: list) -> str:
    """
    Generate a session summary for all commits on a given calendar day.
    """
    hashes = [c["hash"] for c in commits]

    stat_lines = []
    diff_sample = ""
    for h in hashes:
        stat = git("show", "--stat", "--format=", h, cwd=repo_path)
        stat_lines.append(stat)
        if len(diff_sample) < MAX_DIFF_CHARS:
            d = git("show", "--format=", h, cwd=repo_path)
            diff_sample += f"\n--- commit {h[:7]} ---\n{d}"

    combined_stats = "\n".join(stat_lines)

    prompt = f"""You are the Codex session summariser. Summarise a coding session based on its git commits.

Date: {date}
Commits ({len(commits)} total):
{chr(10).join(f"  - {c['subject']}" for c in commits)}

File change statistics:
<stats>
{combined_stats[:MAX_LOG_CHARS]}
</stats>

Diff sample (may be truncated):
<diffs>
{diff_sample[:MAX_DIFF_CHARS]}
</diffs>

Write the summary using this exact structure:

## Session {date}

### What Was Built
2-4 bullet points covering the main things accomplished this session.

### Key Decisions
Any significant architectural or design decisions made. If the diffs show patterns being established or changed, note them.

### Files Changed
List the files modified with a one-line description of what changed in each.

### Lessons and Gotchas
Any non-obvious constraints, fixes, or discoveries revealed by this session's work.

Write in plain, direct prose. No padding."""

    return call_api(prompt, MAX_TOKENS_SESSION)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    force = "--force" in args
    positional = [a for a in args if not a.startswith("--")]

    repo_path = os.path.abspath(positional[0] if positional else os.getcwd())

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print(f"[FAIL] Not a git repository: {repo_path}")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("[FAIL] ANTHROPIC_API_KEY is not set in environment.")
        sys.exit(1)

    src_root = get_src_root(repo_path)
    print(f"Repo:     {repo_path}")
    print(f"src_root: {src_root}")
    print(f"force:    {force}")
    print()

    # ── Phase 1: file explanations ─────────────────────────────────────────────
    files = get_source_files(repo_path, src_root)
    skipped_binary = len(git("ls-files", src_root, cwd=repo_path).splitlines()) - len(files)

    if not files:
        print(f"[WARN] No tracked text files found under {src_root}/")
    else:
        label = f"Phase 1 — file explanations ({len(files)} files"
        if skipped_binary:
            label += f", {skipped_binary} binary skipped"
        print(label + ")")

        done = skipped = 0
        for i, rel_path in enumerate(files, 1):
            out_path = (Path(repo_path) / CODEX_ROOT / rel_path).with_suffix(".md")
            prefix = f"  [{i}/{len(files)}] {rel_path}"

            if out_path.exists() and not force:
                print(f"{prefix} — skip (exists)")
                skipped += 1
                continue

            print(f"{prefix}", end="", flush=True)
            explanation = explain_file(repo_path, rel_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(explanation, encoding="utf-8")
            print(" ✓")
            done += 1

        print(f"  {done} generated, {skipped} skipped (use --force to regenerate)")

    print()

    # ── Phase 2: session summaries ─────────────────────────────────────────────
    commits = get_commits(repo_path)
    if not commits:
        print("[WARN] No commits found.")
        return

    by_date = defaultdict(list)
    for c in commits:
        by_date[c["date"]].append(c)

    sessions_dir = Path(repo_path) / CODEX_ROOT / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    print(f"Phase 2 — session summaries ({len(by_date)} days)")
    done = skipped = 0
    for i, (date, day_commits) in enumerate(sorted(by_date.items()), 1):
        out_path = sessions_dir / f"{date}.md"
        prefix = f"  [{i}/{len(by_date)}] {date} ({len(day_commits)} commits)"

        if out_path.exists() and not force:
            print(f"{prefix} — skip (exists)")
            skipped += 1
            continue

        print(prefix, end="", flush=True)
        summary = summarise_session(repo_path, date, day_commits)
        out_path.write_text(summary, encoding="utf-8")
        print(" ✓")
        done += 1

    print(f"  {done} generated, {skipped} skipped (use --force to regenerate)")
    print()
    print("Done.")
    print(f"  File explanations: {Path(repo_path) / CODEX_ROOT / src_root}")
    print(f"  Session summaries: {sessions_dir}")


if __name__ == "__main__":
    main()
