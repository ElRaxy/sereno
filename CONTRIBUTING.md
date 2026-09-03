# Contributing to sereno

Issues and pull requests are welcome, in English or Spanish. This file is the short version; the
reasoning behind each rule lives in the README ([English](README.md#-contributing) ·
[Español](README.es.md#-contribuir)).

## Before you open anything

```bash
python3 tests/todos.py
```

That is the same entry point CI uses. It collects the whole `tests/` folder, prints a line per
file and ends with the count — there is no hand-written list to keep in sync. Everything must be
green before a pull request is opened.

Requirements: Python 3.8 or newer, and nothing else. Sereno is one file and it stays that way —
**a pull request that adds a dependency will be declined**, however small the dependency is.

## The one rule that is not obvious

**A test you haven't seen fail doesn't count.** Break the code on purpose, watch the test go red,
then fix it. Half the tests here exist because the first version of them passed something it
shouldn't have.

Since 1.33.0 that ritual is itself a test: `tests/test_mutantes.py` breaks one hundred and forty-seven real guards,
one at a time, on a copy of the tree, and fails if any mutant survives — or if an anchor no longer
matches, which means the catalogue went stale and the entry has to be rewritten rather than
quietly skipped. If you add a guard worth keeping, add its mutant.

## House rules

- **`main` is protected.** Work on a branch, open a pull request, let the twelve checks run
  (macOS and Ubuntu × Python 3.8, 3.12, 3.13), and merge by squash. Commits must be signed.
- **Commit messages** follow Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`…).
- **GitHub Actions are pinned by commit SHA** and the repository enforces it — a workflow edit
  using `@v4` will be rejected. Dependabot raises the bumps.
- **Both READMEs move together.** `README.md` and `README.es.md` are kept in step by
  `tests/test_readmes_a_la_par.py`; a section added to one has to be added to the other.
- **Every string the user sees goes through `_()`**, with its Spanish entry in `TEXTOS["es"]` and
  the same `{placeholders}`. `tests/test_i18n.py` walks the AST, so a hardcoded phrase is caught.
  Singular and plural are two separate strings.
- **Releases go through `./release.sh <version>`**, never by hand.

## On AI-assisted code

Sereno is written with Claude Code, and its author says so up front rather than being asked. That
is also why the harness above exists: seventy-two tests, one hundred and forty-seven mutants and a full run on
every pull request are what make a claim about this code checkable by someone who did not write
it. Contributions written the same way are welcome under exactly the same bar — the tests do not
care who typed the line, and neither does the review.

## Reporting a security issue

Not here. See [SECURITY.md](SECURITY.md).
