# Changelog

## 1.18.0

**Open the marked ones at once — and hand them to another CLI.**

`r` ("reopen the marked ones as tabs") already existed and **was broken outside tmux.** There
were three copies of the same Warp YAML in the file — open one, reopen several, restore the
orphans — and the middle one had the command hardcoded to `tmux attach`. Marking five history
sessions and pressing `r` opened five tabs that all failed: `tmux attach -t <uuid>` is not a
thing. `_comando_de()` already knew the right command for all three cases and nobody asked it.

Now there is **one** writer of that YAML and **one** place that decides the command, so a fourth
copy cannot bring the bug back. Also in the picker:

- `r` now requires marking. With nothing marked it used to open **every visible row at once**,
  and it sits next to the arrow keys.
- The notice says what was left out and why — already had a tab, or cannot be opened from here.
  They used to be dropped in silence.

**`c` hands the marked sessions over to another CLI.** A handover, not a migration: a Claude
session's context lives in its own transcript and no other CLI can pick it up. So `c` opens a
**new** session of the other CLI in the same directory and branch, with a briefing of where the
Claude one got to — project, branch, title, state and its last tool calls.

Facts only. No prompt and no reply of yours goes in there: the briefing travels inside Warp's
launch configuration, which stays on disk. `SERENO_RELEVO=completo` adds the conversation, and
is never the default. A session whose directory no longer exists is left out instead of starting
in `~`, because a handover that begins in the wrong place looks like it worked.

Only CLIs actually on your `PATH` are offered — today that table holds `codex`, whose
`codex [PROMPT]` was checked against its `--help`. `gemini` is not in it because it is not
installed here and its flag would have been a guess.

Found while testing this and worth its own line: **a command with newlines broke the YAML.** The
briefing has them, `- exec: <command>` spilled them loose, and the file came out invalid — the
window simply does not open and nothing in the program errors. It is written as a literal block
now, and a test unwraps it back.

## 1.17.0

**`sereno --now` — what all of them are running, in one screen.**

The panel already drew the trail of tool calls: glyph per call, timer, failures marked, and the
stuck-detection on top. Of **one** session — the row under the cursor. So finding out what nine
sessions were doing meant moving the cursor down nine times, and in practice you went back to
attaching to each one, which is the thing this program exists to avoid.

```
4 live · 2 working, 2 waiting on you

Refactor payment webhooks  ·  checkout-api                  in a command
  ! the same command has failed 3 times
    ✗  31s  Bash · pytest tests/webhooks -x -q
    ✗  33s  Bash · pytest tests/webhooks -x -q
    ◐   1m  Bash · pytest tests/webhooks -x -q
```

No new column and no fight for width: the row layout is untouched. It reads exactly what the
panel reads — the tail of each transcript — so it opens nothing extra beyond what each row
already needs, and it is the live sessions only, never the 595 in the history.

The header is counted **from the rows underneath**, not on its own, and a test fails if the two
ever disagree: a summary nobody recomputes while reading it is a summary that drifts.

## 1.16.0

**The one that has already finished stops calling itself busy.**

`writing` was decided by the transcript's mtime: touched in the last 90 seconds. That stays true
for a minute and a half **after** a session answers you — precisely the window in which you want
to know which of the nine is now waiting. Sampled against Claude Code's own spinner on
2026-08-28, across nine live sessions and 90 readings, **16 of the 48 that said `writing` were
sessions that had already stopped** — a third of them. None the other way round, so the error had
a direction: it hid the ones asking for you.

The transcript already said so and nobody was reading it. The CLI writes `stop_reason` on every
reply, and `end_turn` means the turn is closed. A later `user` line — a new prompt, or the result
of the command it was waiting on — reopens it. Both facts come out of the same pass `pulso()`
already makes over the last 80 lines: **no extra read, no extra file opened**.

- `--watch` now fires when the turn actually closes, not up to 90 s later.
- `--json` gains `turn_closed`, next to `writing` and `tool_pending`. It is `null` when the
  transcript does not say — an old transcript, another CLI — and there the state is decided
  exactly as before. A missing fact is not a good fact.
