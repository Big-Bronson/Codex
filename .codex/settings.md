## settings.json

### What This File Does
This file wires Claude's hook system to execute Python scripts at specific points in the code-editing lifecycle. It tells Claude which commands to run before edits start (PreToolUse), after edits complete (PostToolUse), and when the conversation ends (Stop). Think of it as a configuration manifest that connects Claude's internal events to external automation.

### Why It Exists
Claude's native hook system needs to know *which* scripts to run and *when* to run them. Without this configuration, the hook scripts would exist but never execute. This file bridges the gap between Claude's editor and the Codex system's Python utilities, enabling automated workflows like context injection and cleanup.

### What It Protects Against
This design protects against **silent failures** where hook scripts exist but never run due to misconfiguration. By centralizing hook registration in one file, mismatches between event types and handlers become visible. It also prevents scripts from running at the wrong lifecycle moment—for example, injecting context after an edit completes (when it's useless) instead of before it starts.

### Invariants
- The `matcher` patterns (Write|Edit|MultiEdit) must correspond to actual Claude tool names, or matching tools will ignore these hooks.
- The command paths must point to executable Python scripts that exist and are readable at `~/.claude/hooks/`.
- Hook execution order within a single lifecycle event (PreToolUse, PostToolUse, or Stop) is sequential; if one fails, later hooks still execute.
- The JSON structure must be valid; malformed JSON will prevent all hooks from loading.

### Key Patterns
**Event-driven hook registration**: The file uses a matcher pattern to filter which tools trigger which hooks, allowing targeted automation without hardcoding tool logic. **Centralized configuration**: All hook definitions live in one place rather than scattered across multiple files, reducing discovery friction and making system-wide changes manageable.

### Change Log
- 2026-05-12: feat: add PreToolUse hook to inject prior .codex context before edits
- 2026-05-12: Initial release: Codex hook system with installer