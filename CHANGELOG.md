# Changelog

## 1.32.0

**46 of the 200 rows in the history were nobody's sessions.**

A skill optimiser launching itself: twenty-two *"Score how well the response satisfies…"* and
twenty-two *"Complete the following task…"*. They took the real ones' place in the list, counted
as work in `--hoy`, and put projects named `skillopt_sleep_claude_ylulwmwr` into `--disk`'s
breakdown. Here, 78 of them in total.

They are recognised by **where they were born**, not by what they say. Their working directory
hangs off the system temp dir (`$TMPDIR`, `/tmp`, `/var/folders`…) — somewhere nobody resumes
anything from, because tomorrow it is gone. Filtering on the title would be guessing, and it would
break with the next version of whatever script launches them.

- Not offered for resuming, and not counted as work in `--hoy`.
- `--disk` still reports what they weigh, on its own line, exactly as it does for subagents: the
  weight is real even when the work isn't yours.
- `--find` skips them **and says so** — a search that stays quiet about what it skipped answers
  "never said" when the truth is "never looked". `--all` looks at them, because `--all` means
  look at everything.

**The price, stated plainly:** a session genuinely started inside `/tmp` no longer shows up. The
rare case gives way to the one that happens every day.

Ten test files stopped using `/tmp/proyecto` as their pretend working directory — under the new
rule that stands for a throwaway session, which is not what those cases mean. Six mutants, all
red, including the one that matters: matching the temp roots by plain prefix instead of by path
segment, which would swallow `/var/folders2`.

## 1.31.0

**`--hoy`: what today added up to, by project.** (`--today` works too.)

`--now` is the snapshot of this instant. `--disk` is the accumulated weight. Neither answers the
question you actually ask at the end of the day — what did I do today, and what is still hanging.

```
Today · since 05:00 · 5 sessions in 4 projects
  first at 10:07, last at 10:42

by project
  VanguardIA                         2     18m ago
  sereno                             1         now

still open
  ● SEO maratelierdeestilo.com and Treatwell  writing            now   35%
  ○ Warp error review                         waiting on you 35m ago   14%
```

**The day starts at five in the morning.** Someone closing at half past one is asking about the
work they just did; a midnight cutoff would answer *"nothing touched today"* exactly when they
look hardest — and that failure reads as a plausible answer, not as an error. `SERENO_JORNADA=7`
moves the hour.

The `mtime` filter runs before anything is opened, so the command stays cheap: out of 877
transcripts here, a normal day touches fewer than twenty. `--hoy --usage` adds replies and active
time per project, and that one does read whole transcripts. Without it those fields are `null`,
never `0`: nobody measured them, and a zero would read as "did no work".

Same split as `--disk`: `jornada()` observes and returns typed facts, `cmd_hoy()` only prints
them. And *still open* reuses the list's own cutoff instead of inventing a second one — a mutant
proved the private threshold was dead code hiding behind `estado_estable`, and two thresholds
would have meant two different answers to the same question.

## 1.30.2

**`--dismiss` did nothing on any machine that had a session open.**

The flag is in `--help` and it discards the registry entries whose process is gone. It lived
**after** the fork in `main()`, so with one session running — which is to say, always — the
program printed the list of live sessions and exited **0 without discarding anything**.

An option that doesn't exist gets reported (`test_flags.py`). This one existed and was
swallowed in silence, which is worse: you have no reason to check.

Discarding an orphan has nothing to do with whether other sessions are alive — an orphan is an
entry whose process is dead — so the flag now answers before the fork, and it says so when
there is nothing to discard instead of announcing that it discarded zero.

The test calls `main()`, not `orphans()`: what was broken was not the function but where it was
written, and a case against the function would have stayed green the whole time the bug was
live. It also runs a real live process whose command line mentions `claude`, because
`alive()` requires that on top of the pid — parking the guard would have tested nothing.

## 1.30.1

**An adversarial audit of 1.22.0 → 1.29.0 found three things the tests were not holding.**

