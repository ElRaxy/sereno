<h1 align="center">sereno</h1>

<p align="center">
  <strong>Nine agent sessions open. Which one is stuck?</strong><br>
  A terminal UI that tells you what every coding-agent session is <em>actually</em> doing —
  not just that it exists.
</p>

<p align="center">
  <a href="https://github.com/ElRaxy/sereno/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ElRaxy/sereno/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.8+" src="https://img.shields.io/badge/python-3.8%2B-blue">
  <img alt="Dependencies: none" src="https://img.shields.io/badge/dependencies-none-success">
  <img alt="One file" src="https://img.shields.io/badge/install-one%20file-success">
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/licence-MIT-black"></a>
</p>

<p align="center">
  <img src="docs/demo.gif" alt="sereno running against fake sessions" width="900">
</p>

```bash
curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh
sereno
```

---

## The problem

Two agents are mid-task. One has been blocked on its own `pytest` for eleven minutes. One
finished twenty minutes ago and is waiting for you. One is eating 900 MB for a job you
abandoned before lunch.

From the outside all nine look identical. Finding out which is which means clicking through
all nine, reading the last screen of each, and losing your place.

Session managers tell you the nine exist. `sereno` tells you what they are doing.

## The four states, and why they are hard

| | what it means | why you can't get it from `ps` |
|---|---|---|
| **writing** | producing an answer right now | — |
| **in a command** | it issued a tool call and the result never came back | this is the one that matters |
| **waiting on you** | it finished, nobody replied | looks identical to "crashed" |
| **stopped, waiting on you** | same, but a while ago | the ones worth closing |

An agent sitting in a three-minute `Bash` call **writes nothing to its transcript**, so by
file mtime it looks idle — and idle looks abandoned. `sereno` reads the tail of the
transcript and checks whether the last `tool_use` ever got its matching `tool_result`. That
one check is the difference between "it hung" and "it's working".

Every state is composed **in code** from typed facts read off the transcript. No model is
asked to summarise anything, so nothing can confidently tell you a session is fine when it
isn't.

## Reading a row

```
 ▎ Refactor payment webhooks   ◐ checkout-api ⎇feat/webhooks   now   ▰▰▰▰▱  512 MB
 │            │                │       │           │            │       │       │
 │            │                │       │           │            │       │       └ memory
 │            │                │       │           │            │       └ share of the biggest
 │            │                │       │           │            └ idle time, coloured by age
 │            │                │       │           └ git branch
 │            │                │       └ project
 │            │                └ ◐ in a command · ● writing · nothing = waiting on you
 │            └ title (the one Claude gave itself, or /rename)
 └ cursor. Yellow when marked.
```

