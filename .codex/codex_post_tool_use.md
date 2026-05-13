## codex_post_tool_use.py

### What This File Does

This is a Git hook that fires after any file write or edit in a Claude Code session. It captures what changed, sends the diff to Claude via API, and receives back a structured plain-language explanation of the file's purpose, design decisions, and dependencies. That explanation gets written to `.codex/src/` (mirroring the source tree structure) and a one-line summary gets appended to `codex.log`. The hook acts as a living documentation engine—every time code changes, the explanation updates automatically.

### Why It Exists

When AI assists with writing code, the developer can end up with working code they don't fully own mentally. They understand the syntax but not the design tradeoffs, constraints, or invariants baked in. This hook solves that by forcing an explanation to be generated and recorded immediately after each edit, while the context is fresh. It also creates a searchable audit trail in `codex.log` so you can see what changed and why without digging through git history. The hook makes the collaboration artifact—the reasoning behind decisions—explicit and persistent.

### What It Protects Against

The hook defends against three failure modes: (1) code drift where explanations go stale and become misleading, (2) knowledge loss when the AI context window expires and you forget why a design choice was made, and (3) onboarding friction when new developers (or the original developer six months later) can't understand the actual intent from syntax alone. It also guards against over-reliance on git commit messages by keeping structured, semantically consistent explanations in a parallel tree.

### Invariants

- `ANTHROPIC_API_KEY` must be set in the environment, or all explanations fail gracefully.
- Every file under the configured `src_root` that gets written must produce a corresponding `.md` explanation file under `.codex/<src_root>/`.
- The explanation path must preserve the directory structure of the source tree.
- `codex.log` entries must always include a timestamp and file path, maintaining chronological append-only order.
- The git diff must be retrievable; if not, the full file content is used as fallback.
- Configuration in `.codex/config.json` (if present) takes precedence over the hardcoded `src_root` default.
- Existing explanations are preserved and appended to, not overwritten; the change log grows upward.

### Key Patterns

**Configuration layering**: The hook reads from `.codex/config.json` to allow per-project source root override, falling back to "src" if absent. This keeps the tool flexible without requiring edits to the hook itself.

**Graceful degradation**: Every operation that might fail (API call, git diff, file I/O) has a try-except wrapper that returns an error message instead of crashing. The hook never blocks the editor.

**Diff-as-context**: Rather than re-analyzing the entire file, the hook sends only the git diff (or full content for new files) to Claude. This keeps API tokens low and focuses explanation on what actually changed.

**Mirror tree structure**: Explanations live in `.codex/<src_root>/` so the directory layout matches the source tree exactly. This makes it trivial to map between a source file and its explanation without string manipulation.

**Append-only log**: `codex.log` is write-once per edit, never mutated. Each entry includes a timestamp and file path, creating an immutable record of what happened and when.

### Change Log

- 2026-05-12: Refactor to serve both documentation and pedagogy in Codex prompts; shift from documentation-only to teaching-focused explanations; add "Decisions Made Here" and "If You Changed This" sections.
- 2026-05-12: Make source root configurable via `.codex/config.json` so hook works with any project layout.
- 2026-05-12: Initial release of Codex hook system with PostToolUse and Stop hooks, global CLAUDE.md teaching rules, settings.json wiring, and install.py automation.