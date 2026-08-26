# Changelog

## 1.1.0

**Context used, per session.** A bar in the list and the exact figures in the panel. The number
comes from the `usage` that every reply leaves in the transcript, so nothing is estimated and no
API is called.

The ceiling is the one thing Claude Code does not write down: a session running the 1M window
records itself as `claude-opus-5`, exactly like a 200k one. It is worked out from `SERENO_CTX_MAX`,
a `[1m]` suffix, your `settings.json`, and finally the context already observed. That last rule is
what keeps the bar from reading above 100%, and a test fails if it ever does.

**`--watch`** sits there and tells you the moment a session stops working and waits on you. The
transition, not the state: most sessions are idle most of the time. Desktop notification plus a
line on stdout. The first pass is silent, so starting it does not announce what you already knew.

**`--find "text"`** searches what was said, skipping tool output and the `CLAUDE.md` the CLI
pastes into every session, then opens the picker with only the matching sessions. Over 506
transcripts here, 287 files contained a given word and 25 had it in something anyone said.

**`--json`**, with a stable `state` enum, for statuslines and scripts. It carries no
conversation: no prompt, no reply. `--all` adds the resumable history.

**`--demo`**, the environment variable written short, for a first look with no sessions of your
own.

**Model** shown per session, from the same place as the context.

### Fixed

- The detail panel measured itself one column too wide, and curses wraps the overflow to the
  start of the next line. A stray character sat against the left edge, including in the README
  GIF, and looked like terminal dirt.
- The recovery branch after a crash was in Spanish regardless of language, and two of its
  messages named a command that is not the program. The i18n test now walks the AST and fails on
  any phrase printed without going through the translator.
- `--find` opened the picker on the live tab, which hid its own results behind "nothing matches".
- An unknown flag was swallowed: `sereno --jsonn` opened the picker, so a script asking for JSON
  got a TUI waiting for keys. It now says so, and suggests the closest real flag.
- A resumed session was read from the transcript it stopped writing to, so one that was working
  showed as idle, and sometimes twice. On resume the new transcript copies the old lines, and
  those lines keep their original `session_id` while the line's own `sessionId` is the new one:
  that pair is an exact link to the successor, so there is no guessing by timestamps.
- Selection shortcuts (`idle`, `detached`, `all`) work in both languages.
- With no sessions at all, the first screen says what to do next, and if `~/.claude/projects` is
  missing it says that too: the CLI writes that folder, so its absence is a diagnosis.

## 1.0.0

First public release. Picker with mouse support, four session states read from the transcript,
discovery without tmux, isolated demo mode, English and Spanish.
