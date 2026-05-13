## codex_stop.py

### What This File Does
This file is a **Stop Hook** that executes when Claude Code finishes a session turn. It reads the session transcript and activity log, sends them to Claude via the Anthropic API, and writes a structured plain-language summary to `.codex/sessions/YYYY-MM-DD.md`. The summary is designed to serve both as accurate documentation and as a teaching resource that helps the developer understand what was built and be ready to continue the next session.

### Why It Exists
Claude Code sessions are ephemeral — once a turn ends, the context is gone. Developers need a persistent, human-readable record of what happened, what was decided, and what patterns were introduced. This hook closes that gap by automatically capturing the session state at the moment it ends, before information is lost. It also serves pedagogical intent: by forcing Claude to articulate *why* decisions were made and *what the developer should be able to explain*, it creates a learning artifact, not just a log file.

### What It Protects Against
This code defends against several failure modes: (1) Missing or malformed transcript files — it validates file existence and gracefully handles JSON parse errors line-by-line. (2) Unbounded context — it truncates transcript to last 200 entries and log to last 3000 chars to keep token usage reasonable. (3) API failures — it catches HTTP errors and request timeouts (45-second limit) and writes error messages to the summary file rather than crashing silently. (4) Missing API keys — it checks for `ANTHROPIC_API_KEY` and returns an error block instead of failing hard. (5) Sessions spanning multiple stops — it loads any existing summary for the day and instructs Claude to merge new information rather than overwrite.

### Invariants
- `CODEX_ROOT` (`.codex`) and `SESSIONS_DIR` (`.codex/sessions`) must be writable.
- `ANTHROPIC_API_KEY` environment variable must be set for API calls to succeed.
- Session transcript files (if provided) must be valid JSONL, with entries containing `role` and `content` fields.
- Summaries are written one per calendar day (keyed by `YYYY-MM-DD`), and may be appended to if a session spans multiple stops.
- The prompt structure and section headers are rigid — Claude must follow the exact template or summaries will be inconsistent across sessions.

### Key Patterns
**Defensive parsing**: The transcript reader processes JSONL line-by-line, catching and skipping malformed entries rather than failing the whole operation. **Graceful degradation**: All I/O operations (file reads, API calls) return empty strings or error blocks instead of raising exceptions, allowing the hook to always produce *some* output. **Context windowing**: Both transcript and log are deliberately truncated to recent entries, prioritizing recency over completeness — a pragmatic choice for token-constrained API calls. **Incremental summaries**: The hook checks for existing summaries and instructs Claude to merge, not replace, allowing long projects to accumulate a coherent narrative across multiple sessions. **Pedagogical prompting**: The prompt explicitly asks Claude to frame output as "what you should be able to explain" and "questions you must answer," embedding learning intent into the artifact.

### Change Log
- 2026-05-12: refactor: serve both documentation and pedagogy in Codex prompts
- 2026-05-12: refactor: shift Codex prompts from documentation to pedagogy
- 2026-05-12: Initial release: Codex hook system with installer