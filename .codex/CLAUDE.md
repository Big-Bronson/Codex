## CLAUDE.md

### What This File Does

This is a configuration manifest that establishes teaching conventions and operational rules for AI-assisted development sessions. It's a contract between Steve (the developer) and Claude (the AI) that specifies how code should be explained, what assumptions are safe to make, and how the automated Codex hook system behaves. It runs once per session as context and is consulted whenever decisions about code quality, communication style, or explanation depth need to be made.

### Why It Exists

Steve builds projects in learning mode—each session is as much about understanding patterns and system design as it is about shipping features. Without explicit teaching rules, Claude would default to task-completion mode (write fast, explain briefly). This file inverts that: it makes comprehension the primary goal and flags when a new pattern appears. It also documents the Codex hook infrastructure so Steve knows that explanations are being auto-generated and doesn't need to request them manually.

### What It Protects Against

It prevents shallow technical explanation. By requiring system-level reasoning (what does this do, why does it exist, what does it prevent, what invariant does it maintain), it catches code that "works" but relies on magic or unexplained heuristics. It also prevents context drift: by stating Steve's background upfront (MSP, Linux, Python, Bash), it stops Claude re-explaining fundamentals and wasting session tokens. The multi-file comprehension guardrail prevents Claude from shipping coordinated changes where the interaction between files is invisible.

### Invariants

- Every file in `src/` gets an automatic explanation written to `.codex/src/` after modification (PostToolUse hook fires)
- Every session generates a summary in `.codex/sessions/YYYY-MM-DD.md` (Stop hook fires)
- Project-level CLAUDE.md files override these global rules if they exist
- The Anthropic API key is always available as `ANTHROPIC_API_KEY` in the environment
- Communication must be direct and risk-transparent (fragile code is flagged immediately, not buried)

### Key Patterns

**Teaching-first development**: Code is justified before it's written, not after. Explanations happen inline and are reinforced by hooks.

**Hook-based automation**: Explanation labour is offloaded to PostToolUse and Stop hooks so the developer doesn't manually request summaries. The system is self-documenting.

**Explicit context**: Background, learning goals, and communication preferences are stated once and remain in scope for the entire session, reducing negotiation overhead.

**Guardrail-based comprehension**: Multi-file changes require explicit confirmation of interactions before completion, preventing distributed complexity from hiding.

### Change Log

- 2026-05-12: Initial release, Codex hook system with installer