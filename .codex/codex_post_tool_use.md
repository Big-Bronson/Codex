## codex_post_tool_use.py

### What This File Does

This is a Git hook that runs after every file write or edit in the project's source directory. It captures what changed, sends the diff to Claude via the Anthropic API, and gets back a plain-language explanation of the file's purpose, design decisions, and failure modes. That explanation is written to `.codex/src/` as a mirror of the source tree, and a one-line summary is appended to `codex.log` for audit and discovery.

### Why It Exists

As a codebase grows, developers lose context about *why* files exist and what invariants they protect. Git diffs show *what* changed but not *why*. This hook closes that gap by automatically documenting every edit in language a human can reason about. The explanations accumulate in a queryable log and a structured mirror, making it possible to understand system design without digging through commits or asking the original author.

### What It Protects Against

**Missing API key**: returns a safe error message rather than crashing. **File not under source root**: skips processing instead of breaking. **Git not available**: falls back to reading the file directly. **Malformed config**: defaults to "src" if `.codex/config.json` is missing or broken. **API failures**: logs HTTP error details rather than silently failing. **Encoding errors**: uses `errors="replace"` when reading source files to handle non-UTF-8 content gracefully.

### Invariants

- `CODEX_ROOT` (`.codex`) must be writable and must contain `config.json` (optional, defaults to `src_root: "src"`).
- Every explanation must have a Change Log section; prior entries must be preserved.
- The explanation path mirrors the source path exactly, only changing the root prefix and extension (`.md`).
- `call_claude()` must receive `ANTHROPIC_API_KEY` in the environment; without it, the hook degrades gracefully instead of blocking.
- `get_explanation_path()` returns `None` if the file is not under the configured source root; callers must handle this.

### Key Patterns

**Graceful degradation**: Every integration point (git, file I/O, API calls) wraps errors and returns partial data rather than failing hard. **Configuration layering**: hardcoded defaults (`src_root: "src"`) are overridable via `.codex/config.json`, allowing per-project customization. **Structural prompting**: the Claude prompt specifies exact markdown sections (What This File Does, Why It Exists, etc.) so explanations are predictable and queryable. **Truncation for cost**: diffs and existing explanations are capped at 4000 and 3000 characters respectively, keeping API calls cheap. **Path symmetry**: source files map to explanations by swapping the root prefix and changing the extension, making the mirror navigable.

### Change Log

- 2026-05-12: refactor: serve both documentation and pedagogy in Codex prompts
- 2026-05-12: refactor: shift Codex prompts from documentation to pedagogy
- 2026-05-12: Make source root configurable via .codex/config.json
- 2026-05-12: Initial release: Codex hook system with installer