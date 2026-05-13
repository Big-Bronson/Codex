## codex_stop.py

### What This File Does
This file is a lifecycle hook that fires when Claude Code finishes a session turn. It reads the session transcript and activity log, sends them to Claude's API, and writes back a structured plain-language summary into `.codex/sessions/YYYY-MM-DD.md`. The summary serves dual purposes: it documents what was built and decided, and it teaches the developer what they should be able to explain before the next session.

### Why It Exists
Claude Code sessions are ephemeral—once closed, context is lost. Developers need a durable record that isn't raw logs or code diffs, but a narrative they can read in 5 minutes to reorient themselves. Without this hook, developers either rebuild context from scratch (costly) or lose critical decision rationale (risky). The hook automates the gap-closing work that a human notetaker would do.

### What It Protects Against
The code defends against: missing API keys (returns a graceful error instead of crashing), malformed JSONL transcripts (skips unparseable lines), missing or empty log files (proceeds with empty context), transcript size explosion (caps at 200 entries and 4000 chars to stay within token budgets), and transient API failures (catches HTTP and socket errors, returns error message to file). It does not protect against: incomplete transcript writes (assumes Claude Code writes atomically) or session files being edited during hook execution.

### Invariants
- `ANTHROPIC_API_KEY` must be set in the environment, or the summary will contain an error message instead of failing hard.
- The session file `.codex/sessions/` directory must be writable; the hook assumes it exists or can be created.
- The transcript path passed via stdin (if any) must be valid UTF-8 or decodable with error replacement.
- The API response must contain a `content[0].text` field; if not, an error message is returned.
- A session summary file, once written, may be overwritten if the hook fires again the same day (by design—it merges with existing content via the prompt).

### Key Patterns
- **Defensive parsing**: The code uses `errors="replace"` on file reads and wraps all JSON parsing in try-except, allowing partial data loss rather than total failure.
- **Context windowing**: Both transcript (last 200 lines) and log (last 3000 chars) are truncated to prevent token budget overflow, a hard constraint when calling external APIs.
- **Graceful degradation**: If any data source is missing or corrupt, the function continues with empty strings rather than aborting.
- **Incremental summarization**: The prompt instructs Claude to merge new information into an existing summary if one exists, allowing multi-turn sessions to accumulate detail rather than restart from scratch.
- **Pedagogical prompt design**: The prompt explicitly asks for "questions the developer must answer" and "what to read before next session," embedding teaching goals into the API call itself.

### Change Log
- 2026-05-12: refactor: serve both documentation and pedagogy in Codex prompts
- 2026-05-12: refactor: shift Codex prompts from documentation to pedagogy
- 2026-05-12: Initial release: Codex hook system with installer