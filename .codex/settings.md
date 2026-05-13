## settings.json

### What This File Does

This file configures the Claude editor's hook system—a mechanism that automatically runs Python scripts at specific points in the editing lifecycle. When you perform file operations (Write, Edit, MultiEdit), this configuration ensures that setup code runs *before* the operation (PreToolUse), cleanup or analysis code runs *after* (PostToolUse), and final teardown runs when the session ends (Stop).

### Why It Exists

The Codex system needs a way to inject context and perform housekeeping around file edits without modifying the core editor logic. Rather than hard-coding behavior, this declarative hook configuration lets the system remain flexible: scripts can be updated or replaced without rebuilding the editor, and the wiring between lifecycle events and handler scripts lives in one visible place.

### What It Protects Against

This file doesn't defend against runtime failures in the hook scripts themselves—if `codex_pre_tool_use.py` crashes, the edit still proceeds. However, it does protect against *loss of context*: by running PreToolUse hooks before edits, the system ensures any prior .codex state is loaded and available before modifications are made, preventing edits that operate blindly on stale context.

### Invariants

- All three hook types (PreToolUse, PostToolUse, Stop) must exist; removing any breaks the lifecycle.
- The matcher pattern `"Write|Edit|MultiEdit"` must match actual Claude tool names or those hooks never fire.
- The command paths must be absolute (`~/.claude/hooks/`) so they resolve correctly regardless of working directory.
- Each hook entry must have `"type": "command"` and a valid `"command"` string, or the editor will fail to parse the configuration.

### Key Patterns

**Event-driven hooks with matchers**: The configuration separates *when* code runs (PreToolUse, PostToolUse, Stop) from *which* code runs (the command), and filters execution by tool name (Write|Edit|MultiEdit). This decouples lifecycle management from script identity.

**Declarative configuration**: Rather than imperative Python setup, this JSON declares the dependency graph between editor events and handlers, making the system auditable and modifiable without code changes.

### Change Log

- 2026-05-12: feat: add PreToolUse hook to inject prior .codex context before edits
- 2026-05-12: Initial release: Codex hook system with installer