Nothing user-visible changed. What changed is that three claims made by earlier releases are now
actually defended, and one latent crash is closed.

### The CI ran 27 of 44 test files

`ci.yml` listed each test by hand, one `run:` per file — and **not one of the eleven files written
between 1.22.0 and 1.29.0 was ever added**. Seventeen of forty-four never ran, and the twelve
checks per PR were six jobs × two triggers over the same subset. Green the whole time.

A hand-written list is a list you forget. `tests/todos.py` now collects the folder, runs each file
in its own process (they all move `HOME` around) and prints the sentence from each docstring —
which is exactly what the step names used to say. The workflow calls it once and cannot drift.

### A session archived without being opened

*"An orphan that doesn't open is no longer archived as resumed"* (1.27.0) could be undone by
flipping one `if`, with every test green. The decision lived **twice** — once in the picker, once
on the command line — and the test replicated it in its own body rather than calling it, so both
`if True:` and `if False:` survived. The compensating source check anchored on the wrong lines.

There is one copy now, `reanuda()`, and both routes call it. The test calls it too, instead of
reimplementing it, and a case fails if a second copy ever appears.

### The screen could go back to lying about how many tabs opened

`abre_varias` returning the real count is the whole of 1.24.0. Replacing it with `len(pestanas)` —
the bug it fixed — passed all 44 tests: one test measures "no launcher at all", another measures
the opener, nobody measured the link in between propagating the zero. It does now, and `reopen`
is checked to exit 1 without announcing anything.

### And the last binary called bare

`tmux_kill` had `check=False`, which ignores an exit code but does **not** protect against the
binary being absent — that is a `FileNotFoundError`, and inside curses it takes the program with
it. It was the twin of the crash fixed across 1.24–1.27, still standing, protected only by the
fact that without tmux there are no rows to kill. Two lines, and a case that fails without them.

## 1.30.0

**`--watch` now also tells you when a session is running out of context.**

The watcher reported three transitions: a session stopping, two sessions starting to write in
the same place, and one starting to go in circles. All three are about what a session **does**.
The fourth is about what it has left to keep doing it — and it is the only one you answer by
compacting rather than by looking.

```
22:03  ▰ Refactor payment webhooks is at 90% of its context  (strev-api)
```

It fires at **80%** and again at **90%**, and — like the other three — **on the crossing, not on
the state**: half an hour sitting at 92% is one line, not one per poll. If the session compacts,
the level drops on its own and the next climb is news again. A session whose ceiling is not known
says nothing at all: `null` there means *not measured*, and treating it as full would invent an
alert out of a missing number.

```bash
SERENO_CTX_AVISO=70,85 sereno --watch   # your own thresholds
SERENO_CTX_AVISO=0 sereno --watch       # no context alerts at all
```

The decision is a pure function (`contextos_nuevos`), like the other three, for the same reason:
the loop cannot be tested and this can. Six mutants, each turning the case red — including one
that at first did **not**: storing the highest level ever seen instead of the current one would
have silently killed the second alert of any session that compacts and fills up again. It only
showed up once the test ran the actual loop.

## 1.29.0

**Which CLI a session belongs to, and a handover box that remembers.**

### The tab bar was mixing two different things

`claude · historial · codex · gemini · todas`. But **`historial` is not a CLI** — it is Claude
sessions that stopped, a *state*. Having it as a tab put two axes on one bar, and left the real
question unanswered: in the `todas` view **no row said whose it was**.

Now each CLI has a glyph, and it appears **only when the list actually mixes them**:

```
 ✦ claude  ◆ codex  todas    10 en total  ·  ● 1 escribiendo  ·  6 reanudables
 ─────────────────────────────────────────────────────────────────────────────
 ▎ ◐⧉ ✦ Refactor payment webhooks              ahora ▰▰▰▰▱  88%
      ✦ Draft release notes v2.4             hace 7m ▰▰▰▱▱  64%
      ◆ Shrink the docker image              hace 2d
      ◆ Name the new billing events          hace 4d
```