- Verified by turning the mechanism off: with the guard removed, or with `turn_closed` forced
  true, `tests/test_fin_de_turno.py` goes red in both directions.

**What it does not fix, measured on the same bench: 4 of 26.** A session whose last line is a
`tool_result` that never got an answer — interrupted, or dead mid-turn — still reads `writing`
until the 90 s run out. From the transcript that is indistinguishable from a reply about to
arrive, and inventing the difference would be guessing. Down from a third to one in six, not to
zero.

## 1.15.0

**`sereno --disk` — what the transcripts weigh, and where that weight is.**

The panel gives the size of the row under the cursor and nothing else, so the split was invisible.
On the machine this was written on it turned out to be **3.4 GB across 595 sessions**, with
3,464 MB of it in a single project and **403 MB in five sessions** — none of which was visible
anywhere, on a laptop whose disk sits at 97%.

```
3.4 GB in 595 sessions · /Users/you/.claude/projects
  plus 285 subagent transcripts, 436 KB

by project
  VanguardIA                       442      3.4 GB
  and 56 more projects, 3.8 MB between them

the heaviest sessions
     85.2 MB  25d ago  Rebuild the atelier landing page       445cdc22
     …

102 of them (2.9 MB) have no place to go back to.
```

**It deletes nothing, offers to delete nothing, and calls nothing garbage.** `sereno` writes to
nothing that belongs to a session — a heavy history is a fact, not a problem, and what to do about
it is not the tool's call. The facts come out of one function and the printing out of another, so
the numbers can be checked without reading the layout.

340ms for 595 sessions: a `stat` on each, the `cwd` read from each header — the cheapest thing that
answers *does this history still belong to something that exists* — and the title only of the
handful it prints. Subagent transcripts are counted apart, because 285 of them here weigh 436 KB:
folding them into the split would move the file count without moving a megabyte.

Two things measured on the way in, and worth knowing before you go looking for space: **the
irrecoverable sessions weigh nothing** (102 of them, 2.9 MB — the ones with nowhere to go back to,
sunk in the list since 1.14.0), and neither do subagent transcripts. The weight is in long sessions
of the project you actually work on.

## 1.14.2

**Closes the four minor findings the 1.14.1 audit left open on purpose.**

- **`bump-tap.sh` now checks the fact, not the shape.** It validated that a sha *looked* like a sha
  and that the formula had exactly one url and one sha256 — never that the release existed. Handed a
  version that was never published it exited 0 and left the tap pointing at a 404, with only the
  tap's weekly cron to notice, up to seven days later. It now downloads the asset and compares its
  sha against the one it was told to write, so the guarantee belongs to the script instead of to the
  order in which `release.sh` happens to call it.
- **A formula carrying an explicit `version` stanza is refused.** That stanza is a third copy of the
  version number this script does not touch: Homebrew would use the old one while downloading the
  new asset, the `install` guard would `odie`, and `brew install` would be broken for everyone.
  Reproduced before fixing.
- **The header arithmetic has a test.** A row that never started *and* lost its directory is counted
  once, under *never started*, which is what makes the labels add up to the number of rows. Removing
  that condition used to keep the suite green; now it fails.
- **`SERENO_SIN_TAP`, `SERENO_TAP_REMOTO` and `SERENO_ASSET_BASE` are documented** in both READMEs.

`test_bump_tap.py` gained three cases — a version that is not published, a sha that is not the
published asset's, and the `version` stanza — and now serves assets over `file://`, so it exercises
the network check end to end without a network.

## 1.14.1

**An audit of 1.14.0 refuted one of its claims and found six mechanisms whose tests passed with the
mechanism switched off.** Nothing was broken; several things were less proven than they read.

- **`hay_sitio()` marked a directory that exists.** It used `os.path.isdir`, which swallows the
  error inside and returns False, so a permission denied or a symlink loop came out as *the
  directory is gone* — the exact absence the guard claimed to prevent, and its `except OSError` was
  dead code that never ran. Now `os.stat` + `S_ISDIR`, with `FileNotFoundError` separated from *could
  not look*. Reproduced: a directory whose parent is `chmod 000` used to sink its row, and does not
  any more.
