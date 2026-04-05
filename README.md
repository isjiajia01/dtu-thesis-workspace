# DTU Semester 6 Thesis Workspace

Unified workspace for the DTU Semester 6 graduation thesis collaboration with Mover.

## Active workspace structure

This repository now has two active technical layers plus a unified paper workspace:

- `22.03controller_line/` — retained earlier technical thesis line and paper-facing experiment workspace
- `22.04fresh_solver/` — current integrated solver workspace for the newer fresh-solver / Julia-first line
- `22.01paper/` — unified paper workspace containing both the active manuscript and shared paper-planning / writing-guidance docs for `22.03controller_line` and `22.04fresh_solver`

Supporting top-level folders:

- `references/` — reference manuscript snapshots and handoff / workflow guidance
- `ops/` — operational scripts for build, sync, and HPC submission/pull workflows
- `deliverables/` — exported shareable artifacts such as HTML dashboards or presentation outputs
- `archive/` — inactive artifacts that should not be treated as live thesis source material

## Folder roles

### `22.03controller_line/`
Use for:
- retained experiment code and earlier thesis line
- configs, scripts, jobs, tests
- paper-facing technical notes and result organization
- legacy-but-still-relevant source material that supports the manuscript narrative

### `22.04fresh_solver/`
Use for:
- current fresh-solver workspace
- Julia-first algorithm development
- benchmark and matrix-backed integrated solver work
- newer architecture / experiment docs and result summaries

This is the current forward technical workspace.

### `22.01paper/`
Use for:
- the active DTU thesis manuscript
- LaTeX chapters, frontmatter/backmatter, bibliography, build scripts
- shared paper-planning docs
- chapter rewrite plans, claim guardrails, experiment writing maps, and figure-build guidance
- writing-control material that applies across both `22.03controller_line` and `22.04fresh_solver`

This is the main writing target.

### `references/`
Use for:
- older manuscript snapshots such as `references/22.01paper_snapshot/`
- handoff / workflow guidance documents
- non-active but still useful contextual material

Do not use `references/` as the default destination for new work.

### `ops/`
Use for:
- manuscript build wrappers
- sync scripts
- HPC pull / push / submit helpers

Operational shell scripts should live here instead of cluttering the repository root.

### `deliverables/`
Use for:
- exported HTML artifacts
- viewable demos / dashboards / presentation outputs
- one-off shareable renderings that would otherwise clutter the root or thesis folders

### `archive/`
Use for:
- crash dumps
- inactive diagnostic leftovers
- stale artifacts that should be preserved but kept out of active source areas

## Runtime-state policy

This repository lives in iCloud-synced storage, so heavy runtime state should stay outside the repository under:

```text
~/thesis-local-state/dtu-sem6/
```

For `22.03controller_line/`, the following paths are externalized and linked back with symlinks:

- `.venv`
- `data/processed`
- `logs`

`22.04fresh_solver/` currently keeps curated benchmark / matrix assets and selected results in-tree, but bulky runtime-only state should still be externalized if it grows large.

Keep code, docs, configs, and manuscript source in the repository.
Keep virtualenvs, disposable processed data caches, logs, and other bulky runtime state in `~/thesis-local-state/dtu-sem6/`.

## Practical placement rules

- Retained 22.03 experiment work -> `22.03controller_line/`
- Current fresh-solver / Julia work -> `22.04fresh_solver/`
- New manuscript writing -> `22.01paper/`
- Shared paper-planning / rewrite-control docs -> `22.01paper/`
- Older paper copies / handoff docs / reference material -> `references/`
- Build / sync / HPC operational scripts -> `ops/`
- Exported HTML / visual artifacts -> `deliverables/`
- Non-active leftovers / dumps -> `archive/`

## Build

Build the active thesis manuscript from the repository root with:

```bash
./build_paper.sh
```

The root script is a thin wrapper that delegates to:

```bash
./ops/build_paper.sh
```

which now builds from:

```bash
./22.01paper/
```

## Notes

- Treat `22.01paper/` as the canonical unified paper workspace.
- Treat `22.04fresh_solver/` as the current forward technical workspace.
- Treat `22.03controller_line/` as retained technical / paper-facing historical support.
- Treat `references/22.01paper_snapshot/` as the manuscript snapshot reference copy.
- Before changing sync or runtime placement behavior, read `WORKSPACE_MAP.md`.
- Before major structural edits, read `AGENTS.md`.