The tab carries its own glyph, so it **is** the legend — no help line nobody reads. In a
single-CLI tab the column disappears and the title gets its two columns back: repeating the same
symbol eight times only says what the active tab already said. `historial` folds into `claude`,
at the bottom, which is where `ordena()` already put it, and its count moved to the header as
*resumable*.

The four glyphs measure **one column** (`east_asian_width` 'N') and none was already in use —
`▪`, the obvious pick for codex, is the *has a tab open* marker. An emoji would take two and
quietly skew the whole table.

**And a copy that had drifted:** the bar computed the CLI list one way and the Tab cycle another —
one looked at `fuente`, the other at the CLI — so Tab stopped on a tab the bar never drew and the
list came out empty. One `clis_presentes()` now, and a test that fails if a second copy appears.

### The handover box

- **Where the windows open** is now part of it: `w` cycles it, the same question `r` asks.
- **It remembers.** Last destination goes to the front, last place stays put. Whoever hands over
  to Codex once hands over to Codex always; starting from the top of the list every time is making
  them type the same thing again.
- **It says what it cannot offer.** With only Codex installed the box showed one option and
  nothing else — no way to find out this works with more CLIs. The others are listed greyed out,
  grouped by **their own reason**, which is not the same one: one is fixed by installing it, the
  other needs checking in its `--help` how a starting prompt is passed, which is why `gemini` is
  not in `ARNESES` and never was an oversight.
- And `sesión(es)` is gone: one and many are two strings, in both languages.

Eleven mutants across the two areas, each turning a case red — including two that at first did
**not**: the box remembering was only tested through its helper, not through the box.

## 1.28.0

**A session you just closed came back a few seconds later, marked as live.**

Reported by Alex: mark several, close them, they close — and seconds later they are in the list
again, as if running.

The list has two sources: what tmux shows, and a sweep of `~/.claude/projects` for whatever tmux
does **not** show. The second one excludes the first. So killing a session took it out of tmux,
which took it out of that exclusion list, and it **walked straight back in from disk**: its
transcript had been touched seconds ago, so `idle` was near zero, so it was drawn as alive. With
the uuid for a name instead of its own, which is why it did not even look like the same row.

What was closed is now written down, and the sweep skips it. Three things about that note:

- **It goes on disk, not in memory.** Reopening the picker is another process, and the fright
  would repeat there.
- **It records the id and the transcript's stem.** A resumed session is not named after its id —
  with only the id, it comes back through the other door. That case is in the test because
  removing the stem passed everything else: in the straightforward case the two are equal and
  distinguish nothing.
- **It expires after `VIVA` seconds**, the same threshold that already drops a quiet session. A
  note that never expired would hide a session that genuinely came back to life.

`--stop-all` and `--stop` write it too: neither goes through `stop_rows`, and without it the bug
survived by those two doors.

The test carries a **positive control** — a session nobody closed still comes out of the sweep.
Without it, breaking the sweep altogether would pass. Four mutants, each turning a case red.

## 1.27.0

**An orphan that did not open was filed away as resumed — and stopped being offered.**

Found by applying, immediately, the lesson 1.26.0 had just written down: **grep the call, not the
function.** Two more copies of the raw `open` were left, both in the orphan flow — the sessions
that survived closing Warp. And in both, the order was backwards:

```
path = write_launch_config(elegidas)
archive(elegidas, "restored")          # first
subprocess.run(["open", ...])          # and then, without looking
```

Archiving an orphan means *this one is dealt with*, and from then on **it is not offered again**.
So an `open` that failed — a Mac without Warp, a Linux where that binary does not even exist —
left them marked as restored without having opened them: not resumed, and gone from the list. Not
a wrong message. Losing them.

Now they are archived **after** opening and only if something opened, in both the picker and the
command line. When nothing opens, nothing is filed, and tomorrow the list still has them.

**There is now exactly one `subprocess.run(["open", …])` in the file**, inside `_abre_en_warp` —
checked with the grep this time, not by eye. The other five have been going one per version since
1.24.0, which is what happens when you fix the function you have in front of you instead of
counting the callers first.

