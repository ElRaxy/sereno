# Changelog

## 1.10.0

**Three fixes to how a session is named and identified.**

**The id shown is the session's id.** The panel's `session` row, the key that copies, and the
`id` field in `--json` were all handing out `name` — which is the row's *key*: the tmux session
name (`cc-VanguardIA-90a6fb95`) for a live one, the uuid for one from history. Pasting the first
into `claude --resume` resumes nothing. The panel and the copy key now give the Claude session id,
and `--json` gained `session_id` alongside `id`, which keeps its meaning.

**A title is a line, not a prompt.** With no `/rename` and no `aiTitle`, the title came from the
first user message *in full* — 1,727 characters in the longest one here — so twelve of the forty
rows in this machine's history showed the same name, and in the panel they were the same row
repeated. It is now cut at the first sentence, capped at 60 characters, and rows that still match
get their short id appended. A sentence under twelve characters ("Done.", "Ok.") is skipped rather
than used as a name, and a dot inside `progress/x.md` or `1.9.0` does not cut.

**The list refreshes while you are typing.** The refresh only ran on the `getch` timeout, so a
`/rename` done in another window did not show up until you left the keyboard alone for 2.5 s.
The clock is now checked on every turn, same period. Same cost — the refresh was not extra work,
it was postponed work.

## 1.9.0

**The picker stopped reading transcripts in one bite.** Each turn of the loop spends a 25 ms budget
on whatever is missing, starting with the row you are looking at and staying on it until it is done.

That read is what pays for `--usage`, for the peak behind the context bar, and for sorting by spend.
Before, arriving at a large session cost a 120 ms stall, and entering the spend sort cost 389 ms in
one go. Across the 40 sessions here it is now 12 turns of at most 38 ms instead of 345 ms at once,
and 0.002 ms once everything is read.

What comes back half-read says so, and is not painted as a total: the panel shows "reading…" where
the figures go. The **peak** is the one exception and is used mid-read — it can only grow, so a
partial falls short but never overshoots. On the 89 MB transcript it crosses 200k on the very first
turn, so the context bar corrects itself right away rather than after the whole file.

Because of that, the context bar of **every row in the list** now benefits from the peak, not just
the row under the cursor. Sorting by spend takes no partials — that would sort by how much has been
read — so a half-read row waits at the bottom and moves up once, when it finishes.

## 1.8.0

**The context guard now has memory.** It already refused to put the ceiling below the context a
session was holding; it now also looks at the **peak** that session ever reached.

Compacting destroys the evidence: the window drops to 16k and a one-million session starts being
drawn against the standard one. Across the 524 transcripts on this machine that misreads **30**
of them (5.7%), always the same way — one read 171k against 200k, an 86% that says "compact now",
when it was 171k of a million, a 17%.

The peak is rebuilt from the transcript `sereno` already reads end to end for `--usage`: the
`usage` of every reply, and the `preTokens` of every compaction. That field is context and not a
running total — checked against the reply just before each boundary, median +0.4% and 165 of 169
within ±5%. As coverage it beats the alternative by a lot: `preTokens` appears in 107 of 524
transcripts, `cost-state` in 13.

It costs nothing extra — those two lines were already being parsed — and it is exposed as
`peak_context_tokens` in `--json --usage`. Reading the whole file is what it needs, so today the
panel and `--usage` have it and the plain list does not.

**What is still not possible: proving a session is *not* on the big window.** Beyond `cost-state`
there is no evidence in the transcript — across those 524 there is not one auto-compaction, which
would give away the threshold, and not a single `message.model` carrying the `[1m]` suffix.

## 1.7.0

**`s` has a fifth sort: by what each session has burned.** New input plus output, heaviest first,
alongside activity, context, project and memory.

It is not the context bar wearing another hat, and the case that separates them is compacting:
it empties the window and does not give back what was already spent. Measured across the 40
sessions on this machine, the three that had compacted ranked 2nd, 3rd and 4th by spend and 5th,
7th and 8th by context. Against activity there is no resemblance at all — rho 0.13.

