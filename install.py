#!/usr/bin/env python3
"""
Codex installer.
Can be run from any working directory — locates package files relative to itself.
"""

import json
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

HERE = Path(__file__).parent  # always the directory the script lives in

HOOK_SCRIPTS = [
    "codex_post_tool_use.py",
    "codex_stop.py",
]
SETTINGS_SOURCE = "settings.json"
CLAUDE_MD_SOURCE = "CLAUDE.md"

# ── Helpers ───────────────────────────────────────────────────────────────────

def find_python() -> str:
    """
    Return the python executable name that actually works on this machine.
    Prefers python3, falls back to python. Used to patch the hook command
    strings in settings.json so they invoke the right binary.
    """
    for candidate in ("python3", "python"):
        try:
            result = subprocess.run(
                [candidate, "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "python3"


def get_claude_dir() -> Path:
    """
    ~/.claude on all platforms. Claude Code uses this path on Windows too.
    Path.home() resolves to C:\\Users\\<name> on Windows, /home/<name> on Linux.
    """
    return Path.home() / ".claude"


def check_source_files() -> list:
    missing = []
    for f in HOOK_SCRIPTS + [SETTINGS_SOURCE, CLAUDE_MD_SOURCE]:
        if not (HERE / f).exists():
            missing.append(f)
    return missing


# ── Installation steps ────────────────────────────────────────────────────────

def install_hooks(claude_dir: Path) -> str:
    """
    Copy hook scripts into ~/.claude/hooks/.
    On Unix, mark them executable. On Windows the executable bit is irrelevant
    — the command string in settings.json invokes python directly anyway.
    """
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    for script in HOOK_SCRIPTS:
        dst = hooks_dir / script
        shutil.copy2(HERE / script, dst)
        if platform.system() != "Windows":
            dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return f"{len(HOOK_SCRIPTS)} scripts → {hooks_dir}"


def merge_settings(claude_dir: Path, python_cmd: str) -> str:
    """
    Merge Codex hooks into ~/.claude/settings.json without clobbering
    anything already there.

    Strategy: for each hook event type (PostToolUse, Stop), compare command
    strings. Only append a new entry if none of its commands already appear
    in the existing list. This makes the installer safe to re-run.
    """
    settings_path = claude_dir / "settings.json"

    with open(HERE / SETTINGS_SOURCE, "r") as f:
        incoming = json.load(f)

    # Patch python command and expand ~ to the real hooks path.
    # ~ does not expand in Windows cmd, which is what Claude Code uses to run
    # hook commands on Windows. Write the absolute path so it works everywhere.
    hooks_dir = claude_dir / "hooks"
    raw = json.dumps(incoming)
    raw = raw.replace("python3 ", f"{python_cmd} ")
    raw = raw.replace("~/.claude/hooks/", str(hooks_dir).replace("\\", "/") + "/")
    incoming = json.loads(raw)

    if settings_path.exists():
        with open(settings_path, "r") as f:
            existing = json.load(f)
        verb = "merged into existing"
    else:
        existing = {}
        verb = "created new"

    if "hooks" not in existing:
        existing["hooks"] = {}

    for event_type, incoming_entries in incoming.get("hooks", {}).items():
        if event_type not in existing["hooks"]:
            existing["hooks"][event_type] = incoming_entries
            continue

        # Collect every command string already registered for this event
        registered_commands: set = set()
        for entry in existing["hooks"][event_type]:
            for hook in entry.get("hooks", []):
                registered_commands.add(hook.get("command", ""))

        # Only add entries whose commands are not already present
        for entry in incoming_entries:
            entry_commands = {h.get("command", "") for h in entry.get("hooks", [])}
            if not entry_commands & registered_commands:
                existing["hooks"][event_type].append(entry)

    with open(settings_path, "w") as f:
        json.dump(existing, f, indent=2)

    return f"{verb} settings.json"


def install_claude_md(claude_dir: Path) -> str:
    """
    Write CLAUDE.md to ~/.claude/CLAUDE.md.
    If one already exists, back it up to CLAUDE.md.bak before overwriting.
    The backup is always the single previous version — re-running the
    installer replaces the backup, not accumulates them.
    """
    dst = claude_dir / "CLAUDE.md"

    if dst.exists():
        shutil.copy2(dst, claude_dir / "CLAUDE.md.bak")
        shutil.copy2(HERE / CLAUDE_MD_SOURCE, dst)
        return "backed up existing → CLAUDE.md.bak, wrote new"

    shutil.copy2(HERE / CLAUDE_MD_SOURCE, dst)
    return "created"


def check_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Codex Installer")
    print("=" * 44)

    # Guard: must be run from the package directory
    missing = check_source_files()
    if missing:
        print(f"\n[FAIL] Missing source files: {', '.join(missing)}")
        print("Run this script from the directory containing the Codex package files.")
        sys.exit(1)

    python_cmd = find_python()
    claude_dir = get_claude_dir()

    print(f"  Platform:   {platform.system()}")
    print(f"  Python:     {python_cmd}")
    print(f"  Claude dir: {claude_dir}")
    print()

    steps = [
        ("Hook scripts",      lambda: install_hooks(claude_dir)),
        ("settings.json",     lambda: merge_settings(claude_dir, python_cmd)),
        ("CLAUDE.md",         lambda: install_claude_md(claude_dir)),
    ]

    results = {}
    failed = False

    for label, fn in steps:
        try:
            desc = fn()
            results[label] = ("OK", desc)
        except Exception as e:
            results[label] = ("FAIL", str(e))
            failed = True

    # API key is a warning, not a hard failure
    if check_api_key():
        results["ANTHROPIC_API_KEY"] = ("OK", "found in environment")
    else:
        results["ANTHROPIC_API_KEY"] = ("WARN", "not set — hooks will error at runtime until this is exported")

    # Checklist output
    icons = {"OK": "✓", "WARN": "!", "FAIL": "✗"}
    print("Checklist:")
    for label, (status, desc) in results.items():
        print(f"  [{icons[status]}] {label}: {desc}")

    print()
    if failed:
        print("Installation incomplete. Fix the errors above and re-run.")
        sys.exit(1)
    else:
        print("Installation complete.")
        print("Open a project with a src/ directory and ask Claude to write a file there to verify.")


if __name__ == "__main__":
    main()