The right-hand panel shows the same session's **last prompt and last reply**, so you can
decide whether to go back to it without opening it.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh
```

Or take the file — it is one script and the standard library:

```bash
curl -fsSLo ~/.local/bin/sereno https://raw.githubusercontent.com/ElRaxy/sereno/main/sereno
chmod +x ~/.local/bin/sereno
```

Python 3.8+. That is the whole dependency list. No venv, no lock file, no supply chain.
`scp` it to a server and it runs there too.

## Use

```bash
sereno            # the picker
sereno --list     # plain list, touches nothing
sereno --help
```

| key | |
|---|---|
| `↑` `↓` / `j` `k` | move |
| `ENTER` | open it |
| `SPACE` | mark · `v` marks a range · `a` all · `i` invert · `d` everything idle over an hour |
| `x` | close the marked ones (asks first, and warns if any is mid-task) |
| `/` | filter by title as you type |
| `TAB` | Claude · resumable history · Codex · Gemini · all |
| `?` | everything else |

**The mouse works.** Click to select, double click to open, right click (or the bar on the
left edge) to mark, wheel to scroll. The tabs at the top and the buttons along the bottom
are real buttons.

Nothing drops you out of the picker. Closing four sessions and opening a fifth is one
visit, not five.

### Try it without touching your data

```bash
SERENO_DEMO=1 sereno
```

Invented sessions, invented projects. **Use this for anything you publish.** The detail
panel shows real prompts and real replies, so a screenshot of a session manager is an
unusually efficient way to leak a client's work — the first take of the GIF above went out
with customer names in it, which is why the demo mode and a test that guards it both exist.

### One line when you open a terminal

```bash
# ~/.zshrc or ~/.bashrc
sereno --hook
```

Prints one line when something is running, and absolutely nothing when there isn't.

## Where the data comes from

`~/.claude/projects`, which Claude Code writes on its own. No config, no daemon, no
telemetry, nothing to set up — install it and it already knows about every session you have
ever run.

Codex, Gemini and Antigravity sessions come from their own history directories and open
with their own `resume` command. They are files on disk, not live processes, so `sereno`
refuses to "close" them rather than pretending it did something.

### Optional: tmux and Warp

If your sessions run inside tmux, you also get live memory per session, which ones already
have a terminal attached, and the ability to actually kill them. On macOS with Warp,
`ENTER` opens a session in a **new window** instead of taking over the one you are reading.

Both optional. Without them everything works except the memory column, and `ENTER` execs
into the session in the current terminal.

## How it compares

Most tools in this space *launch and orchestrate* sessions. This one **observes** them, and
that is the whole design.

|  | sereno | tmux session managers | desktop apps |
|---|---|---|---|
| Live per-session state | yes | no | some |
| Last prompt + last reply | yes | no | some |
| Works with no setup | yes | needs its own launcher | needs install |
| Codex / Gemini too | yes | Claude only | Claude only |
| Runs over SSH | yes | yes | no |
| Dependencies | none | tmux | Electron / Swift |

If you want something to *spawn* a fleet of agents, use one of those instead — and then use
this to see what the fleet is doing.

## Configuration

| Variable | |
|---|---|
| `SERENO_LANG` | `en` or `es`. Defaults to your locale (on macOS, `AppleLocale`). |
| `SERENO_DEMO` | `1` for fake sessions. |
| `SERENO_TMUX_SOCK` | tmux socket to read. Default `claude-code`. |
| `SERENO_REGISTRY` | where the optional launcher registry lives. |

## Notes on the source

One file, ~2.000 lines, standard library only.

**The comments are in Spanish.** They explain *why* each decision is the way it is, usually
naming the incident that caused it, and translating that would flatten it into generic
prose. The interface is bilingual; the reasoning is in the author's language. Issues and
PRs in English are very welcome.

Three of those decisions, if you go looking:

- **The cursor row changes background, not video.** `A_REVERSE` repaints the whole row white
  and throws away the colour of every column — the state, the project, the memory — on the
  one row you are actually looking at.
- **Mouse events are parsed by hand.** The ncurses that ships with macOS is 6.0 from *2015*
  and only speaks the 1988 x11 mouse protocol, where the column travels in a single byte and
  dies at column 223. On a wide window, clicks in the right-hand panel land somewhere else
  entirely. `sereno` requests SGR and parses it itself, while still accepting `KEY_MOUSE`
  from a modern ncurses.
- **`agent-*.jsonl` are not sessions.** Claude Code drops its subagent transcripts next to
  the real ones — 213 against 1.035 on the machine this was built on. They are not
  resumable and have no title of their own, so the list drowned under twenty copies of the
  same subagent prompt until they were filtered out.

## Contributing

Issues and pull requests welcome, in English or Spanish. Two things the CI will check for
you, and both exist because they fail *silently*:

- `tests/test_demo_aislado.py` — demo mode must not return a single row that came from
  real disk. Plants a canary in a fake `HOME` and walks every function that reads data.
- `tests/test_i18n.py` — every string passed through `_()` has a Spanish entry with the
  same `{placeholders}`. English is the key, so a missing translation doesn't crash; it
  just quietly shows up in the wrong language.

Regenerate the demo with `vhs demo.tape` ([vhs](https://github.com/charmbracelet/vhs)), and
look at the frames before committing them.

## Credits

Built by [Alex Micó](https://github.com/ElRaxy) — with **Claude Code (Opus 5)** as
co-author, pair and, on the mouse protocol, the one who read the terminfo. Fitting for a
tool whose entire job is watching Claude Code sessions.

## Licence

MIT. See [LICENSE](LICENSE).
