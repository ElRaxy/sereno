<div align="center">

# sereno

### Nine agent sessions open. Which one is stuck?

**A terminal UI that tells you what every coding-agent session is _actually_ doing — not just that it exists.**

One Python file · zero dependencies · Claude Code, Codex, Gemini, Antigravity

<br>

[![CI](https://img.shields.io/github/actions/workflow/status/ElRaxy/sereno/ci.yml?style=flat-square&label=ci&labelColor=16161e&color=5fff5f)](https://github.com/ElRaxy/sereno/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ElRaxy/sereno?style=flat-square&labelColor=16161e&color=5fff5f)](https://github.com/ElRaxy/sereno/releases/latest)
[![Python](https://img.shields.io/badge/python-3.8+-00afff?style=flat-square&labelColor=16161e)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-5fff5f?style=flat-square&labelColor=16161e)](#-install)
[![Install](https://img.shields.io/badge/install-one%20file-ffaf00?style=flat-square&labelColor=16161e)](#-install)
[![Licence](https://img.shields.io/badge/licence-MIT-af87ff?style=flat-square&labelColor=16161e)](LICENSE)
[![Stars](https://img.shields.io/github/stars/ElRaxy/sereno?style=flat-square&labelColor=16161e&color=ffaf00)](https://github.com/ElRaxy/sereno/stargazers)

**English** · [Español](README.es.md)

<br>

<img src="docs/demo.gif" alt="sereno running against fake sessions" width="880">

</div>

```bash
curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh
sereno
```

---

## Contents

- [Why](#-why)
- [The four states](#-the-four-states-and-why-theyre-hard)
- [Reading a row](#-reading-a-row)
- [Install](#-install)
- [Use](#-use)
- [Where the data comes from](#-where-the-data-comes-from)
- [What it does, and what it doesn't](#-what-it-does-and-what-it-deliberately-doesnt)
- [Privacy](#-privacy)
- [Requirements](#-requirements)
- [FAQ](#-faq)
- [Configuration](#-configuration)
- [Notes on the source](#-notes-on-the-source)
- [Contributing](#-contributing)
- [Credits](#-credits)

---

## 🌙 Why

A *sereno* was the night watchman who walked Spanish streets until the 1970s, carrying a
lantern and the keys to every door on his round. You slept; he checked. When something was
wrong, he was the one who knew.

Right now you have nine terminal tabs open. Two agents are mid-task. One has been blocked on
its own `pytest` for eleven minutes. One finished twenty minutes ago and is waiting for you.
One is eating 900 MB for a job you abandoned before lunch.

From the outside, all nine look identical. Finding out which is which means clicking through
all nine, reading the last screen of each, and losing your place.

**Session managers tell you the nine exist. `sereno` tells you what they are doing.**

---

## 🔎 The four states, and why they're hard

|  | what it means | why `ps` can't tell you |
|:--|:--|:--|
| 🟢 **writing** | producing an answer right now | — |
| 🟠 **in a command** | it issued a tool call and the result never came back | **this is the one that matters** |
| ⚪ **waiting on you** | it finished, nobody replied | looks identical to "it crashed" |
| ⚫ **stopped, waiting on you** | same, but over six hours ago | these are the ones worth closing |

An agent sitting in a three-minute `Bash` call **writes nothing to its transcript**, so by
file mtime it looks idle — and idle looks abandoned. `sereno` reads the tail of the transcript
and checks whether the last `tool_use` ever got its matching `tool_result`.

That single check is the difference between *"it hung"* and *"it's working, leave it alone"*.

```mermaid
flowchart LR
    T["last 80 lines of the transcript"] --> A{"a tool_use still<br>without its tool_result?"}
    A -->|yes| S1["🟠 in a command"]
    A -->|no| B{"file written to<br>in the last 90 s?"}
    B -->|yes| S2["🟢 writing"]
    B -->|no| C{"idle for<br>under six hours?"}
    C -->|yes| S3["⚪ waiting on you"]
    C -->|no| S4["⚫ stopped"]
    T -.->|"no transcript"| S5["unknown — never guessed"]

    classDef fact fill:#1f2430,stroke:#5c6773,color:#e6e6e6
    classDef ask fill:#2b3242,stroke:#5c6773,color:#e6e6e6
    classDef out fill:#3a3f4b,stroke:#8a8f99,color:#ffffff
    class T fact
    class A,B,C ask
    class S1,S2,S3,S4,S5 out
```

To `ps`, all four are the same live process. The order matters too: **the tool check wins over
"is it writing"**, because a `tool_use` line was itself just written to the file, so both are
true at once and only the second one tells you anything.

> Every state is composed **in code** from typed facts read off the transcript — two booleans
> and a timestamp. No model is asked to summarise anything, so nothing can confidently tell
> you a session is fine when it isn't. When the facts are missing the row says `unknown`
> rather than picking the friendly answer.

---

## 📖 Reading a row

```
 ▎ ◐ Refactor payment webhooks  checkout-api ⎇feat/webhooks      now ▰▰▰▰▱  88% 512 MB
 │ │            │                    │            │               │     │     │     │
 │ │            │                    │            │               │     │     │     └ memory
 │ │            │                    │            │               │     │     └ % of the window
 │ │            │                    │            │               │     └ context used
 │ │            │                    │            │               └ idle time, by age
 │ │            │                    │            └ git branch
 │ │            │                    └ project
 │ │            └ title — the one Claude gave itself, or your /rename
 │ └ ◐ in a command · ● writing · nothing = waiting on you
 └ cursor. Turns yellow when the row is marked.
```

**The title is the last thing to be cut.** Narrow the window and the support columns go first,
in this order: memory, then the project (which narrows before it goes), then the context bar.
The title keeps its width down to about 45 columns, because it is the one thing that tells two
sessions apart. Widening never takes a column away again, so resizing doesn't make the row
jump.

A column with nothing to say takes no space at all: no tmux means no memory column, and a
Codex tab means no context column, rather than eighteen blanks on every line.

The panel on the right shows that session's **last prompt and last reply**, so you can decide
whether to go back to it without opening it — plus the exact context figures (`176k / 200k`)
and the model.

### About that context bar

It answers the question you currently answer by opening the session: *can this one take
another task, or is it about to compact?* The number is read from the transcript — every reply
records what it cost — so nothing is estimated and no API is called.

The **ceiling** is the one thing Claude Code does not write down. A session running the
one-million window still records itself as `claude-opus-5`, exactly like a 200k one. So sereno
works it out in this order, and stops at the first that answers:

1. `SERENO_CTX_MAX`, if you set it.
2. A `[1m]` suffix on the model in the transcript.
3. The `model` in your `~/.claude/settings.json` — where the suffix actually lives today.
4. The context already seen. A session holding 560k is not on a 200k ceiling.

Rule 4 is what keeps the bar honest: the percentage can never read above 100%, and there is a
test that fails if it ever does.

---

## ⚡ Install

There is nothing to install, really. `sereno` is one Python file. Every route below ends with
that same file sitting somewhere on your `PATH`.

**The one-liner**

```bash
curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh
```

**From the Releases page, no piping into a shell**

If you'd rather not pipe a script from the internet into `sh` — and you shouldn't, as a habit —
go to [**Releases**](https://github.com/ElRaxy/sereno/releases/latest), download the `sereno`
asset in your browser, and then:

```bash
chmod +x ~/Downloads/sereno && mv ~/Downloads/sereno ~/.local/bin/
```

Each release ships a `SHA256SUMS` file next to it. To check what you downloaded is what I
published:

```bash
cd ~/Downloads && shasum -a 256 -c SHA256SUMS      # sha256sum -c on Linux
```

**From the repository page**

Open [`sereno`](https://github.com/ElRaxy/sereno/blob/main/sereno) and use GitHub's download
button. It's the same file the installer fetches, at whatever `main` says today.

**With git, if you'd rather follow along**

```bash
git clone https://github.com/ElRaxy/sereno.git && ln -s "$PWD/sereno/sereno" ~/.local/bin/sereno
```

The symlink means `git pull` updates the command.

**Read the installer before running it**

```bash
curl -fsSLo /tmp/install.sh https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh
less /tmp/install.sh && sh /tmp/install.sh
```

It's 32 lines: it checks you have Python 3.8+, downloads one file into `~/.local/bin`, and
tells you if that directory isn't on your `PATH`. Set `SERENO_BIN` to put it elsewhere.

---

Python 3.8+ is the whole dependency list. No venv, no lock file, no supply chain. `scp` it to a
server and it runs there too. To uninstall, delete the file.

> **No Homebrew, no package manager, and that's deliberate.** A formula is a second copy of the
> version number that goes stale the week you forget it. If enough people ask, I'll reconsider —
> [open an issue](https://github.com/ElRaxy/sereno/issues).

---

## 🕹 Use

```bash
sereno            # the picker
sereno --list     # plain list, touches nothing
sereno --json     # the same facts, for your statusline or your scripts
sereno --watch    # sit there and tell you the moment one stops and waits on you
sereno --find "the thing you half remember"
sereno --help
```

### `--find`

For the session you know you had and cannot find. It searches **what was said** — your prompts
and the agent's replies — and prints the matches with enough of a line around them to
recognise, then opens the picker with only those, so `ENTER` puts you back inside.

```bash
sereno --find "webhook idempotency"
sereno --find "webhook idempotency" --all     # everything, not just the 200 most recent
```

Searching the raw files instead would have been three lines shorter and useless. Measured over
506 transcripts here: 287 files contained the word, 25 had it in something a human or the agent
actually said. The rest were `tool_result` dumps — greps, file contents, command output — and
the project's `CLAUDE.md`, which the CLI pastes into **every** session. With those in, any word
from your own project matches everywhere.

### `--watch`

Leave it in a spare pane. It says nothing until a session **stops working** — the transition
from writing (or running a command of its own) to waiting on you. Not "it is idle": most of
them are idle most of the time, and an alert you get every twenty seconds is one you stop
reading.

```bash
sereno --watch              # every 20s
sereno --watch --every 60
```

You get a desktop notification (`osascript` on macOS, `notify-send` on Linux — both already on
your system) and a line on stdout, so it works over SSH and pipes fine. The first pass is
always silent: it only sets the baseline, otherwise starting it would announce everything you
already knew.

`--json` gives you every session with a stable `state`
(`writing` · `in_command` · `waiting` · `stopped` · `unknown`), its context figures, memory and
idle seconds. **It carries no conversation** — no prompt, no reply, nothing that was said. The
picker can show you that because you are looking at your own screen; a pipe cannot, so it
doesn't. A test fails if a field ever sneaks one in.

```bash
sereno --json | jq -r '.sessions[] | select(.state=="waiting") | .title'
sereno --json --all      # add the resumable history, the equivalent of pressing TAB
```

<details>
<summary><strong>Three things worth wiring it into</strong></summary>

<br>

**A shell prompt that says how many are waiting on you.** Cheap enough to run on every prompt,
and silent when the answer is zero:

```bash
sereno_wait() {
  local n
  n=$(sereno --json 2>/dev/null | jq '[.sessions[] | select(.state=="waiting")] | length')
  [ "${n:-0}" -gt 0 ] && printf ' ⏳%s' "$n"
}
PS1='$(sereno_wait) \w $ '
```

**A tmux status bar with the session closest to compacting.** The one you want to know about is
the one running out of window, not the one using the most memory:

```bash
# .tmux.conf
set -g status-right '#(sereno --json | jq -r "[.sessions[] | select(.context_max>0)] \
  | max_by(.context_tokens/.context_max) \
  | \"\(.title[0:24]) \(.context_tokens*100/.context_max | floor)%\"") '
```

**Anything that needs to wait for an agent to finish.** `state` is a closed enum, so this is a
loop and not a guess:

```bash
until [ "$(sereno --json | jq -r '.sessions[] | select(.id=="'"$id"'") | .state')" = waiting ]; do
  sleep 20
done
say "it wants you"
```

Every field is typed and every state comes from that same enum, so nothing here has to parse
prose. `context_max` is `null` when the ceiling is unknown, which is why the tmux line filters
on it first.

</details>

| key | |
|:--|:--|
| `↑` `↓` / `j` `k` | move |
| `ENTER` | open it |
| `SPACE` | mark · `v` a range · `a` all · `i` invert · `d` everything idle over an hour |
| `x` | close the marked ones — asks first, and warns if any is mid-task |
| `/` | filter by title as you type |
| `TAB` | Claude · resumable history · Codex · Gemini · all |
| `?` | everything else |

**The mouse works.** Click to select, double click to open, right click (or the bar on the
left edge) to mark, wheel to scroll. The tabs at the top and the buttons along the bottom are
real buttons.

Nothing drops you out of the picker. Closing four sessions and opening a fifth is one visit,
not five.

### 🎭 Try it without touching your data

```bash
sereno --demo          # or SERENO_DEMO=1 sereno
```

Invented sessions, invented projects. **Use this for anything you publish.** The detail panel
shows real prompts and real replies, so a screenshot of a session manager is an unusually
efficient way to leak a client's work — the first take of the GIF above went out with customer
names in it, which is why demo mode and a test that guards it both exist.

### 🔔 One line when you open a terminal

```bash
# ~/.zshrc or ~/.bashrc
sereno --hook
```

Prints one line when something is running, and absolutely nothing when there isn't.

---

## 💾 Where the data comes from

Claude Code already writes everything, in `~/.claude/projects/<project>/<uuid>.jsonl`: one line
of JSON per event, appended as the session runs. `sereno` reads the **last 80 lines** of at most
40 of those files and derives everything from them. Nothing else exists — no config file, no
daemon, no index, no telemetry, no API call. Install it and it already knows about every session
you have ever run.

| what it reads | what it gets out of it |
|:--|:--|
| the file's mtime | is it writing right now |
| the last `tool_use` / `tool_result` pair | is it stuck inside a command |
| `message.usage` on the last reply | context spent, and the model |
| `cwd`, `gitBranch` | project and branch |
| `aiTitle`, `lastPrompt` | the title and the panel |

That costs **4 ms** for the live sessions and **16 ms** for the whole history, measured against
1,248 transcripts and 3.8 GB. The results are cached by mtime, so a file that hasn't moved isn't
read twice.

Codex, Gemini and Antigravity come from their own history directories and reopen with their own
`resume` command. They are files on disk, not live processes, so `sereno` refuses to "close" them
rather than pretending it did something.

<details>
<summary><strong>Optional: tmux and Warp</strong></summary>

<br>

If your sessions run inside tmux you also get live memory per session, which ones already have a
terminal attached, and the ability to actually kill them. On macOS with Warp, `ENTER` opens a
session in a **new window** instead of taking over the one you're reading.

Both optional. Without them everything works except the memory column — which then takes no space
at all, rather than sitting there empty — and `ENTER` execs into the session in the current
terminal.

</details>

---

## 📊 What it does, and what it deliberately doesn't

Almost everything else in this space **launches and orchestrates** sessions: it starts the agents,
so it knows about them because it made them. `sereno` starts nothing. It reads what the CLIs
already wrote, which is why it sees sessions you opened last month, from a terminal it has never
heard of, on a machine you're SSH'd into.

**It will never:**

- **launch or orchestrate agents.** That's the whole crowded half of this space, and the half
  that has to own your workflow to work at all. Use one of those to spawn a fleet, then use this
  to see what the fleet is doing.
- **write to a transcript, or to anything that belongs to a session.** It kills processes you
  pick, and that's the only destructive thing in it.
- **send anything anywhere.** There is no networking code at all, and a test in CI fails the
  build if any appears.
- **ask a model what it thinks.** Every state is composed in code from typed facts.

What that buys you, concretely:

|  | sereno | launchers and session managers | desktop apps |
|:--|:--:|:--:|:--:|
| Sees sessions it didn't start | ✅ | ❌ | 🟡 |
| Live per-session state | ✅ | ❌ | 🟡 |
| Last prompt + last reply | ✅ | ❌ | 🟡 |
| Context spent per session | ✅ | ❌ | ❌ |
| Works with zero setup | ✅ | needs its launcher | needs install |
| Codex / Gemini too | ✅ | Claude only | Claude only |
| Runs over SSH | ✅ | ✅ | ❌ |
| Dependencies | **none** | tmux | Electron / Swift |

---

## 🔒 Privacy

It reads your prompts and your agent's replies to draw them on your screen. That deserves a
straight answer, not a promise:

**`sereno` has zero networking code.** No `socket`, no `urllib`, no `requests` — the whole
import list is `os, sys, json, re, shlex, shutil, subprocess, time, datetime, pathlib,
unicodedata` and `curses`. Nothing it reads can leave your machine, because there is nothing
in it that can send anything anywhere.

The only external programs it ever runs are `ps` (memory), `tmux` (list and kill sessions),
`open` (hand a session to Warp), `defaults` (read your macOS locale) and — only under
`--watch` — `osascript` / `notify-send` for the desktop alert. No telemetry, no analytics, no
update check, nothing phoning home.

One thing worth saying plainly: a `--watch` alert puts the **session title** into your system's
notification centre, which on a shared or screen-shared machine is a place you may not want it.
The alert carries the title and the project, never the conversation.

`tests/test_sin_red.py` walks the AST on every CI run and fails if a networking import appears,
or if a new external binary shows up that isn't on that list. You don't have to take my word
for it — the test *is* the word.

[`SECURITY.md`](SECURITY.md) has the full list of what it reads, what it writes and what it
runs, and it's where to report anything exploitable.

---

## ✅ Requirements

| | |
|:--|:--|
| **macOS** | works, and it's where it was built |
| **Linux** | works — CI runs the real TUI in a pty on Ubuntu |
| **Windows** | no. `curses` isn't in the Python standard library there. **WSL is fine** |
| **Python** | 3.8 or newer, no packages |
| **Terminal** | any. Uses 256 colours when available, degrades cleanly when not |

---

## 🩺 FAQ

<details>
<summary><strong>I installed it and it shows nothing</strong></summary>

<br>

Check `ls ~/.claude/projects` — that's the only thing it needs. If the folder is empty you
haven't run Claude Code on this machine (or `$HOME` isn't what you think, which happens under
`sudo`).

If it lists sessions but the ones you expected are missing, they're probably in the
**`history`** tab rather than `claude`: anything whose transcript hasn't moved in 90 seconds
counts as resumable, not live. Press `TAB`.

</details>

<details>
<summary><strong>`x` says "history, not processes: nothing to close"</strong></summary>

<br>

Correct, and deliberate. Without tmux there's no process to kill — the session is a file on
disk. `sereno` refuses instead of pretending it did something. Use `ENTER` to resume it, or
delete the transcript yourself if you want it gone.

</details>

<details>
<summary><strong>The memory column is empty</strong></summary>

<br>

Memory is per-process, and it only knows the process if the session runs inside tmux under the
socket it watches (`SERENO_TMUX_SOCK`, default `claude-code`). Everything else still works.

</details>

<details>
<summary><strong>Does it slow anything down? Does it touch my sessions?</strong></summary>

<br>

It reads the **tail** of at most 40 transcripts and caches by mtime — 4 ms for the live ones,
16 ms for the full history, measured against 1.248 transcripts and 3,8 GB. It never writes to a
transcript. The only thing it ever writes is a Warp launch file, and only when you press
`ENTER` on a machine that has Warp.

</details>

<details>
<summary><strong>How do I uninstall it?</strong></summary>

<br>

```bash
rm ~/.local/bin/sereno
```

That's it. It creates no config, no cache and no state directory of its own.

</details>

---

## 🔧 Configuration

There is no config file. Everything is an environment variable, so nothing about it survives
you deleting the script.

| Variable | Default | |
|:--|:--|:--|
| `SERENO_LANG` | your locale | `en` or `es`. On macOS it reads `AppleLocale` |
| `SERENO_DEMO` | off | `1` for invented sessions. Set it before any screenshot |
| `SERENO_CTX_MAX` | worked out | context ceiling in tokens, when the cascade gets it wrong |
| `SERENO_TMUX_SOCK` | `claude-code` | which tmux socket to read |
| `SERENO_REGISTRY` | `~/.claude/warp-sessions` | where the optional launcher registry lives |
| `SERENO_BIN` | `~/.local/bin` | where `install.sh` puts the file |
| `SERENO_DEBUG` | off | `1` stops the picker swallowing a curses error. Use it if it
  exits without saying why |

```bash
# a one-million window, in English, without touching anything permanent
SERENO_CTX_MAX=1000000 SERENO_LANG=en sereno
```

---

## 🧠 Notes on the source

One file, about 3,200 lines, standard library only.

**The comments are in Spanish.** They explain *why* each decision is the way it is, usually
naming the incident that caused it, and translating that would flatten it into generic prose.
The interface is bilingual; the reasoning is in the author's language. Issues and PRs in
English are very welcome.

<details>
<summary><strong>Three decisions worth knowing about</strong></summary>

<br>

**The cursor row changes background, not video.** `A_REVERSE` repaints the whole row white and
throws away the colour of every column — the state, the project, the memory — on the one row
you're actually looking at.

**Mouse events are parsed by hand.** The ncurses that ships with macOS is 6.0 from **2015** and
only speaks the 1988 x11 mouse protocol, where the column travels in a single byte and dies at
column 223. On a wide window, clicks in the right-hand panel land somewhere else entirely.
`sereno` requests SGR and parses it itself, while still accepting `KEY_MOUSE` from a modern
ncurses.

**`agent-*.jsonl` are not sessions.** Claude Code drops its subagent transcripts next to the
real ones — 213 against 1.035 on the machine this was built on. They aren't resumable and have
no title of their own, so the list drowned under twenty copies of the same subagent prompt
until they were filtered out.

</details>

---

Changes between versions are in [CHANGELOG.md](CHANGELOG.md).

## 🤝 Contributing

Issues and pull requests welcome, in English or Spanish. Run the tests before you open one:

```bash
for t in tests/test_*.py; do python3 "$t"; done
```

There are ten, and CI runs all of them on macOS and Ubuntu across Python 3.8, 3.12 and 3.13.
Most guard against something that fails **silently**, which is why they exist at all:

- **`test_demo_aislado.py`** — demo mode must not return a single row that came from real disk.
  Plants a canary in a fake `HOME` and walks every function that reads data.
- **`test_i18n.py`** — every string printed goes through `_()` and has a Spanish entry with the
  same `{placeholders}`. It walks the AST, so a hardcoded phrase is caught too. English is the
  key, so a missing translation never crashes; it just quietly shows the wrong language.
- **`test_sin_red.py`** — no sockets, and no external binary beyond the declared list.
- **`test_contexto.py`** — the context bar can never read above 100%.
- **`test_json_sin_conversacion.py`** — `--json` carries no prompt and no reply.
- Plus the TUI booting in a pty, `--watch` firing on the edge, `--find` reading only speech,
  unknown flags being reported, and a resumed session being followed to its live transcript.

Two house rules:

- **A test you haven't seen fail doesn't count.** Break the code on purpose, watch it go red,
  then fix it. Half the tests here were written that way after the first version passed
  something it shouldn't have.
- **GitHub Actions are pinned by commit SHA**, and the repository enforces it, so a workflow
  edit using `@v4` will be rejected. Dependabot raises the bumps.

Regenerate the demo with `vhs demo.tape` ([vhs](https://github.com/charmbracelet/vhs)) — and
look at the frames before you commit them. `SERENO_DEMO=1` first, always: the panel shows real
prompts.

Anything exploitable goes to [`SECURITY.md`](SECURITY.md), not to a public issue.

---

## 👤 Credits

Built by **[Alex Micó](https://github.com/ElRaxy)**, who had nine Claude Code tabs open at
the time and no idea which one to go back to.

Written with **Claude Code (Opus 5)** as co-author — including the afternoon spent discovering
that macOS ships a 2015 ncurses. Fitting, for a tool whose whole job is watching Claude Code
sessions.

If it saves you one round of clicking through nine tabs, a ⭐ helps other people find it.

---

## 📄 Licence

MIT — see [LICENSE](LICENSE). Do what you want with it.
