## install.py

### What This File Does
This is an automated deployment script that bootstraps the Codex hook system into a Claude Code installation. It copies hook scripts into `~/.claude/hooks/`, merges hook configuration into `~/.claude/settings.json` without overwriting existing data, installs teaching rules into `~/.claude/CLAUDE.md`, and detects or prompts for an Anthropic API key. The script is platform-aware and runs successfully from any working directory on Windows, Linux, and macOS.

### Why It Exists
Claude Code's hook system requires files to be placed in specific locations and configuration to be wired into settings.json in a idempotent way. A developer installing Codex needs a single entry point that handles platform differences (Python binary names, path separators, Windows registry checks), respects existing user configuration, and clearly reports what was done. Manual file copying and JSON editing is error-prone and non-repeatable.

### What It Protects Against
- **Character encoding crashes on Windows**: Forces UTF-8 output before any print() call so Unicode checklist characters (✓ ✗ !) don't fail on cp1252 consoles.
- **Path expansion failures on Windows**: Converts `~/.claude/hooks/` to absolute paths because Windows cmd.exe doesn't expand `~` in hook command strings.
- **Duplicate hook registration**: The merge strategy compares existing command strings to avoid adding the same hook twice when the installer is re-run.
- **Configuration loss**: Backs up the previous CLAUDE.md as CLAUDE.md.bak before overwriting, and only merges new hooks into settings.json rather than replacing it.
- **Missing Python interpreter**: Tests both `python3` and `python` to find a working binary before patching settings.json with hardcoded command strings.
- **Incomplete installations**: Validates all source files exist before proceeding, preventing silent partial deployments.

### Invariants
- `HERE` always points to the directory containing install.py, allowing the script to locate its sibling source files regardless of the current working directory.
- `~/.claude/` is the canonical Codex configuration root on all platforms (Claude Code uses this path even on Windows).
- settings.json hooks configuration is always a dictionary with event type keys (PostToolUse, PreToolUse, Stop) mapping to lists of entries, each with a "hooks" list containing objects with "command" fields.
- Hook scripts are only marked executable on Unix-like systems; Windows uses the python binary in the command string instead.
- Any existing hooks configuration in settings.json is preserved; new hooks are only added if their command strings don't already exist.

### Key Patterns
- **Platform branching**: Conditional logic for Windows vs. Unix (executable bits, path separators, registry checks) rather than abstracting into a shared layer.
- **Idempotent merge**: Settings and hooks are merged by inspecting command string equality, making repeated runs safe and producing the same result.
- **String templating**: JSON is dumped to a raw string, searched-and-replaced for python_cmd and hook paths, then re-parsed—simpler than walking the tree structure.
- **In-place update with single backup**: CLAUDE.md backups are overwritten each run, keeping exactly one previous version available without accumulation.
- **Fail-fast validation**: Source files are checked before any installation step begins, catching configuration errors early.

### Change Log
- 2026-05-13: Self-install and retroactive backfill of .codex/ directory structure.
- 2026-05-12: Add PreToolUse hook injection before edits and explicit UTF-8 encoding on all settings.json file opens.
- 2026-05-12: Document retro.py in README and surface it in installer output; broaden API key detection and add platform-aware persistence.
- 2026-05-12: Prompt for API key during install and persist it system-wide; fix Windows path expansion and add README.
- 2026-05-12: Initial release with PostToolUse and Stop hooks, global CLAUDE.md teaching rules, and settings.json hook wiring.