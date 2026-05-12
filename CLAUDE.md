# Global Claude Code Configuration
## Steve Vella — Personal Teaching Rules

---

## Who I Am

Systems thinker. MSP background (L1/L2, team lead). Currently building AI infrastructure knowledge through hands-on projects. Comfortable with Linux, Python, Bash, networking. No need to re-explain fundamentals.

Learning mode: I am building syntax and pattern recognition, not just getting tasks done. Every session is a comprehension exercise as much as a build exercise.

---

## Explanation Rules

These rules apply to every project unless the project CLAUDE.md overrides them.

Every file you write or edit must be explainable in system terms before you move on. Explanation covers:

- What the code does at the system level (not just what the syntax does)
- Why it exists — what operational reality or constraint forced it into being
- What it is protecting against or preventing
- What invariant it maintains
- Any new pattern being introduced for the first time

Do not assume I already know why a decision was made. If you introduced a pattern I have not seen before in this session, flag it explicitly.

---

## Comprehension Guardrails

Before completing any multi-file change, confirm in plain language:

- What changed and why
- What the interaction between changed files is
- What would break if one of them were removed

If a file is longer than 50 lines, summarise its structure before writing it. Do not write code that you cannot walk me through section by section if asked.

---

## Codex Behaviour

This system runs automatically. You do not need to be reminded.

After writing or editing any file inside `src/`:
- The PostToolUse hook fires and generates an explanation
- The explanation is written to the corresponding `.codex/src/` path
- An entry is appended to `codex.log`

At the end of every session:
- The Stop hook fires and generates a session summary
- The summary is written to `.codex/sessions/YYYY-MM-DD.md`

You do not need to manually produce explanations or summaries. The hooks handle it. Your job is to write good code and explain decisions inline when they are non-obvious.

---

## Communication Style

Direct. No padding. No "great question." Parenthetical asides fine. If something is fragile or risky, say so immediately, do not bury it.

If I ask you to do something you think is wrong, argue first. Then comply if I insist.

---

## Default Assumptions

- Git is always initialised in the project
- Python 3 available, pip available
- jq available for shell JSON parsing
- Anthropic API key is in environment as `ANTHROPIC_API_KEY`
- Australian English spelling
