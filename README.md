<div align="center">

<img src="docs/hero.webp" alt="A night watchman raising a lantern to a wall of terminal windows, four of them lit" width="880">

# sereno

### Nine agent sessions open. Which one is stuck?

**A terminal UI that tells you what every coding-agent session is _actually_ doing — not just that it exists.**

One Python file · zero dependencies · Claude Code, Codex, Gemini, Antigravity

<br>

[![CI](https://img.shields.io/github/actions/workflow/status/ElRaxy/sereno/ci.yml?style=flat-square&label=ci&labelColor=16161e&color=5fff5f)](https://github.com/ElRaxy/sereno/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8+-00afff?style=flat-square&labelColor=16161e)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-5fff5f?style=flat-square&labelColor=16161e)](#-install)
[![Install](https://img.shields.io/badge/install-one%20file-ffaf00?style=flat-square&labelColor=16161e)](#-install)
[![Licence](https://img.shields.io/badge/licence-MIT-af87ff?style=flat-square&labelColor=16161e)](LICENSE)
[![Stars](https://img.shields.io/github/stars/ElRaxy/sereno?style=flat-square&labelColor=16161e&color=ffaf00)](https://github.com/ElRaxy/sereno/stargazers)

**English** · [Español](README.es.md)

</div>

---

<div align="center">
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
- [How it compares](#-how-it-compares)
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
| ⚫ **stopped, waiting on you** | same, but a while ago | these are the ones worth closing |

An agent sitting in a three-minute `Bash` call **writes nothing to its transcript**, so by
file mtime it looks idle — and idle looks abandoned. `sereno` reads the tail of the
transcript and checks whether the last `tool_use` ever got its matching `tool_result`.

That single check is the difference between *"it hung"* and *"it's working, leave it alone"*.

> Every state is composed **in code** from typed facts read off the transcript. No model is
> asked to summarise anything, so nothing can confidently tell you a session is fine when it
> isn't.

---

## 📖 Reading a row

```
 ▎ Refactor payment webhooks   ◐ checkout-api ⎇feat/webhooks   now   ▰▰▰▰▱  512 MB
 │            │                │       │           │            │       │       │
 │            │                │       │           │            │       │       └ memory
 │            │                │       │           │            │       └ share of the biggest
 │            │                │       │           │            └ idle time, coloured by age
 │            │                │       │           └ git branch
 │            │                │       └ project
 │            │                └ ◐ in a command · ● writing · nothing = waiting on you
 │            └ title — the one Claude gave itself, or your /rename
 └ cursor. Turns yellow when the row is marked.
```

The panel on the right shows that session's **last prompt and last reply**, so you can decide
whether to go back to it without opening it.

---

## ⚡ Install

```bash
curl -fsSL https://raw.githubusercontent.com/ElRaxy/sereno/main/install.sh | sh
```

Or just take the file — it's one script and the standard library:

```bash
curl -fsSLo ~/.local/bin/sereno https://raw.githubusercontent.com/ElRaxy/sereno/main/sereno
chmod +x ~/.local/bin/sereno
```

Python 3.8+. That's the whole dependency list. No venv, no lock file, no supply chain.
`scp` it to a server and it runs there too.

---

## 🕹 Use

```bash
sereno            # the picker
sereno --list     # plain list, touches nothing
sereno --help
```

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
SERENO_DEMO=1 sereno
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

`~/.claude/projects`, which Claude Code writes on its own. No config, no daemon, no telemetry,
nothing to set up — install it and it already knows about every session you have ever run.

Codex, Gemini and Antigravity sessions come from their own history directories and open with
their own `resume` command. They are files on disk, not live processes, so `sereno` refuses to
"close" them rather than pretending it did something.

<details>
<summary><strong>Optional: tmux and Warp</strong></summary>

<br>

If your sessions run inside tmux you also get live memory per session, which ones already have
a terminal attached, and the ability to actually kill them. On macOS with Warp, `ENTER` opens a
session in a **new window** instead of taking over the one you're reading.

Both optional. Without them everything works except the memory column, and `ENTER` execs into
the session in the current terminal.

</details>

---

## 📊 How it compares

Most tools in this space **launch and orchestrate** sessions. This one **watches** them, and
that's the whole design.

|  | sereno | tmux session managers | desktop apps |
|:--|:--:|:--:|:--:|
| Live per-session state | ✅ | ❌ | 🟡 |
| Last prompt + last reply | ✅ | ❌ | 🟡 |
| Works with zero setup | ✅ | needs its launcher | needs install |
| Codex / Gemini too | ✅ | Claude only | Claude only |
| Runs over SSH | ✅ | ✅ | ❌ |
| Dependencies | **none** | tmux | Electron / Swift |

If you want something to *spawn* a fleet of agents, use one of those — and then use this to
see what the fleet is doing.

---

## 🔧 Configuration

| Variable | |
|:--|:--|
| `SERENO_LANG` | `en` or `es`. Defaults to your locale (on macOS, `AppleLocale`) |
| `SERENO_DEMO` | `1` for fake sessions |
| `SERENO_TMUX_SOCK` | tmux socket to read. Default `claude-code` |
| `SERENO_REGISTRY` | where the optional launcher registry lives |

---

## 🧠 Notes on the source

One file, ~2.000 lines, standard library only.

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

## 🤝 Contributing

Issues and pull requests welcome, in English or Spanish. Two things CI checks for you, and both
exist because they fail **silently**:

- **`tests/test_demo_aislado.py`** — demo mode must not return a single row that came from real
  disk. Plants a canary in a fake `HOME` and walks every function that reads data.
- **`tests/test_i18n.py`** — every string passed through `_()` has a Spanish entry with the same
  `{placeholders}`. English is the key, so a missing translation doesn't crash; it just quietly
  shows up in the wrong language.

Regenerate the demo with `vhs demo.tape` ([vhs](https://github.com/charmbracelet/vhs)) — and
look at the frames before you commit them.

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
