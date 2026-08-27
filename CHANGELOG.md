# Changelog

## 1.3.0

**What a session has burned, with `--usage`.** The context bar says how full the window is right
now; it says nothing about the twelve hours already spent, because a session that compacted three
times reads 20%. The new flag adds tokens in and out, cache read, replies, compactions and the
minutes actually worked — to `--list`, to `--json`, and to the detail panel, which now also shows
the compaction count pinned to the context percentage that it explains.

Four figures and no total. Cache read is the same material being read again, and it runs a
hundred times larger than everything else put together; adding it to the input gives a number
that means nothing. The four parts stay apart.

It is off by default: the figure is spread across the whole transcript, so the file has to be
read end to end — 0.11 ms for the median one here, 223 ms for the largest on disk. Inside the
picker it is read for the row under the cursor and cached, so a refresh costs 2.6 ms.

**No price table.** `sereno` does not work out money. When the CLI leaves its own `cost-state`
line, that `totalCostUSD` is relayed as-is in `api_cost_usd`, and only in `--json --usage` — never
in the TUI, where on a subscription plan it would be money you did not pay.

Said plainly in the README because it changes how you read the number: subagent turns and the
CLI's own Haiku calls leave no line in the transcript, so a session that delegated a lot
under-reports.

## 1.2.1

**`--list` shows the four states, like the picker does.** It used to say only "running" or
"idle", collapsing four into two and losing the one that matters — a session stuck inside a
three-minute command, which by file date is indistinguishable from an abandoned one. It also
shows the context percentage now, and durations past two days read as `7d 2h` instead of
`170h 26m`.

**The Spanish interface is now written in Spanish.** Of 245 strings exactly one carried an
accent: the whole UI read like it had been typed on a keyboard without them. All of them are
fixed, and the i18n test now fails on any string containing a word that always takes an accent.

## 1.2.0

**The title is the last thing to be cut.** It was the first: at 70 columns the list showed
"Refactor pa…" next to a "checkout-api" with its whole branch, sacrificing the one thing that
tells two rows apart to keep a value that repeats on every line and appears in full in the panel
anyway. Now the title is served first and the support columns light up with what's left, in
order: context, project, memory.

**The state marker moved to the left, next to the title.** It used to be painted after the title,
which is padded out to the longest one on screen — so a short title left fifteen blanks between
the sentence and the dot telling you whether that session is alive.

**A column with nothing to say now takes no space.** No tmux means no memory column at all rather
than eight blanks per row; a Codex tab drops the context column the same way.

Resizing can no longer shrink a column. Widening the window used to *narrow* the title, because
the project column came back and took the room — found by the new test, not by looking.

### Fixed

- The memory needle is gone: it drew the same fact as the figure right next to it, with less
  precision. The figure stays, coloured by the same threshold.
- `fijas`, the width of everything that isn't the title, was a hardcoded 38 that was already off
  by one. It's now derived from the columns themselves, in a pure function with its own test.

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