It is the only one of the five that sorts on something it has to go and read, so it reads once,
on entering the mode: 94 ms for 8 live sessions, 389 ms for the 40 in history, then nothing. The
other four cost the same as before, and `ordena()` still touches no disk — a separate pass loads
what it will need.

Which figure to sort on barely matters: `out`, `input+output` and `cache read` correlate at
rho >= 0.98 across those transcripts and share the same top 5, so it takes the one that fits in a
line. Money is out for a different reason — `totalCostUSD` is only written on exit, so it was
present in 16 of 40 sessions and in none of the live ones.

`SERENO_SORT=spend` leaves it on, `-spend` inverts it.

## 1.6.0

**`--watch` has a third thing to tell you: a session that starts going in circles.** It already
reported one stopping and two starting to write in the same place; the counts behind `↻` were
being computed for every row anyway, so this cost nothing to add.

Like the other two it fires on the transition, not the state: twenty minutes of the same loop is
one line, not one per poll. A session already looping when you start `--watch` is baseline, not
news — and if it then *also* starts sweeping, that is new and gets said.

## 1.5.0

**"Which one is stuck?" is answered in the list now, not one row at a time.** The two counts the
panel already made — the same command failing three times, two searches in a row finding nothing
— are now computed for every row on screen and show up as `↻` next to the state, with the wording
in `--list` and a `stuck` enum in `--json`.

It reuses the objects the status pass already parsed, so it reads nothing extra: 5 ms of CPU
across sixteen real rows, against the 49 that pass already costs.

The warning column is shared with the clash marker, and the clash wins it. Not because it is
more common — because missing it can cost you overwritten work, while missing the other costs
minutes. Both are shown in full in the panel and in `--list`.

**It is expected to stay quiet**, and that is measured: across 10,375 real tool calls from the
twelve largest transcripts here, the loop warning fires on zero windows and the sweep on one.
The thresholds were not loosened to produce a livelier number.

## 1.4.0

**The context ceiling now listens to the session before the machine.** `SERENO_CTX_MAX` still
wins, but under it the order flipped: what *this* session says — the `cost-state` line, then a
`[1m]` suffix in the transcript — now overrules the `model` in your global `settings.json`,
which a session launched with a different `--model` does not obey anyway.

The point of the flip is the direction that was impossible before: a session the CLI recorded
**without** the suffix can now bring the ceiling back down to the standard window. On a machine
configured for the big window, a 200k session used to be drawn against a million — 6% where 30%
was due.

A guard sits above all of it: the ceiling can never end up below the context already seen, so
lowering it can never produce a bar over 100%. And the Haiku the CLI runs for titles is ignored
when reading `cost-state` — counting it would let a throwaway conversation talk the ceiling
down on its own.

## 1.3.0

**The panel shows the path, not just the last step.** Under the prompt and the reply there is
now a trail of the last tool calls — what each one was, how long it took, and how it ended:
done, error, a search that found nothing, or still running with the clock ticking. It comes out
of the same tail of the transcript the panel already reads, only for the row under the cursor.

Two things in that trail are called out, and both are counted rather than sensed: the same
command failing three times in a row, and two searches in a row that come back empty. Anything
else in between resets the count — two empty greps with an edit between them are work, not a
sweep. "Twenty minutes on one call" gets no line of its own: `status` already says that, and
the same fact twice is not a second opinion.

**The context ceiling now has one fact about the session itself.** It used to be worked out
from your global `settings.json` and from how much context had already been seen — nothing that
knew whether *this* session was launched on the one-million window. The `cost-state` line the
CLI writes when it closes keys its `modelUsage` by `claude-opus-5[1m]`, suffix included. It is
rare (15 of 517 transcripts here) and it only ever raises the ceiling, but when it is there it
settles the question, and it costs no extra reading.

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
