# Professor Preview Figure Workflow

This folder stores thesis figures used in the professor-preview manuscript build.

## Default policy

Use the following default split:

- **Mermaid + `mmdc`** for architecture diagrams, role-split schematics, flowcharts, pipelines, and other text-heavy box-and-arrow explanatory figures.
- **Matplotlib** for genuine data plots such as curves, bars, scatter plots, and similar quantitative visualizations.

Do **not** hand-position text-heavy architecture boxes in matplotlib unless the user explicitly asks for that approach.

## Current Mermaid-managed figures

These figures are source-controlled as Mermaid files:

- `fig_integrated_architecture.mmd`
- `fig_role_split_schematic.mmd`

Rendered outputs are generated alongside the sources as:

- `.pdf` (preferred for LaTeX / thesis use)
- `.svg` (vector source / inspection / reuse)
- `.png` (preview convenience)

## Current matplotlib-managed figures

These figures are currently generated from `make_professor_preview_figures.py`:

- `fig_west_picking_curve_comparison.*`
- `fig_regime_summary_table.*`

## Regeneration

From the repository root, run:

```bash
./ops/render_mermaid_figures.sh
```

This renders every `.mmd` file in this folder to PDF, SVG, and PNG using:

- config: `mermaid_config.json`
- renderer: `mmdc` from `@mermaid-js/mermaid-cli`

## LaTeX integration preference

For thesis/manuscript usage:

- prefer **PDF** exports in `\includegraphics` because the current XeLaTeX workflow handles PDF robustly and keeps Mermaid diagrams vector-sharp in the compiled thesis
- keep **SVG** exports as the editable/vector inspection output
- keep **PNG** exports as a fallback preview/export format

## Editing guidance for future agents

When a thesis explanatory figure needs structural edits:

1. update the `.mmd` source, not only the rendered image
2. rerun `./ops/render_mermaid_figures.sh`
3. rebuild the thesis PDF if the figure is used in the manuscript
4. avoid switching back to matplotlib for text-heavy box diagrams unless explicitly requested
