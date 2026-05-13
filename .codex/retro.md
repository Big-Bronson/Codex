## retro.py

### What This File Does
This script backfills Codex documentation for existing Git repositories that were not using Codex from the start. It crawls the Git history of a project's source files, generates plain-language technical explanations for each file based on its commit history and current content, and creates session summaries organized by date. The output is written to `.codex/<src_root>/<filename>.md` for individual files and `.codex/sessions/YYYY-MM-DD.md` for daily summaries.

### Why It Exists
When a developer adopts Codex on an existing project, there is no historical record of explanations for files that predate the adoption. This script solves the cold-start problem by retroactively generating those explanations using the Git history that already exists, allowing Codex to cover the entire project's evolution without manual intervention.

### What It Protects Against
The code defends against several practical deployment hazards: (1) **encoding crashes** — Git output containing non-UTF-8 sequences (Windows cp1252 filenames, binary diffs, etc.) are decoded with `errors="replace"` rather than crashing; (2) **Windows console incompatibility** — stdout/stderr are explicitly reconfigured to UTF-8 before any output to prevent cp1252 encoding crashes when printing Unicode characters like ✓ and ✗; (3) **accidental processing of binary files** — files are filtered by extension and null-byte detection before explanation generation; (4) **API rate limits** — the `call_api()` function retries up to 3 times with exponential backoff on 429 responses; (5) **incomplete repositories** — Git commands gracefully handle edge cases like `HEAD~1` on single-commit repos by ignoring return codes and treating empty output as "nothing to report."

### Invariants
- `ANTHROPIC_API_KEY` must be set in the environment, or all API calls will return error strings without crashing the script.
- The Git repository at `repo_path` must be valid and accessible; invalid repos cause Git commands to return empty strings, which are handled as "no data" rather than failures.
- `.codex/config.json` (if present) must be valid JSON; if it is not, `src_root` defaults to `"src"`.
- Binary files (detected by extension or null bytes) are never opened for explanation, preventing crashes from unprintable content.
- All file paths are relative to `repo_path` and are consistently normalized by `git ls-files`, so path handling is deterministic.

### Key Patterns
**Graceful degradation through error strings** — API failures and Git errors are returned as human-readable strings and written to output files rather than raising exceptions, allowing the script to continue processing remaining files. **Cheap re-runs** — the `--force` flag controls whether existing `.codex/` files are overwritten; by default, the script only generates missing files, making incremental runs fast. **Binary detection layering** — extension check (O(1)) happens first, then null-byte scanning (O(1) on typical files), so binary files are rejected cheaply. **Encoding-safe subprocess wrapper** — the `git()` helper function decodes all subprocess output with `errors="replace"`, making it safe to pipe any Git output without crashing on non-UTF-8 bytes. **Token budget awareness** — the API is called with different `max_tokens` limits for file explanations (1024) versus session summaries (1500) to control cost and latency per use case.

### Change Log
- 2026-05-12: Fix cp1252 crash on Windows by reconfiguring stdout to UTF-8
- 2026-05-12: Add retro.py: retroactive Codex backfill for existing projects