The test watches the source order too, not only the behaviour: its behaviour case has to replicate
the decision, so on its own an inversion in the program would keep it green. Two mutants — filing
before opening, and never filing — each turn a case red.

## 1.26.0

**`r` asks where to open them.**

1.25.0 gave sereno three ways to open several sessions at once and then picked one for you — the
first available. The only way to say otherwise was `SERENO_LANZADOR`, an environment variable,
which is exactly the complaint 1.23.0 made about the handover: *an environment variable is not a
way to offer something*.

```
Abrir 2 sesión(es) en:

· Fix flaky login test
· Migrate CI to reusable workflows

[1] warp  —  una ventana de verdad para cada una
[2] tmux  —  una ventana de tmux para cada una, donde ya estás
[3] terminal  —  una ventana de Terminal.app para cada una

[1-9] abrir ahí    [otra tecla] cancelar
```

Each line says what that launcher actually opens: *tmux* on its own does not tell you whether the
windows are the system's or tmux's. With only one launcher around there is no box — a box with a
single option is just one more keypress.

**And the fix in 1.24.0 never reached the key people actually press.** `r` inside the picker had
its own copy of the raw `open` call — the fourth in the file — so neither the guard that stopped
the Linux crash nor the launcher table went anywhere near it. It reported the tabs it *asked for*,
and on any Linux it still took the program down. That copy is gone: it goes through `abre_varias`
like everything else, and reports what opened.

**One bug caught by the tests, not by reading:** the demo's `ejecutar` is a two-parameter lambda
and the picker now passes three, so `r` in `--demo` raised. It has a default now, and a test
watches the signature.

Five mutants — always the first launcher, `donde` not passed through, a box shown for a single
option, cancel that opens anyway, and the demo lambda back to two parameters — each turn a case
red. And checked in a real pty: mark, press `r`, and the box comes out with its three lines.

## 1.25.0

**Opening several at once stops being a Warp thing — and a macOS thing.**

1.24.0 made `r` and `c` admit they could not do it without Warp. This gives them two more ways,
in preference order:

| | what it opens | needs |
|---|---|---|
| **Warp** | a real window per session | macOS with Warp |
| **tmux** | a tmux window per session, in the session you are already in | being *inside* tmux — **the only one that works off macOS** |
| **Terminal.app** | a Terminal window per session | macOS |

Terminal.app is last on purpose: macOS **restores** its windows on reboot, so a day of handovers
leaves windows coming back at startup. `SERENO_LANZADOR` forces one. iTerm2, kitty and
gnome-terminal are one line each — but none is installed on this machine and none goes in by
guesswork: how you ask a terminal for a window with an order inside gets checked first, the way
these three were.

**The order travels in a script on disk, not inline.** `do script` and `tmux new-window` take the
order as one string, and a handover briefing has newlines, single quotes and double quotes in it:
inline is the same bug that used to break Warp's YAML, in a different suit. The script does three
things, each measured rather than assumed:

- `cd` to the session's directory and **abort** if it is gone — not carry on in `~`;
- `unset TMUX`, because reattaching is `tmux attach`, which inside tmux refuses with *sessions
  should be nested with care* (verified: with `TMUX` set it fails, empty it works);
- **delete itself before the `exec`** — a deleted file is still readable through the descriptor
  `sh` already holds, so everything after the `rm` still runs (verified) and the briefing does not
  stay on disk. It lives in `~/.sereno/lanzar`, `0700`, deliberately not in `/tmp`, which every
  user on the machine can read.

**And the count is the truth now.** `reopen` reports how many windows actually opened, not how
many were asked for, and says so when some did not.

Checked end to end on both new launchers, with a briefing carrying newlines, `it's` and `"raro"`
and accents: it arrives whole, the working directory is the session's, `TMUX` reaches the child
empty, and no script is left behind. Five mutants — no `unset`, a `cd` that does not abort, a
script that does not delete itself, `0755` on the script, and the table reordered — each turn a
case red.

