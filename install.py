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

# Force UTF-8 stdout/stderr on Windows so Unicode checklist characters (✓ ✗ !)
# don't crash on cp1252 consoles. Must happen before any print() call.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Constants ─────────────────────────────────────────────────────────────────

HERE = Path(__file__).parent  # always the directory the script lives in

HOOK_SCRIPTS = [
    "codex_pre_tool_use.py",
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

    with open(HERE / SETTINGS_SOURCE, "r", encoding="utf-8") as f:
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
        with open(settings_path, "r", encoding="utf-8") as f:
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

    with open(settings_path, "w", encoding="utf-8") as f:
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


def find_api_key() -> tuple:
    """
    Search for an existing API key across all common storage locations.
    Returns (key, location_description) or (None, None) if not found anywhere.

    Checks in order:
      1. Current process environment — key is already live
      2. Windows registry HKCU\\Environment — set by a previous setx run but
         not yet visible because the desktop app predates it
      3. Shell profile files — key is persisted but desktop app never sourced them
      4. .env file in home directory — manual setup some users prefer
    """
    import re

    # 1. Live environment
    val = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if val:
        return val, "current environment"

    # 2. Windows registry
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                val, _ = winreg.QueryValueEx(k, "ANTHROPIC_API_KEY")
                if val:
                    return val, "Windows user environment registry (needs restart to activate)"
        except Exception:
            pass

    # 3. Shell profile files
    profile_candidates = [
        Path.home() / ".zshrc",
        Path.home() / ".zprofile",
        Path.home() / ".bash_profile",
        Path.home() / ".bashrc",
        Path.home() / ".profile",
        Path.home() / ".config" / "fish" / "config.fish",
    ]
    pattern = re.compile(r'ANTHROPIC_API_KEY[=\s]+["\']?(sk-ant-[^\s"\']+)')
    for path in profile_candidates:
        if path.exists():
            try:
                match = pattern.search(path.read_text(encoding="utf-8", errors="replace"))
                if match:
                    return match.group(1), str(path)
            except Exception:
                pass

    # 4. ~/.env
    env_file = Path.home() / ".env"
    if env_file.exists():
        try:
            match = pattern.search(env_file.read_text(encoding="utf-8", errors="replace"))
            if match:
                return match.group(1), str(env_file)
        except Exception:
            pass

    return None, None


def persist_api_key(key: str) -> str:
    """
    Write the API key to the appropriate persistent location for this platform
    so it survives reboots and is visible to desktop apps.

    Windows:
      setx writes to HKCU\\Environment. Visible to all future processes;
      requires restart for already-running apps.

    macOS:
      Writes to ~/.zshrc (default shell since Catalina) or ~/.bash_profile
      (bash login shell convention). Also runs launchctl setenv so the current
      desktop session picks it up immediately without a restart.

    Linux:
      Writes to the profile file matching the active shell: fish config uses
      'set -gx' syntax; zsh/bash use export. Checks for an existing entry
      first so re-running the installer does not append duplicates.
    """
    system = platform.system()

    if system == "Windows":
        result = subprocess.run(
            ["setx", "ANTHROPIC_API_KEY", key],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return "written to Windows user environment via setx (restart Claude Code to apply)"

    # Determine target profile file
    shell = os.environ.get("SHELL", "")
    if "fish" in shell:
        profile = Path.home() / ".config" / "fish" / "config.fish"
        export_line = f'\nset -gx ANTHROPIC_API_KEY "{key}"\n'
    elif system == "Darwin":
        # macOS login shells read .bash_profile not .bashrc; zsh is default
        profile = Path.home() / (".zshrc" if "zsh" in shell else ".bash_profile")
        export_line = f'\nexport ANTHROPIC_API_KEY="{key}"\n'
    else:
        profile = Path.home() / (".zshrc" if "zsh" in shell else ".bashrc")
        export_line = f'\nexport ANTHROPIC_API_KEY="{key}"\n'

    # Guard against duplicate entries
    existing = ""
    if profile.exists():
        existing = profile.read_text(encoding="utf-8", errors="replace")
    if "ANTHROPIC_API_KEY" not in existing:
        profile.parent.mkdir(parents=True, exist_ok=True)
        with open(profile, "a", encoding="utf-8") as f:
            f.write(export_line)

    notes = [f"written to {profile}"]

    # macOS: also activate immediately for the current desktop session
    if system == "Darwin":
        try:
            subprocess.run(
                ["launchctl", "setenv", "ANTHROPIC_API_KEY", key],
                capture_output=True, timeout=5
            )
            notes.append("activated in current desktop session via launchctl")
        except Exception:
            notes.append("launchctl activation failed — restart Claude Code to apply")

    return " | ".join(notes)


def prompt_api_key() -> tuple:
    """
    Interactively prompt for the API key. Returns (key, None) on success
    or (None, reason) if the user declines.
    """
    print()
    print("  ANTHROPIC_API_KEY is not set.")
    print("  The hooks call the Anthropic API (Haiku) to generate explanations.")
    print("  Get a key at: https://console.anthropic.com/settings/keys")
    print()
    answer = input("  Enter your API key now, or press Enter to skip: ").strip()

    if not answer:
        return None, "skipped — set ANTHROPIC_API_KEY manually before using the hooks"

    if not answer.startswith("sk-ant-"):
        print("  Warning: key doesn't match expected format (sk-ant-...) — saving anyway.")

    return answer, None


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
        ("Hook scripts",  lambda: install_hooks(claude_dir)),
        ("settings.json", lambda: merge_settings(claude_dir, python_cmd)),
        ("CLAUDE.md",     lambda: install_claude_md(claude_dir)),
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

    # API key — search all known locations before prompting
    key, location = find_api_key()
    if key:
        results["ANTHROPIC_API_KEY"] = ("OK", f"found in {location}")
    else:
        key, skip_reason = prompt_api_key()
        if key:
            try:
                desc = persist_api_key(key)
                results["ANTHROPIC_API_KEY"] = ("OK", desc)
            except Exception as e:
                results["ANTHROPIC_API_KEY"] = ("WARN", f"could not persist automatically: {e} — set it manually")
        else:
            results["ANTHROPIC_API_KEY"] = ("WARN", skip_reason)

    # Checklist output
    icons = {"OK": "✓", "WARN": "!", "FAIL": "✗"}
    print()
    print("Checklist:")
    for label, (status, desc) in results.items():
        print(f"  [{icons[status]}] {label}: {desc}")

    print()
    if failed:
        print("Installation incomplete. Fix the errors above and re-run.")
        sys.exit(1)
    else:
        print("Installation complete.")
        if platform.system() == "Windows":
            print("Restart the Claude Code app to apply the API key to its environment.")
        print("Then open a project with a src/ directory and ask Claude to write a file there to verify.")
        print()
        print("To backfill an existing project that pre-dates Codex:")
        print("  python retro.py [repo_path]          # generates explanations + session summaries from git history")
        print("  python retro.py --force [repo_path]  # regenerate even if .codex/ files already exist")


if __name__ == "__main__":
    main()
