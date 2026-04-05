# DTU Thesis Workspace

Public-facing thesis workspace for my DTU Master's thesis on **rolling-horizon last-mile delivery optimization**.

This repository combines three layers of work that were developed together during the project:

- **`22.01paper/`** — the manuscript workspace
- **`22.03controller_line/`** — the retained controller-oriented thesis line
- **`22.04fresh_solver/`** — the newer integrated fresh-solver / Julia-first line

The goal of publishing this repository is to show the thesis as a real research-and-engineering workspace rather than only a final PDF: manuscript, algorithm development, experiment structure, diagnostics, and supporting ops/scripts live together.

## What this repository shows

- rolling-horizon planning under flexible service days and depot resource constraints
- a transition from an earlier retained controller line to a newer integrated solver line
- manuscript writing connected directly to experiment evidence and diagnostic outputs
- practical research operations: build scripts, HPC sync helpers, figure generation, and workspace conventions

## Repository structure

### `22.01paper/`
The active thesis manuscript workspace.

Contains:
- LaTeX manuscript source
- chapter rewrite plans and writing-control documents
- bibliography and frontmatter/backmatter
- thesis figures and figure-generation recipes

### `22.03controller_line/`
The retained earlier technical line.

Contains:
- rolling-horizon experiment code and controller logic
- historical paper-facing experiment structure
- supporting docs, configs, job scripts, and tests

### `22.04fresh_solver/`
The current forward technical workspace.

Contains:
- integrated fresh-solver development
- Julia-first solver code
- OR branch experiment notes and diagnostics
- selected thesis-relevant run outputs and summaries

### Supporting folders

- **`ops/`** — build, sync, and HPC helper scripts
- **`deliverables/`** — exported dashboards / HTML artifacts
- **`references/`** — manuscript snapshots and workflow references
- **`archive/`** — inactive leftovers that should not be treated as live thesis source material

## Suggested reading path

If you want the fastest way to understand the project:

1. read this `README.md`
2. read `WORKSPACE_MAP.md`
3. inspect `22.01paper/README.md`
4. inspect `22.04fresh_solver/README.md`
5. inspect `22.03controller_line/README.md`

## Build

Build the thesis manuscript from the repository root:

```bash
./build_paper.sh
```

This delegates to:

```bash
./ops/build_paper.sh
```

## Notes on the public snapshot

This public repository is a cleaned workspace snapshot.

Excluded from publication:
- local runtime state such as virtual environments and logs
- bulky processed-data/runtime caches that are not needed to understand the structure
- LaTeX build artifacts
- private signature assets
- crash dumps

## Project context

This thesis was carried out at **DTU** in collaboration with **Mover** and is framed as an operational planning problem rather than a purely abstract academic exercise.