## 1.24.0

**On a machine without Warp, `r` and `c` took the whole program down.**

`open` is a macOS command. On Linux `subprocess.run(["open", ...])` raises
`FileNotFoundError` — and it was called with `check=False`, which only ignores the *exit code*,
not a missing binary. So on any Linux, marking two sessions and pressing `r` crashed sereno from
inside curses. Sereno is published for anyone; this needed no exotic setup, just not being on a
Mac with Warp.

The other half is the same failure without the crash: on **macOS without Warp** nothing raised,
`open warp://…` failed quietly, and the screen still announced *"Reattaching 3 tabs"*. Three tabs
that do not exist.

One `_abre_en_warp()` now makes that call, in the three places that made it, and returns **a
fact** — whether it happened — instead of taking the call for granted. Without Warp it says so,
and says what does work: `ENTER` opens one at a time, on any terminal, and always did.

The test carries a **positive control**: with Warp and with `open`, the same rows *are* reported
open. Without it a blunt `return 1` would pass both of the cases above.

## 1.23.0

**`c` pregunta a dónde va, en vez de coger el primero del PATH.**

Handing a session over opened windows of another CLI on a single keypress, with no confirmation
and without saying which one it was going to: it took whichever came first out of `arneses_disponibles()`.
With one installed nobody notices; with two it decided for you. And the conversation — the last
prompt and the last answer — was asked for with an environment variable, `SERENO_RELEVO=completo`,
which nobody finds without reading the README.

Both now live in the same box, over the list:

```
Entregar 1 sesión(es) a:

· Refactor payment webhooks

[1] codex   [2] claude
[k] incluir la conversación: no

[1-9] entregar    [otra tecla] cancelar
```

The origin CLI is not offered — but only when it is the origin of **every** marked row: with a
mixed selection both appear, because some row can go to each. `k` toggles the conversation and
says, while it is on, that it ends up written to Warp's configuration on disk. Any other key
cancels, which is new: until now `c` had no way back.

The box is composed by `lineas_relevo()`, apart from the drawing, for the reason 1.19.0 learned
the hard way — **curses does not complain when a box does not fit**, so the geometry is checked
on the lines, without a terminal in the middle. And the test double grew a `newwin`: it returned
a plain `0`, so no test could press a key that opened a box. Neither this one nor the close
confirmation was reachable.

**And the same empty-path guard, deduplicated.** `abrir_sesion` had its own copy of the check
1.22.0 fixed — the version that lets `""` through. One `_dir_util()` now decides it in both
places: it does not survive as two.

## 1.22.0

**The handover went one way, and its guard did not hold.**

Three defects in `c`, found by asking what it does for someone who is not me.

`Path("").is_dir()` returns **`True`**: Python reads the empty path as `.`. The guard that
existed to stop a handover starting in the wrong directory therefore let through every row with
no recorded `cwd` — which is every Codex row, they carry `""` — and opened the other CLI wherever
the process happened to be standing, announcing *1 handed over*. It is the exact failure the
guard was written to prevent, passing as a success. The check now asks for an **absolute** path,
so a relative one is out too: it exists relative to the process, not to the session.

**Nothing hands a session to the CLI it is already running under.** A Codex row handed to Codex
opened a blank session and counted it as a handover.

**And it goes both ways now.** `claude` is in the table beside `codex` (`claude [PROMPT]` starts
an interactive session with a seed, checked against its own `--help`), the briefing names the CLI
it comes from instead of always saying *"a Claude Code session"* — false for a Codex row — and
with nothing chosen the destination is whichever available CLI is not the origin. So a Codex
session is handed to Claude without picking anything.

**And a Codex row now knows where it lives.** Its index carries `{id, thread_name,
updated_at}` and nothing else, so every Codex session arrived with an empty directory — which,
once the guard above holds, means none of them could be handed over at all: the other half of the
handover would have shipped implemented and dead. The header of its rollout does carry it, in
`payload.cwd`. Only the rows about to be drawn are opened, and only their first line: **9 of 11
resolved in 7 ms** on this machine, against 699 rollouts on disk. The two without one keep an
empty directory rather than inheriting a neighbour's, and the project column fills in for the
rest.

