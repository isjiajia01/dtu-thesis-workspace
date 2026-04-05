# DTU Semester 6 Workspace Map

This workspace is split between an iCloud-synced source tree and a local non-synced runtime-state tree.

## Canonical synced workspace

Repository root:

```text
/Users/zhangjiajia/Life-OS/20-29 Study/22 DTU Semester 6
```

Use the synced repository for:
- source code
- thesis writing
- configs and job scripts
- curated benchmark / matrix assets
- small exported artifacts
- workflow documentation

## Canonical local runtime-state root

```text
~/thesis-local-state/dtu-sem6
```

Use the local runtime tree for:
- virtual environments
- logs
- large temporary outputs
- heavyweight runtime caches
- HPC pull overflow and disposable experiment artifacts

## Root folder roles

### Active
- `22.03controller_line/` — retained paper-facing thesis line
- `22.04fresh_solver/` — current fresh-solver / integrated-solver workspace
- `22.01paper/` — unified manuscript + paper-planning workspace for both 22.03 and 22.04

### Reference
- `references/22.01paper_snapshot/` — older manuscript snapshot kept as reference only
- `references/*.md` — handoff / workflow reference documents

### Support
- `ops/` — build, sync, and HPC operational scripts
- `deliverables/` — exported HTML and similar shareable outputs
- `archive/` — inactive artifacts such as crash dumps

## Externalized runtime paths

### `22.03controller_line/`
These repository paths should remain symlinks into local runtime state:

- `.venv` -> `~/thesis-local-state/dtu-sem6/22.03controller_line/.venv`
- `data/processed` -> `~/thesis-local-state/dtu-sem6/22.03controller_line/data/processed`
- `logs` -> `~/thesis-local-state/dtu-sem6/22.03controller_line/logs`

### `22.04fresh_solver/`
- curated `data/processed/benchmarks/` and `data/processed/matrices/` are intentionally kept in-tree
- curated `results/` may stay in-tree when they are thesis-relevant summaries / baselines
- large rerun outputs, disposable caches, or bulky runtime state should still move to `~/thesis-local-state/dtu-sem6/22.04fresh_solver/` if they grow beyond convenient repository size

## Placement rules

- If it is retained 22.03 experiment logic, paper-facing evidence structure, or legacy thesis support code: put it in `22.03controller_line/`.
- If it is the newer fresh-solver / Julia-first integrated solver work: put it in `22.04fresh_solver/`.
- If it is final manuscript prose, LaTeX structure, or shared paper-planning / rewrite-control material serving both 22.03 and 22.04: put it in `22.01paper/`.
- If it is an older manuscript copy or workflow / handoff reference: keep it under `references/`.
- If it is a build / sync / HPC operation script: keep it under `ops/`.
- If it is an exported HTML artifact or shareable rendered file: put it in `deliverables/`.
- If it is inactive clutter or diagnostic residue that should still be preserved: put it in `archive/`.
- If it is bulky runtime-only state: keep it under `~/thesis-local-state/dtu-sem6/`.

## Sync policy

Default root sync scripts should keep the repository source-focused while allowing curated in-tree assets for `22.04fresh_solver`.

Primary operation scripts now live under:

```text
ops/
```

Examples:

```bash
./ops/local_sync_to_hpc.sh
./ops/hpc_sync_to_local.sh
```

If a pull contains large non-source outputs, prefer placing them under:

```text
~/thesis-local-state/dtu-sem6/hpc-pulls/
```

and summarize the useful findings back into the repository.

## Cleanup policy

- Do not leave `.venv`, disposable processed-data caches, or logs as real directories inside the synced repository when they are meant to be local runtime state.
- Do not leave duplicate `* 2` Finder-style copies in active folders.
- Keep root-level exported artifacts out of the repository root; move them into `deliverables/` or `archive/` as appropriate.
- Keep the root readable: active work should primarily appear under `22.03controller_line/`, `22.04fresh_solver/`, `22.01paper/`, `references/`, and `ops/`.
