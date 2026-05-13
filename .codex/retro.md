## retro.py

### What This File Does

This script backfills the `.codex/` directory with AI-generated explanations for an existing project that didn't have Codex enabled from the start. It scans the git repository's source files, extracts their full commit history, calls Claude to generate plain-language technical explanations, and writes both per-file markdown documents and per-day session summaries.

### Why It Exists

When Codex is installed mid-project, there's no historical record of explanations for files that predate the installation. This script solves the cold-start problem by mining git history to reconstruct that missing context. It allows teams to retroactively document legacy code without manually writing explanations or starting fresh with a new repository.

### What It Protects Against

The script defends against several categories of failure:

- **Encoding crashes on Windows**: Reconfigures stdout/stderr to UTF-8 with error replacement before any output, preventing cp1252 console crashes when displaying Unicode progress characters (✓ ✗).
- **Non-UTF-8 git output**: The `git()` helper uses `errors="replace"` when decoding subprocess output, so binary diffs, cp1252 filenames, or other non-UTF-8 sequences never crash the parser.
- **Binary file processing**: The `is_binary()` function checks file extensions and scans for null bytes to avoid feeding executables, images, or compiled files to the API.
- **Codex recursion**: Explicitly filters out `.codex/` paths from file discovery, preventing the script from explaining explanations when `src_root` is set to `.`.
- **API rate limits**: The `call_api()` function retries up to 3 times on 429 responses with exponential backoff.
- **Missing git history edge cases**: Tolerates single-commit repos and files with no introduction diffs by treating empty git output as "nothing to report."

### Invariants

- `ANTHROPIC_API_KEY` environment variable must be set before any API call.
- `repo_path` must point to the root of a valid git repository.
- `.codex/config.json` must exist or have sensible defaults applied (`src_root` defaults to `"src"`).
- All generated output files must be written with UTF-8 encoding.
- Files matching `BINARY_EXTENSIONS` or containing null bytes must never be passed to the API.
- `.codex/` itself must be excluded from file discovery regardless of `src_root` value.
- Session summaries must be keyed by `YYYY-MM-DD` dates extracted from commit timestamps.

### Key Patterns

- **Encoding-safe subprocess wrapping**: The `git()` helper centralizes all git command execution and always decodes output with error replacement, making it safe to call without try-except blocks.
- **Graceful API error handling**: `call_api()` returns error strings (prefixed with `[Error: ...]`) instead of raising exceptions, allowing the script to continue and write failed results to disk for inspection.
- **Extension-first binary detection**: `is_binary()` checks file extensions before reading file content, avoiding the cost of I/O for known binary types.
- **Deferred file reading**: Source file content is read only once per file and passed into the prompt context rather than accessed repeatedly.
- **History aggregation by date**: Commits are collected and grouped by date for session summary generation, allowing multiple commits from the same day to be bundled into one summary.

### Change Log

- 2026-05-12: Fix cp1252 crash on Windows by reconfiguring stdout to UTF-8
- 2026-05-12: Add retro.py — retroactive Codex generator for existing projects