Ten new cases across `test_relevo.py` and `test_cwd_codex.py`, each checked by mutation: the old
guard, the missing same-CLI filter, the fixed briefing, splitting the uuid on hyphens and sharing
one `cwd` between rows were each put back, and each one turned a case red.

**Checked by opening the window, not by reading the YAML.** A real Codex row was handed over:
Warp opened, `claude` started in `/Users/alex/Desktop/VanguardIA` — the directory read from that
session's rollout — and its transcript's first prompt is the briefing, whole, saying it comes
from a Codex session. Warp reports nothing when a launch does not happen, so the first attempt
was confirmed against a positive control (a trivial configuration that writes a file) before
concluding anything about this one.

## 1.21.0

**Two places where it filled a gap in instead of leaving it empty.**

`--find` looks at the 200 most recent transcripts. There are 601 on this machine, so a plain
search reads a third of them and the header said only *"searching 200 transcripts"* — which reads
as *that is all there is*. It now says how many older ones it skipped and that `--all` includes
them. A "you never said that" which is really "it wasn't in the third I read" is the worst answer
a search can give. On stderr, like the size notice, so a piped run stays clean.

`--list` printed `open for ?` for any session with no tmux entry — every session not launched
through the alias, which the picker reads from `~/.claude/projects`. The panel leaves that field
blank; the list filled it with a question mark. Same fact, two treatments, and the ugly one
asserts the field and pads it with a symbol. It is left out now, and the row no longer trails
whitespace either.

Neither is a crash. Both are the list saying something it does not know.

## 1.20.0

**A session you just interrupted stops calling itself busy.**

1.16.0 taught the state to read `stop_reason`, and made one rule out of it: any later `user` line
reopens the turn. Pressing ESC writes a `user` line, so an interrupted session read as `writing`
for the next ninety seconds — and that is the worst case of the lot, because you interrupt a
session precisely when you are about to type into it.

The CLI marks it two ways, counted over this machine's transcripts: 87 interruptions, **78 with
an `interruptedMessageId` field and 9 with only the English text**. Both are read. The field is
the real signal — typed, and it survives that sentence being reworded or translated; the text
catches the nine that arrive without it.

The two are tested **apart**, with the field case deliberately carrying a text that is not one of
the markers. With both signals in one case, turning off either half of the detector still passed
green — measured, not assumed.

**And `--watch` was verified end to end for the first time**, against real sessions rather than a
unit test: it fired on `lesbainsdeazahara.net imágenes home`, whose turn closed at 14:51:46, at
14:51, and on `BioOnline` (14:52:37) at 14:52. Same minute, inside the polling interval — not the
ninety seconds late it would have been before 1.16.0.

## 1.19.0

**`n`: the `--now` view, without leaving the picker.**

1.17.0 added `--now` — what every live session is running, in one screen — and left it in the
shell. The picker is where you actually are, so getting it meant quitting and typing a command.
Now `n` opens the same screen over the list, and any key closes it.

One composer builds both (`lineas_now()`). Two of them writing the same facts is how a screen and
a terminal end up disagreeing about the same nine sessions, which is the thing this program
exists not to do.

**A bug found by testing it, not by reading it:** in a window under six rows tall the box came
out taller than the screen. It never showed up because **ncurses does not complain** — measured
in a 40-column pty, a `newwin` wider than the terminal returns fine and an `addnstr` past the
edge returns fine too. The box just loses its right edge, silently, forever.

So the geometry now lives in its own function with no curses in it (`caja_now`), and a test
sweeps 9 heights x 8 widths x 5 lengths in milliseconds, checking the box stays inside the screen
and the last line does not land on the bottom border. The on-screen test could not have caught
this; that one runs the real TUI in a pty and checks the screen opens, paints and closes — three
window sizes, because the grid is covered for free by the pure one.

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
