# Codex — Installation Guide

## What You're Installing

Three files:

| File | Purpose |
|------|---------|
| `global_CLAUDE.md` | Teaching rules loaded into every Claude Code session |
| `codex_post_tool_use.py` | Hook: fires after every `src/` file write, generates explanation |
| `codex_stop.py` | Hook: fires when session ends, generates session summary |
| `settings.json` | Wires the hooks into Claude Code |

---

## Step 1 — Place the files

```bash
# Create hook directory
mkdir -p ~/.claude/hooks

# Copy hook scripts
cp codex_post_tool_use.py ~/.claude/hooks/
cp codex_stop.py ~/.claude/hooks/

# Make them executable
chmod +x ~/.claude/hooks/codex_post_tool_use.py
chmod +x ~/.claude/hooks/codex_stop.py

# Global CLAUDE.md
cp global_CLAUDE.md ~/.claude/CLAUDE.md

# Hook configuration — user level (applies to all projects)
cp settings.json ~/.claude/settings.json
```

If you already have a `~/.claude/settings.json`, merge the `hooks` block manually — don't overwrite it wholesale.

---

## Step 2 — Set your API key

The hooks call the Anthropic API using Haiku (fast, cheap). Your key must be in the environment:

```bash
# Add to ~/.zshrc or ~/.bashrc
export ANTHROPIC_API_KEY="sk-ant-..."
```

The key is read at hook execution time, so it needs to be available in shell sessions where you run Claude Code.

---

## Step 3 — Initialise a project

Every project that uses Codex needs:

1. Git initialised (required for diff extraction)
2. A `src/` directory (all code you want explained goes here)
3. A project-level `CLAUDE.md`

```bash
cd ~/projects/my-project
git init
mkdir -p src
```

Minimal project `CLAUDE.md`:

```markdown
# my-project

## What This Project Is
[One paragraph description]

## Current Build State
[What works, what doesn't, what's next]

## Architecture
[Key files and what they do]

## Known Fragile Areas
[Anything Claude should be careful around]
```

---

## Step 4 — Verify it works

Start a Claude Code session in your project and ask Claude to write a small file to `src/`:

```
Write a hello world Python script to src/hello.py
```

After Claude writes the file, check:

```bash
# Explanation file should exist
cat .codex/src/hello.md

# Log entry should be appended
cat .codex/codex.log
```

End the session (type `exit` or close). Check:

```bash
# Session summary should exist
cat .codex/sessions/$(date +%Y-%m-%d).md
```

---

## Directory Layout After First Session

```
my-project/
├── CLAUDE.md
├── src/
│   └── hello.py
└── .codex/
    ├── src/
    │   └── hello.md          ← auto-generated explanation
    ├── sessions/
    │   └── 2026-05-12.md     ← auto-generated session summary
    └── codex.log             ← append-only tool log
```

---

## Git Strategy

Commit `.codex/` with the project so explanations travel with the code:

```gitignore
# .gitignore — do NOT exclude .codex/
# Leave it out of .gitignore entirely
```

Or exclude it if you want explanations local only:

```gitignore
.codex/
```

Default recommendation: commit it. If you change machines or return after months away,
the explanation history is worth more than the disk space.

---

## Troubleshooting

**No `.codex/` directory appearing**
- Confirm the file is in `src/` — hooks only fire for files under `src/`
- Check `ANTHROPIC_API_KEY` is exported in the shell running Claude Code
- Run the hook manually to see errors: `echo '{"tool_input":{"file_path":"src/test.py"}}' | python3 ~/.claude/hooks/codex_post_tool_use.py`

**Explanation file is empty or contains an error message**
- API key issue — check the error text in the file
- Network issue — the hook has a 30s timeout

**Stop hook not generating summary**
- The hook skips if there are no log entries and no transcript content
- If it was a session with no `src/` writes, that's expected behaviour
- Check `stop_hook_active` isn't blocking it: this field prevents infinite loops and is normal

**Hook slowing down sessions noticeably**
- The PostToolUse hook calls Haiku which typically responds in 1-3 seconds
- This is synchronous — Claude waits for the hook before continuing
- If it's too slow, add `"async": true` to the hook config in `settings.json` (explanation writes asynchronously, slight risk of race condition on very fast consecutive writes)
