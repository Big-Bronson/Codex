## codex_pre_tool_use.py

### What This File Does
This is a pre-execution hook that runs before Claude Code applies any Write/Edit/MultiEdit operation to files in your project's source root. It reads a JSON event from stdin, looks up whether a `.codex` explanation file exists for the target file, and if one does, prints that explanation to stdout so Claude Code can inject it into Claude's context before the edit happens. It always exits cleanly with code 0, never blocking execution.

### Why It Exists
When Claude edits a file it has already documented in `.codex`, Claude should see that prior understanding before making changes. This prevents Claude from re-learning the file from scratch or contradicting its own previous analysis. The hook enables context injection without requiring API calls, external services, or blocking behavior — it's a lightweight bridge between stored explanations and Claude's active editing context.

### What It Protects Against
This code defends against several silent failure modes: malformed JSON input (catches and exits cleanly), missing or unparseable config files (falls back to "src" root), file paths outside the configured source root (skips them silently), and read errors on the explanation file (catches all exceptions and exits). It also handles the case where no explanation exists yet (first write to a file) by exiting silently rather than printing a spurious message or failing. The dual path-prefix check (`startswith(src_root + os.sep)` and `startswith(src_root + "/")`) prevents matching false positives like "src_alt" when looking for "src".

### Invariants
- The `.codex` directory and `config.json` must be readable or absent (graceful degradation to defaults).
- The explanation file path must map back to a relative path under `src_root` or it is skipped.
- The hook must always exit 0; no scenario should cause a non-zero exit.
- The explanation file path transformation must exactly mirror `codex_post_tool_use.py` so pre- and post-hooks operate on the same files.
- File paths in the event JSON come from Claude Code and are either `file_path` or `path` keys in `tool_input`.

### Key Patterns
**Fail-safe exit pattern**: Every error condition (`except`, missing file, invalid path) calls `sys.exit(0)` rather than raising or exiting nonzero. The hook prioritizes never blocking Claude over completeness.

**Config mirroring**: The `get_src_root()` and `get_explanation_path()` functions use identical logic to `codex_post_tool_use.py` so both hooks share a single source of truth for directory mapping and naming conventions.

**Structured hint block**: The output wraps the explanation in recognizable markers (`[Codex] Prior understanding...` and `[End Codex context]`) so Claude Code can reliably detect and extract the injected context.

### Change Log
- 2026-05-12: Initial commit — added PreToolUse hook to inject prior `.codex` context before file edits, with fallback to "src" root and silent exit on first writes or missing explanations.