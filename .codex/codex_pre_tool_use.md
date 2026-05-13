## codex_pre_tool_use.py

### What This File Does
This is a hook that runs *before* Claude Code executes a Write, Edit, or MultiEdit operation on any file in your project's source directory. If a `.codex` explanation file already exists for that target file, this hook reads it and prints it to stdout—which Claude Code then injects into Claude's context window so Claude sees the prior understanding of the code before making changes. If no explanation exists yet (first write to that file), the hook exits silently.

### Why It Exists
Claude's context resets between tool calls. When Claude edits a file it previously generated documentation for, that documentation isn't automatically available unless explicitly injected. This hook closes that loop: your `.codex` explanations become living context that inform every subsequent edit, preventing Claude from losing architectural understanding or reintroducing issues it already documented.

### What It Protects Against
- **Context loss**: Claude editing a file without remembering what it documented about that file's purpose or constraints
- **Over-talking**: The hook is designed to fail silent (always exit 0, never block)—it cannot hang Claude or break the tool pipeline if the `.codex` directory is missing, corrupted, or unreadable
- **Path confusion**: Files outside `src_root` are ignored; the path mapping logic is kept identical to `codex_post_tool_use.py` so both hooks agree on what's in scope

### Invariants
- `get_src_root()` must return a consistent value throughout a session (reads from `.codex/config.json`)
- The explanation file path mapping (`<src_root>/auth/service.ps1` → `.codex/<src_root>/auth/service.md`) must match exactly the reverse mapping in `codex_post_tool_use.py`
- The hook must always exit with code 0, even on error—it cannot block Claude
- Only files under `src_root` (and within it) trigger context injection; files elsewhere are silently skipped

### Key Patterns
- **Fail-safe design**: Every error path (malformed JSON, missing config, unreadable files, path outside src_root) exits 0 without output—the hook never crashes or halts the tool
- **Symmetric logic**: `get_src_root()` and `get_explanation_path()` are documented as exact mirrors of the post-hook equivalents, maintaining consistency between the before and after phases
- **Structured output**: Printed context is wrapped in `[Codex]` and `[End Codex context]` markers so Claude Code can reliably parse and inject it

### Change Log
- 2026-05-12: Added PreToolUse hook to inject prior .codex context before file edits