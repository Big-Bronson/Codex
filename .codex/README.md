## README.md

### What This File Does

This is the user-facing entry point and installation guide for Codex, a system that automatically generates markdown explanations of source code files and session summaries by hooking into Claude Code's execution pipeline. It documents what the system does, how to install it, how to configure it per-project, and what files comprise the implementation.

### Why It Exists

Claude Code needs a discoverable, human-readable explanation of what Codex is and how to use it. Without this, users who clone the repository have no clear starting point. The README also serves as a contract between the system's behavior (what the hooks do) and user expectations (what output to expect where). It was added alongside the initial Windows path fix because the installer couldn't succeed silently without documentation guiding users through setup and validation.

### What It Protects Against

It protects against installation confusion by explicitly listing prerequisites (`ANTHROPIC_API_KEY` in environment, Python 3.7+, Claude Code installed) so users know what's missing before they run `install.py`. It protects against silent hook failures by documenting the exact output structure users should see in `.codex/`. It protects against lost work by recommending that `.codex/` be committed to git, ensuring explanations and session logs travel with the code. It addresses the retroactive backfill problem by documenting `retro.py` for projects with existing git history.

### Invariants

- The `src/` directory (or configured `src_root`) must exist before hooks fire; hooks only process files written beneath this path.
- Git must be initialized in the project; hooks depend on `git diff` output.
- The `.codex/` directory structure must be creatable and writable by the hook processes.
- `ANTHROPIC_API_KEY` must be in the environment when hooks execute; they fail silently otherwise.
- `install.py` must be run before hooks can function; it wires them into `~/.claude/settings.json`.

### Key Patterns

**Progressive disclosure**: Installation is covered first (the immediate need), then project setup, then output expectations, then advanced topics like per-project configuration and retroactive backfill. Users get what they need to start, then deeper details.

**Concrete examples**: Every concept is paired with actual file paths or code snippets (`.codex/src/service.md`, the `config.json` JSON structure, the `retro.py` command invocations) so users can ground abstract descriptions in reality.

**Idempotency emphasis**: The README explicitly states "Safe to re-run — it will not duplicate hook entries" and "Re-runs are safe and cheap by default" to lower the perceived cost of experimentation and give users confidence they won't break their setup.

**Specification by structure**: The output structure is shown as a directory tree with inline comments, which is more scannable and concrete than prose description.

### Change Log

- 2026-05-12: Document `retro.py` in README and surface it in installer output
- 2026-05-12: Make source root configurable via `.codex/config.json`
- 2026-05-12: Fix Windows path expansion and add README