# 22.01paper Manuscript Workspace Notes

`22.01paper/` is now the **main thesis manuscript workspace** for the DTU Semester 6 thesis.

It combines two roles in one place:

1. the actual LaTeX manuscript source (`main.tex`, `Frontmatter/`, `Chapters/`, `Backmatter/`, `bibliography.bib`), and
2. the writing-control documents that keep the thesis aligned with the retained `22.03controller_line` experiment story.

So this folder should no longer be understood as an old side paper folder. It is the unified place where the thesis is written, structured, and kept claim-safe.

---

## Purpose of this folder

`22.01paper/` exists to turn the broader research program into a coherent, defendable graduation thesis.

It serves four purposes:

1. to host the actual manuscript source,
2. to preserve the final experiment-to-writing mapping,
3. to prevent thesis claims from drifting away from retained evidence,
4. to keep chapter planning, bibliography, figures, and appendices under one roof.

At the workspace level, the role split is:

- `22.03controller_line` = retained controller-centered experiment line and paper-facing evidence backbone,
- `22.04fresh_solver` = current fresh-solver / integrated-solver research line,
- `22.01paper` = unified graduation thesis manuscript and writing-control workspace.

---

## What is kept here

This folder keeps both manuscript assets and writing-control assets.

### Manuscript-side assets
- `main.tex`
- `Frontmatter/`
- `Chapters/`
- `Backmatter/`
- `Setup/`
- `Pictures/`
- `bibliography.bib`

### Figure-generation policy
For thesis figures inside `22.01paper/`:

- use **Mermaid + `mmdc`** by default for architecture diagrams, flowcharts, role-split schematics, and other text-heavy box-and-arrow explanatory figures
- use **matplotlib** mainly for genuine quantitative/data plots
- prefer Mermaid source files (`.mmd`) plus rendered PDF outputs for manuscript-grade explanatory diagrams in the current XeLaTeX workflow
- keep SVG alongside PDF as vector source/inspection output
- when updating Mermaid-managed figures under `Pictures/professor_preview/`, regenerate them with `./ops/render_mermaid_figures.sh`

### Writing-control assets
- `CHAPTER_REWRITE_PLAN.md`
- `CLAIM_GUARDRAILS.md`
- `FIGURE_BUILD_RECIPES.md`
- `THESIS_EXPERIMENT_WRITING_MAP.md`
- related planning / rewrite notes

### Why these Markdown files matter

#### `CHAPTER_REWRITE_PLAN.md`
Use this as the **rewrite sequence and chapter priority guide**.

It explains:
- which experiment lines are still in scope,
- what order the results should be written in,
- how the final story should progress from baseline to final controller.

#### `CLAIM_GUARDRAILS.md`
Use this as the **claim boundary document**.

It tells future writers and agents:
- what is safe to claim,
- what is not safe to claim,
- which controller versions are mainline,
- which versions are only counterexamples or exploratory follow-ups.

#### `FIGURE_BUILD_RECIPES.md`
Use this as the **figure construction reference**.

It should guide:
- which figures belong in the thesis,
- what inputs they require,
- how figures map to the retained experiment story.

#### `THESIS_EXPERIMENT_WRITING_MAP.md`
Use this as the **main evidence-to-chapter map**.

It connects:
- experiment names,
- output paths,
- chapter roles,
- final ranking logic,
- the retained controller progression.

This is one of the most important writing-control files in the thesis workspace.

---

## How this folder should be used

When writing the final thesis in `22.01paper/`, use this folder as follows:

### 1. Use `22.03controller_line` for the retained experimental storyline
The final paper-facing experiment backbone should come from the retained `22.03controller_line` line:

- `EXP00`
- `EXP01`
- `EXP01 / Scenario1` controller progression:
  - `v2`
  - `v4`
  - `v5`
  - `v6f`
  - `v6g`

### 2. Use broader earlier material for depth, not for the final result spine
Broader pre-`22.03controller_line` material should support:

- problem richness,
- formal formulation,
- data semantics,
- broader method discussion,
- appendix-level exact or matheuristic extensions.

But the final result narrative should remain anchored in `22.03controller_line`, while architecture-side or solver-side discussion can selectively draw from `22.04fresh_solver` where appropriate.

### 3. Use `22.04fresh_solver` selectively for newer solver-side insights
`22.04fresh_solver` should mainly support:

- integrated solver architecture discussion,
- depot-aware mechanism analysis,
- bucket-level diagnostics,
- OR / shadow-price follow-up discussion,
- careful comparison of newer solver-side findings that are useful for the thesis.

It should not automatically replace the retained `22.03controller_line` writing backbone.

### 4. Use this folder to keep the thesis story consistent
Before changing thesis claims, chapter structure, or figure priorities, check whether the change also requires updates to:

- retained experiment mapping,
- claim guardrails,
- figure recipes,
- chapter rewrite sequencing,
- bibliography and manuscript structure.

---

## Recommended role of each repository in the final thesis

### `22.03controller_line`
Best used for:
- retained experiment scope,
- final controller line,
- final claim discipline,
- final paper-facing results structure,
- final writing order for the retained experimental story.

### `22.04fresh_solver`
Best used for:
- the current integrated solver architecture,
- fresh-solver implementation and diagnostics,
- depot-coupled solving discussion,
- OR / shadow-price mechanism exploration,
- newer solver-side evidence and limitations.

### `22.01paper`
Best used for:
- the actual DTU thesis manuscript,
- frontmatter and backmatter,
- chapter text,
- final bibliography,
- final figures and appendices,
- rewrite planning and claim control.

---

## Writing principle

The thesis should **not** read like two unrelated projects.

Instead, it should read as one continuous research program:

1. a broad rich rolling-horizon delivery problem is formulated,
2. several methodological directions are explored,
3. the work narrows into a retained controller-centered thesis line,
4. newer solver-side work sharpens architecture and diagnostic understanding,
5. the final graduation thesis is written around a disciplined, unified story.

`22.01paper/` exists to make that unified story explicit and writable.

---

## Maintenance rule

If the retained thesis storyline changes, this folder must be updated immediately.

In practice, that means keeping the writing-control documents aligned with:

- the current final controller version,
- the current retained experiments,
- the current writing-safe claims,
- the current figure plan,
- the current chapter ordering,
- and the actual LaTeX manuscript structure.

If a document here is outdated, it becomes actively harmful because it can mislead later writing or automated assistance.

---

## Status

This folder is now the **main thesis manuscript workspace**.

Its value is twofold:
- it preserves the retained `22.03controller_line` paper-facing logic and evidence discipline,
- and it provides the actual manuscript environment in which the thesis is being rewritten.

Both roles need to stay aligned.