<h1 align="center">sereno</h1>

<p align="center">
  See what every coding-agent session on your machine is <em>actually</em> doing.<br>
  One Python file. No dependencies. Works with Claude Code, Codex, Gemini and Antigravity.
</p>

<p align="center">
  <img src="docs/demo.gif" alt="sereno running against fake sessions" width="900">
</p>

## The problem

Nine terminal tabs open. Two agents are mid-task, one has been blocked on its own
`pytest` for eleven minutes, one finished twenty minutes ago and is waiting for you,
and one is eating 900 MB for a job you already abandoned.

Finding out which is which means clicking through all nine.

Session listers will tell you the nine exist. `sereno` tells you what they are doing:

- **writing** — the agent is producing an answer right now
- **in a command** — it issued a tool call and the result has not come back
- **waiting on you** — it finished and nobody has replied
- **stopped, waiting on you** — same, but it has been a while

That distinction is the whole point, and it is not guessable from a process list. An
agent sitting in a three-minute `Bash` call writes nothing to its transcript, so by
mtime alone it looks idle. `sereno` reads the tail of the transcript and checks
whether the last `tool_use` ever got its `tool_result`.

Next to each session you also get its memory, its project and branch, what you last
asked, and what it last answered — so you can decide without opening anything.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh
```

Or just take the file. It is one script and the standard library:

```bash
curl -fsSLo ~/.local/bin/sereno https://raw.githubusercontent.com/ElRaxy/sereno/main/sereno
chmod +x ~/.local/bin/sereno
```

Needs Python 3.8+. That is the entire dependency list.

## Use

```bash
sereno            # the picker
sereno --list     # plain list, touches nothing
sereno --help
```

Arrows or `j`/`k` to move, `SPACE` to mark, `ENTER` to open, `x` to close the marked
ones, `/` to filter, `TAB` to switch between Claude sessions, resumable history, and
the other CLIs. `?` for the rest.

The mouse works too: click to select, double click to open, right click (or the bar on
the left edge) to mark, wheel to scroll, and the tabs and the buttons along the bottom
are clickable.

Nothing you do drops you out of the picker. Closing four sessions and opening a fifth
is one visit, not five.

### Try it without touching your data

```bash
SERENO_DEMO=1 sereno
```

Fake sessions, invented projects. Use this for screenshots and recordings — the detail
panel shows your real prompts and replies, and a demo of a session manager is a very
easy way to publish a client's work by accident. Ask me how I know.

### One line when you open a terminal

```bash
# ~/.zshrc or ~/.bashrc
sereno --hook
```

Prints a single line when something is running, and nothing at all when there isn't.

## Where the data comes from

Everything comes from `~/.claude/projects`, which Claude Code writes on its own. No
configuration, no daemon, nothing to set up.

Codex, Gemini and Antigravity sessions are read from their own history directories and
opened with their own `resume` command. They are history on disk, not live processes,
so `sereno` will refuse to "close" them instead of pretending it did something.

### Optional: tmux and Warp

If your sessions run inside tmux, `sereno` also reports live memory per session, which
of them already has a tab attached, and can actually kill them. On macOS with Warp
installed, `ENTER` opens a session in a **new window** instead of replacing the
terminal you are looking at.

Both are optional. Without them you get everything except the memory column, and
`ENTER` execs into the session in the current terminal.

## Configuration

| Variable | Does what |
|---|---|
| `SERENO_LANG` | `en` or `es`. Defaults to your locale (on macOS, `AppleLocale`). |
| `SERENO_DEMO` | `1` for fake sessions. |
| `SERENO_TMUX_SOCK` | tmux socket to look at. Default `claude-code`. |
| `SERENO_REGISTRY` | Where the optional launcher registry lives. |

## Notes on the source

One file, ~2.000 lines, standard library only — no venv, no lock file, no supply
chain. Copy it to a server over SSH and it runs.

**The comments are in Spanish.** They explain *why* each decision is the way it is,
usually with the incident that caused it, and translating them would flatten that into
generic prose. The interface is bilingual; the reasoning is in the author's language.
Issues and PRs in English are welcome.

A few of those decisions, if you are reading the source:

- The picker highlights the cursor row by changing the **background**, not with
  `A_REVERSE`. Reverse video repaints the whole row white and throws away the colour of
  every column — the status, the project, the memory — on the one row you are looking at.
- Mouse events are parsed by hand. The ncurses that ships with macOS is 6.0 from 2015
  and only speaks the 1988 x11 mouse protocol, where the column travels in a single
  byte and dies at 223. On a wide window, clicks in the right-hand panel land somewhere
  else entirely. `sereno` asks for SGR and parses it itself, while still accepting
  `KEY_MOUSE` from a modern ncurses.
- The verdict is never the model's. Every "is this session working" answer is composed
  in code from typed facts read off the transcript, never from a summary.

## Non-goals

It does not launch sessions, manage worktrees, proxy your API traffic, or count your
tokens. There are good tools for all of that. This one answers a single question, and
answers it fast enough that you'll actually check.

## Licence

MIT. See [LICENSE](LICENSE).