- **The TTL was never tested.** The test cleared the cache by hand instead of letting it expire, so a
  cache that never expired — a row that would never revive — passed green. It now moves the clock.
- **`release.sh` calling the tap bump was checked for existence, not position.** The whole guarantee
  is positional: `bump-tap.sh` validates the *shape* of a sha, never the *fact* that the asset
  exists, so what protects the tap is that the call sits behind the verify-by-download. Moving it
  earlier kept the test green. Now the order itself is asserted.
- **The zero that meant no accounting.** The CLI writes `cost-state` with `totalCostUSD: 0` and an
  empty `modelUsage` on a subscription plan; that is not *this session cost nothing*, it is *nobody
  is counting*. It was stored as `0.0`, telling a statusline the work was free. Measured across the
  878 transcripts on this machine: 40 lines with a real cost, 8 with that undocumented zero, and
  **none** with a legitimate zero — so telling them apart loses no real case.
- **The privacy paragraph named a list of imports it called complete, and it wasn't.** `base64`
  joined in 1.13.0 with OSC 52 and the list never said so. `test_sin_red.py` now checks the list in
  both READMEs against the imports the program actually has.
- **Two published numbers were wrong** and are corrected in the 1.14.0 entry: caching per path saves
  3 stats out of 40 on a cold start, not 36, and the claim that the `stat` cannot block the TUI is
  false — the reload is synchronous with painting, so a hung mount freezes the list.

The full audit is in the repo history of the PR that fixed this.

## 1.14.0

**Sessions you cannot go back to stop competing for the top of the list.**

A session whose working directory no longer exists cannot be resumed in any useful sense: it drops
you into a `cd` to a place that is not there. Those now sort below everything, print in grey, and
the header counts them apart — `6 resumable · 40 with nowhere to go back to`.

It is the twin of what 1.12.0 did for sessions that never started, asking the same question from
the other side. Those never answered; these answered plenty and lost their destination, so the two
counts never overlap.

On the machine this was written on it was **40 of the 46 history rows**. That number is inflated by
53 sessions an optimiser had left behind that same morning, so here it is without them: still **28
of 37**, in two very specific flavours — worktrees already deleted (10 of 15) and temporary
directories (18 of 18, every single one).

**They are sunk, never hidden.** A directory missing today may be a worktree you recreate or a disk
you remount. The check is cached per path with a 30-second TTL, so a row revives on its own without
a restart.

Two guards, both because a missing directory is not always a missing directory: a session with no
recorded `cwd` is never marked (flagging a row over an absent field is the mistake this fixes), and
a live session is never marked, since its process is running inside that directory.

The `stat` deliberately does not live in `ordena()`, which is pure and runs four times a second: it
is resolved once when the row is built, which brings the amortised cost down to roughly one `stat`
per distinct path every 30 seconds.

**That reduces repetition, not blocking**, and the first cut of this entry claimed otherwise. The
reload runs synchronously in the loop that paints, so on a hung mount — where a `stat` never returns
— the list freezes: no repaint, no keys. Measured by injecting 1s of latency per `stat`: the first
pass takes 37.4s. Two numbers from that first cut were wrong too, and are corrected here: caching
per path saves 3 stats out of 40 on a cold start (40 rows are 36 distinct paths, not four), and what
it actually saves is the repeat between refreshes — 37 stats down to 1.

`--json` grows one field, `cwd_exists`, so a statusline can filter for what is genuinely resumable
instead of guessing from the project name.

Also: the Spanish README was missing the "sessions that never started" section that 1.12.0 added to
the English one. Both are in now.

## 1.13.1

**Same program as 1.13.0. Use this one: the file published under 1.13.0 is not the program.**

