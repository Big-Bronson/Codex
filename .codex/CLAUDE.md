## CLAUDE.md

### What This File Does

This is a configuration manifest that tells Claude (the AI) how to behave during development sessions with Steve Vella. It's not executable code—it's a standing instruction set that shapes how explanations are generated, what assumptions are safe to make, and what guardrails apply to code generation. The file sits at the project root and acts as a persistent context layer, read at the start of each session to establish ground rules.

### Why It Exists

Steve learns by building, not by being given finished solutions. He needs explanations grounded in *why* code exists—what operational problem it solves, not just what the syntax does. Without this file, Claude would default to generic task-completion mode: write the code, assume the user knows the reasoning, move on. This file forces a different contract: every piece of code must be justifiable in system terms, and that justification must be explicit in the work product (via the Codex hook system). It also documents Steve's technical context (MSP background, Linux/Python/Bash comfort, no need for fundamentals re-explanation) so explanations can be pitched correctly.

### What It Protects Against

This file protects against three failure modes:

1. **Shallow comprehension**: Code written and immediately forgotten because the *why* was never captured. The Codex hooks (referenced here) force written explanations into a logged artifact.
2. **Mismatched explanation level**: Wasting time re-explaining TCP/IP to someone with networking experience, or skipping crucial context for someone new to a pattern.
3. **Undocumented assumptions**: Multi-file changes where the interaction between files is opaque. The "comprehension guardrails" section explicitly require a plain-language summary before sign-off.

### Invariants

- This file is read at the start of every session and defines the global rule set.
- Any project-specific `CLAUDE.md` in a subdirectory *overrides* these rules, not supplements them.
- The Codex hook system (PostToolUse and Stop hooks) runs automatically; Claude does not need to manually invoke explanations.
- The default assumptions (Git init'd, Python 3, jq available, API key in environment) must hold true or tool invocations will fail silently.
- All code written must be explainable section-by-section; if it cannot be, it should not be written.

### Key Patterns

**Standing instruction set**: This is a human-readable contract that persists across sessions and shapes AI behaviour without being code. It's declarative (what the rules are) rather than imperative (how to enforce them).

**Context-as-configuration**: Instead of Steve repeating his background and learning style each session, it's written once and trusted to be read. Reduces friction, ensures consistency.

**Layered override model**: Global rules (this file) + project-specific rules (project CLAUDE.md) allow defaults without brittleness.

### Change Log

- 2026-05-12: Initial release; global teaching rules, explanation contract, Codex hook reference, communication style, and default environment assumptions.