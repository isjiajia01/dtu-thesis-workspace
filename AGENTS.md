# Thesis Workspace AGENTS Guide

This repository is the unified DTU Semester 6 thesis workspace.

There should remain one canonical workspace guide at:

- `AGENTS.md`

Do not create extra per-folder `AGENTS.md` files unless explicitly asked.

## Mandatory startup reading

Before making meaningful changes in this workspace, read these files in order:

1. `AGENTS.md`
2. `WORKSPACE_MAP.md`
3. `README.md`
4. `references/DTU_HPC_NO_BRAINER.md`
5. `references/DROID_AI_WORKSPACE_GUIDE.md`
6. `references/DROID_AI_ALGORITHM_HANDOFF.md`

## Current workspace interpretation

Treat the repository as one thesis workspace with:

- `22.03controller_line/` = retained earlier technical / paper-facing thesis line
- `22.04fresh_solver/` = current fresh-solver / integrated-solver workspace
- `22.01paper/` = unified final manuscript + shared paper-planning / rewrite-guidance workspace for both 22.03 and 22.04
- `references/22.01paper_snapshot/` = older manuscript snapshot kept only as reference
- `ops/` = build / sync / HPC operational scripts
- `deliverables/` = exported artifacts
- `archive/` = inactive artifacts / crash dumps / leftovers

`22.02thesis/` has been intentionally removed from the workspace and should not be reintroduced unless the user explicitly asks for it.

## Folder roles

### `22.03controller_line/`
Use for:
- retained experiment code
- paper-facing result organization
- earlier thesis-line technical notes
- legacy-but-still-useful evidence support

### `22.04fresh_solver/`
Use for:
- current fresh-solver development
- Julia-first solver work
- benchmark / matrix-backed integrated planning experiments
- newer architecture docs, experiments, and result summaries

This is the default forward technical workspace.

### `22.01paper/`
Use for:
- active LaTeX manuscript work
- chapter writing
- bibliography / frontmatter / figures integrated into the final thesis
- shared paper-planning docs
- chapter rewrite plans
- claim guardrails
- experiment-writing maps and figure recipes
- writing-control material shared by both `22.03controller_line` and `22.04fresh_solver`

This is the canonical final writing target.

### `references/`
Use for:
- manuscript backup / older snapshot / comparison source
- handoff docs
- workflow guidance docs

Do not silently treat it as an active work destination.

### `ops/`
Use for:
- build wrappers
- sync scripts
- HPC submission / retrieval helpers

Operational scripts should prefer this folder instead of the repository root.

### `deliverables/`
Use for:
- exported HTML
- demos
- presentation-style or dashboard-style outputs
- other shareable rendered artifacts

### `archive/`
Use for:
- crash dumps
- stale diagnostics
- inactive leftovers that should be preserved but removed from active work areas

## Runtime-state rules

This repository sits in iCloud-synced storage.
Heavy runtime state should live outside the repository under:

```text
~/thesis-local-state/dtu-sem6/
```

For `22.03controller_line/`, these paths should stay externalized as symlinks into local runtime state:

- `.venv`
- `data/processed`
- `logs`

For `22.04fresh_solver/`, curated benchmark / matrix assets and selected thesis-relevant result outputs may stay in-tree, but bulky runtime-only outputs should still be externalized if they grow large.

## Practical task routing

### If the task is about retained 22.03 experiments or paper-facing historical evidence
Work in `22.03controller_line/`.

### If the task is about current fresh-solver / Julia integrated solver work
Work in `22.04fresh_solver/`.

### If the task is about thesis prose / LaTeX manuscript or shared paper-planning / rewrite-control guidance
Work in `22.01paper/`.

### If the task needs to recover or compare against an older manuscript copy or read handoff docs
Inspect `references/`.

### If the task is about build / sync / HPC operations
Inspect `ops/`.

### If the task produces exported view artifacts
Place them in `deliverables/`.

### If the task is cleanup
Prefer:
- removing caches
- deleting duplicate `* 2` copies
- externalizing bulky runtime state
- moving stale artifacts into `archive/` or `deliverables/`

Be conservative with source deletion unless the user explicitly requests it.

## Root cleanliness rules

- Keep the repository root readable.
- Avoid leaving ad hoc exports at the root.
- Avoid leaving bulky runtime directories inside the synced tree.
- Prefer `deliverables/` for render outputs and `archive/` for inactive residue.
- Prefer `ops/` for operational shell scripts.
- Active work should mainly live under `22.03controller_line/`, `22.04fresh_solver/`, and `22.01paper/`.

## Figure-generation rule for thesis diagrams

For thesis architecture diagrams, role-split schematics, flowcharts, pipeline diagrams, and other box-and-arrow explanatory figures, do **not** hand-position text in matplotlib unless the user explicitly asks for that approach.

Default policy:

- Use Mermaid source files (`.mmd`) plus `mermaid-cli` (`mmdc`) as the default generation path.
- Store Mermaid figure sources next to the rendered thesis assets, e.g. under `22.01paper/Pictures/...`.
- Prefer PDF output for LaTeX/manuscript integration in the current XeLaTeX thesis workflow; SVG may be kept as vector source/inspection output and PNG as a convenience preview.
- Keep the Mermaid config file with the figure sources so later agents can regenerate figures consistently.
- Reserve matplotlib primarily for genuine data plots (curves, bars, scatter, heatmaps), not text-heavy architecture boxes.

Current local tool status:

- `mmdc` is installed globally via `@mermaid-js/mermaid-cli` and should be preferred for these thesis diagrams.

## Documentation maintenance rule

Update `AGENTS.md`, `README.md`, and `WORKSPACE_MAP.md` together whenever any of these change:

- active folder roles
- manuscript target
- runtime-state placement policy
- root cleanup / placement conventions
- major structural interpretation of the workspace

Do not leave these three files out of sync.

## Canonical summary

If a future agent needs the short version, use this:

This repository is the DTU Semester 6 thesis workspace. `22.03controller_line/` is the retained earlier paper-facing technical line, `22.04fresh_solver/` is the current fresh-solver workspace, `22.01paper/` is the unified final manuscript plus shared paper-planning folder for both 22.03 and 22.04, `references/22.01paper_snapshot/` is the older manuscript snapshot kept for reference, `ops/` stores build / sync / HPC operation scripts, `deliverables/` stores exported shareable artifacts, and `archive/` stores inactive leftovers. Heavy runtime state for `22.03controller_line/` should stay outside the synced repository under `~/thesis-local-state/dtu-sem6/`, while curated 22.04 benchmarks / matrices may remain in-tree.