The release procedure extracted the file with `git show $SHA:sereno`. Under zsh that does not
extract anything: `$SHA:sereno` starts with `:s`, the substitution modifier, so the shell eats the
suffix and leaves the bare sha — the command becomes `git show <sha>`, which prints the commit
log. No error, exit 0. The asset published under v1.13.0 was that log, and GitHub releases are
immutable, so it could not be replaced.

The trap only springs when the path starts with `s` (`$V:foo` expands fine) and the file in this
repo is called `sereno`, so it is not something to remember. Releases now go through
`./release.sh <version>`, which uses braces and — more to the point — **refuses to publish** if
what it extracted does not start with the shebang or does not report the version being released,
and re-downloads the published asset to check it before saying OK.

Also: the Spanish README was missing the click-to-copy section that 1.13.0 added to the English
one.

## 1.13.0

**The values you were going to retype are one click away.**

Until now a single thing could be copied — the session id, with `y`. Everything else in the panel
you had to read and type again, and while sereno is running you cannot even drag-select it: mouse
reporting is on, so the terminal hands the drag to the app instead of selecting text.

Four values now carry a copy zone, marked with an **underline**: the project, the session id, and
the headers of *what you last said* and *what it last replied*. Click one and it goes to the
clipboard, over OSC 52 — no new binary, and it works over SSH.

Two of the four copy something you could **not** read on screen:

- **`project`** shows `docs-site · main` and copies `/Users/you/code/docs-site`. On the 40 history
  sessions of the machine this was written on, the full path was visible **0 times out of 40** — a
  click that copied what was painted would copy exactly what you had just finished reading.
- **the reply header** copies the whole reply, not the part that fitted. **15 of 37** replies were
  painted truncated.

The status line always says what actually landed on the clipboard, so a value that differs from its
label is never a silent surprise. Fields with nothing worth pasting — status, memory, context,
model, spend — are not underlined and do not react.

## 1.12.0

**Sessions that never got a reply stop competing for the top of the list.**

On the machine this was written on, **21 of the 39 history rows** were sessions that had never
received a single reply — and 16 of those were the same one, launched over and over and dying
instantly with `API Error: 401 · Please run /login`, zero tokens each. Because they had just died,
they were the *most recent* rows, so the default sort put them first. More than half of a list whose
whole job is "which one do I go back to" was sessions you cannot go back to.

They now sort below everything, in grey, and the header counts them separately: `3 resumable ·
1 never started` instead of `4 resumable`. Resuming one hands you its startup error and nothing else,
so counting it as resumable was a claim the tool could not keep.

The fact is deliberately narrow: **no reply anywhere in the session consumed a token**. `pico` is the
largest context the session ever held, so a zero can only come from zero real replies — and it is
only read once the transcript has been read whole, because a partial zero means "not known yet".

**A live session is never marked**, even at zero. One you just launched has not answered yet and is
exactly the row you want at the top; there was one 23 seconds old when this was measured.

## 1.11.0

**The context bar remembers where the session has been.**

Compacting resets the number but not the session, and the list was reading backwards because of
it. On the machine this was written on: a session on its 716th turn that had compacted twice drew
**11%** and looked like the freshest of the nine, while an untouched one on turn 246 drew **36%**
and looked heavier. It is the reading you use to decide whether a session takes another task, and
it was pointing the wrong way for four of nine rows.

The peak was already computed (1.8.0) and already survived compacting — it just lived in the panel,
one row at a time, which is no use for comparing nine of them. It is now in the bar: filled cells
in colour are what the session holds now, filled cells in grey are where it has been, hollow cells
it never reached. The percentage is untouched — a peak that inflated it would say the session is
full, which is the opposite of true.

Not drawn when the terminal has no colour: colour is the only thing separating "holds" from "held",
and without it a fuller bar just lies upwards. Not drawn either until the transcript has been read
whole — the peak is `0` until then, and `0` draws nothing.

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

**The demo has session ids now**, one per row and fixed, so the panel and the copy key show
something shaped like the real thing instead of falling back to the row name (`demo-infra-3`).
They are paths that do not exist and nothing opens them. The recording was redone on top of that
and it now walks through the sort by spend and the copy key as well.

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
