## INSTALL.md

### What This File Does

This is the setup manual for Codex, a system that automatically generates explanations and summaries for code written in Claude Code sessions. It walks a developer through four concrete steps: copying hook scripts and configuration files into their local Claude environment, configuring an API key, initializing a project with Git and required directories, and verifying the system works by triggering a hook and checking its output.

### Why It Exists

Codex requires multiple moving pieces to function—two Python hook scripts, a global teaching document, and a settings configuration file—all of which must be placed in specific locations with specific permissions. Without this guide, developers would have no way to know where to put files, what order to do things in, or how to verify success. The document also establishes the contract between the user's machine (where hooks run) and each project (which feeds data to the hooks).

### What It Protects Against

The guide defends against several failure modes: developers overwriting their existing `settings.json` file wholesale instead of merging it; API keys not being available to hook processes at execution time; projects without Git initialization or `src/` directories triggering silent hook failures; and developers assuming the system is broken when it simply hasn't been triggered yet. The troubleshooting section specifically addresses the most common failure states (missing `.codex/` directories, empty explanations, no session summaries) and provides debugging steps for each.

### Invariants

- Hook scripts must be in `~/.claude/hooks/` and executable
- `global_CLAUDE.md` must be at `~/.claude/CLAUDE.md`
- `settings.json` must be at `~/.claude/settings.json` and properly merged if already present
- Every project using Codex must have Git initialized
- Every project must have a `src/` directory—hooks only fire for writes under `src/`
- Every project must have a `CLAUDE.md` file with specific sections (What This Project Is, Current Build State, Architecture, Known Fragile Areas)
- `ANTHROPIC_API_KEY` environment variable must be exported in shells where Claude Code runs
- The `.codex/` output directory is created on first hook execution, not manually

### Key Patterns

**Explicit configuration over magic**: The guide walks through every file placement and environment variable explicitly rather than assuming automatic discovery. **Local-then-project hierarchy**: User-level hooks and global teaching rules apply to all projects; project-level `CLAUDE.md` customizes behavior per project. **Verification-driven setup**: Rather than assuming files are in place, step 4 gives concrete commands to test that the system is actually working. **Troubleshooting by symptom**: The troubleshooting section groups failure modes by observable outcome (missing directory, empty file, no summary) rather than by technical cause, making it more useful to someone debugging blindly.

### Change Log

- 2026-05-12: Initial release with full installation and verification procedures, git strategy guidance, and troubleshooting for four common failure modes