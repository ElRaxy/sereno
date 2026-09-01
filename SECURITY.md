# Security

## Reporting a vulnerability

Open a [private security advisory](https://github.com/ElRaxy/sereno/security/advisories/new).
Please don't file a public issue for anything exploitable.

One person maintains this in the evenings, so expect a first reply within a week.

## What sereno does on your machine

Most of it is reading, but not all of it, so here is the whole list.

**Reads**

- `~/.claude/projects/**/*.jsonl` and the equivalent directories for Codex, Gemini and
  Antigravity. It parses transcripts; it never writes to one.
- `~/.claude/settings.json`, for the context window your model is configured with.

**Writes**

- `~/.claude/warp-sessions/` (override with `SERENO_REGISTRY`). Its own registry of live
  sessions, the archive it moves closed entries into, and a `preferencias.json` holding your
  sort order and the launcher you last chose. Nothing else lives there.
- `~/.warp/launch_configurations/*.yaml`, a launch file for Warp when reopening tabs.
- `~/.sereno/lanzar/lanza-*.sh`, a throwaway script per tab when the tabs go to tmux or
  Terminal.app, which take the command as one string. Outside `/tmp` on purpose: a handover
  briefing carries conversation text, and `/tmp` is readable by every user on the machine.

**Runs**

- `ps` and `tmux` to see what is alive, `open` to hand a launch file to Warp, `defaults` to
  read a Warp setting, `osascript` (macOS) or `notify-send` (Linux) for `--watch` alerts.
- `/bin/sh -c <the session's own command>` when you press ENTER outside Warp. It replaces
  itself with that shell so the session inherits your terminal.
- Nothing else. But note what it does **not** run: the command that reopens a session is
  executed by Warp, tmux or Terminal.app, in an *interactive* shell where your aliases apply.
  That is why the CLI is written into the command as its absolute path (`shutil.which`) and
  never as a bare name — otherwise an alias called `claude` can add flags to a session you
  reopened. On the author's machine it added `--allow-dangerously-skip-permissions`: the launch
  file read `claude --resume <id>` and `ps` read otherwise. `tests/test_binario_no_alias.py`
  fakes the `PATH` and fails if any of the three places that compose a command drops back to
  the bare name.
- The processes you mark with SPACE get killed when you press `x`. Only those.

`tests/test_sin_red.py` walks the source and fails the build if a binary outside that list
shows up, or if anything opens a socket. There is no telemetry, no update check and no
network code of any kind. No secrets and no credentials. There is no config file to edit
either — everything you can set is an environment variable; the `preferencias.json` above is
written by the program, not by you, and deleting it only forgets your last sort order.

## Your session text is on screen

The panel shows the last prompt and the last reply of each session, so a screenshot of
sereno is a screenshot of your work. Before recording or sharing anything, run it with
`SERENO_DEMO=1`, which replaces every session with invented ones.

`--watch` sends a notification through your desktop's notification centre, which on macOS
keeps a history. It sends the session's title and project folder, never a prompt or a reply,
but a title Claude generated for itself does describe what you were working on.

## Supply chain

- Single file, Python standard library only. No dependencies to compromise.
- CI actions are pinned by commit SHA, not by tag, and the workflow token is read-only.
- Releases are built from a tagged commit on `main`. If a download's contents differ from
  the file in the repository at that tag, don't run it and tell me.
- Commits from 2026-08-26 onwards are signed with an SSH key registered to my GitHub account,
  so GitHub marks them Verified. An unsigned or unverified commit on `main` is not mine.
- Releases are immutable: once published, neither the tag nor the assets can be changed.
- `main` takes no direct pushes, mine included. Everything lands through a pull request with
  the six test jobs green, and force-pushes and branch deletion are refused outright.
