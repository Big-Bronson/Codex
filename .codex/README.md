## README.md

### What This File Does
This is the user-facing entry point and instruction manual for Codex, a system that automatically generates markdown documentation for code files and work sessions by hooking into Claude Code's lifecycle. It explains what Codex does, how to install it, how to configure projects, and documents the purpose of each component file in the system.

### Why It Exists
Users installing Codex need to understand what they're getting, what prerequisites are required, how to run the installer, and how to prepare their projects. Without this document, the system is opaque and unusable. The README also serves as the "agent-discoverable entry point"—when Claude Code introspects this repository, it reads README.md first to understand the project's purpose and structure.

### What It Protects Against
It protects against silent installation failures by documenting the installer's behavior (what it modifies, where, and how to verify success). It prevents projects from being misconfigured by specifying the exact three prerequisites needed (`src/` directory, git initialization, `CLAUDE.md`). It guards against data loss by clarifying that `.codex/` should be committed to git and that re-running the installer is safe. It also documents the per-project configuration escape hatch (`.codex/config.json`) so users don't get stuck with hardcoded `src/` if their project structure differs.

### Invariants
- The installer must be run before Codex hooks activate
- Projects must have `src/` directory (or a configured alternative via `.codex/config.json`) for hooks to fire
- Projects must be git-initialized for hooks to extract diffs
- `ANTHROPIC_API_KEY` must be in the environment at hook execution time
- The `.codex/` directory structure mirrors the project's source structure under the configured `src_root`
- All generated documentation should be committed alongside source code

### Key Patterns
**Three-layer documentation**: immediate explanation (what it does), procedural guidance (how to install and configure), and reference table (what each file is for). The document moves from high-level concept → setup → verification → troubleshooting/edge cases, following a "journey" pattern that meets users where they are. It also uses concrete file trees and JSON examples rather than abstract descriptions, grounding the explanation in runnable commands.

### Change Log
- 2026-05-12: Document retro.py in README and surface it in installer output
- 2026-05-12: Make source root configurable via .codex/config.json  
- 2026-05-12: Fix Windows path expansion and add README