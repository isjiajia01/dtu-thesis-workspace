from __future__ import annotations

# NOTE FOR FUTURE AGENTS:
# This script is for quantitative/data-style figures only.
# Use it for plots such as curves, comparisons, tables, bars, and similar
# matplotlib-native outputs.
#
# Do NOT add new thesis architecture diagrams, role-split schematics,
# flowcharts, pipelines, or other text-heavy box-and-arrow explanatory
# figures here unless the user explicitly asks for matplotlib.
# Those figures are Mermaid-managed in this folder as `.mmd` sources and
# should be rendered through:
#     ./ops/render_mermaid_figures.sh
# using `mmdc` + `mermaid_config.json`.

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path('/Users/zhangjiajia/Life-OS/20-29 Study/22 DTU Semester 6')
OUT = ROOT / '22.01paper' / 'Pictures' / 'professor_preview'
DIAG = ROOT / '22.04fresh_solver' / 'results' / 'diagnostics'
RUNS = ROOT / '22.04fresh_solver' / 'results' / 'raw_runs'
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 16,
    'axes.labelsize': 12,
    'figure.facecolor': 'white',
    'axes.facecolor': '#fcfcfd',
    'axes.edgecolor': '#d0d7de',
    'axes.linewidth': 0.8,
    'grid.color': '#d9dee7',
    'grid.alpha': 0.4,
    'savefig.bbox': 'tight',
})

COLORS = {
    'v7': '#5B6CFF',
    'v8': '#F25F5C',
    'v8_1': '#F2A541',
    'v8_2': '#1F9D8B',
    'controller': '#4F46E5',
    'fresh': '#0F766E',
    'accent': '#C2410C',
    'gray': '#475569',
    'light': '#EFF6FF',
}


def save(fig, name: str):
    fig.savefig(OUT / f'{name}.png', dpi=220)
    fig.savefig(OUT / f'{name}.svg')
    plt.close(fig)


def load_json(name: str):
    return json.loads((DIAG / name).read_text())


def load_run(name: str):
    return json.loads((RUNS / name).read_text())


# 1. West picking curve comparison
curve = load_json('west_v7_v8_v8_1_v8_2_picking_curve_compare.json')
all_buckets = sorted({b for rows in curve['top_peaks'].values() for b, _ in rows})
# use csv instead for full curve
import csv
buckets, v7, v8, v81, v82 = [], [], [], [], []
with (DIAG / 'west_v7_v8_v8_1_v8_2_picking_curve_compare.csv').open() as f:
    for r in csv.DictReader(f):
        buckets.append(r['bucket_hhmm'])
        v7.append(float(r['v7_total_picking_over']))
        v8.append(float(r['v8_total_picking_over']))
        v81.append(float(r['v8_1_total_picking_over']))
        v82.append(float(r['v8_2_total_picking_over']))

fig, ax = plt.subplots(figsize=(14, 7.4))
x = list(range(len(buckets)))
ax.plot(x, v7, color=COLORS['v7'], lw=2.8, label='OR-V7 reference')
ax.plot(x, v8, color=COLORS['v8'], lw=2.2, alpha=0.9, label='V8 (over-control)')
ax.plot(x, v81, color=COLORS['v8_1'], lw=2.2, alpha=0.95, label='V8.1')
ax.plot(x, v82, color=COLORS['v8_2'], lw=3.2, label='V8.2 (best trade-off)')
ax.axvspan(buckets.index('05:30'), buckets.index('06:15'), color='#fee2e2', alpha=0.28, zorder=0)
ax.text((buckets.index('05:30') + buckets.index('06:15')) / 2, max(v7) * 1.02,
        'critical morning wave\n05:30–06:15', ha='center', va='bottom', color='#991b1b', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.22', facecolor='white', edgecolor='none', alpha=0.8))
ax.annotate('V7 peak\n1990.4 at 06:00', xy=(buckets.index('06:00'), 1990.4),
            xytext=(buckets.index('07:00'), 1850),
            arrowprops=dict(arrowstyle='->', color=COLORS['v7'], lw=1.5),
            color=COLORS['v7'], fontsize=10)
ax.annotate('V8.2 peak\n1637.1 at 06:00', xy=(buckets.index('06:00'), 1637.08),
            xytext=(buckets.index('07:45'), 1450),
            arrowprops=dict(arrowstyle='->', color=COLORS['v8_2'], lw=1.5),
            color=COLORS['v8_2'], fontsize=10)
ax.set_title('West picking-overload curve\nV8.2 smooths the morning wave without collapsing service', pad=12)
ax.set_ylabel('Aggregated picking overload')
ax.set_xlabel('15-minute bucket')
ax.set_xticks(x[::2])
ax.set_xticklabels(buckets[::2], rotation=45, ha='right')
ax.grid(True, axis='y')
ax.legend(frameon=False, ncol=2, loc='upper right')
ax.spines[['top', 'right']].set_visible(False)
fig.subplots_adjust(top=0.87)
save(fig, 'fig_west_picking_curve_comparison')


# 2. Summary table figure
west_v82 = load_run('west_multiday_or_v8_2_julia.json')
west_v7 = load_run('west_multiday_or_v7_julia.json') if (RUNS / 'west_multiday_or_v7_julia.json').exists() else None
herlev_v82 = load_run('herlev_multiday_or_v8_2_julia.json')
herlev_v7 = load_run('herlev_multiday_or_v7_julia.json')
east_v82 = load_run('east_multiday_or_v8_2_julia.json')
east_v7 = load_run('east_multiday_or_v7_julia.json')

rows = [
    ['West', 'High', '99.93%', '99.41%', '3 → 27', '14901 → 13997', 'Strong gain\nunder high pressure'],
    ['Herlev', 'Medium', '99.14%', '99.52%', '9 → 5', '—', 'Moderate\nservice gain'],
    ['East', 'Low', '100.00%', '99.72%', '0 → 9', '—', 'No free win\nin loose regime'],
]

fig, ax = plt.subplots(figsize=(16.8, 5.8))
ax.axis('off')
col_labels = ['Instance', 'Regime', 'OR-V7 SR', 'V8.2 SR', 'Deadline failures', 'Morning picking over', 'Interpretation']
col_widths = [0.13, 0.13, 0.13, 0.13, 0.13, 0.13, 0.13]
table = ax.table(cellText=rows, colLabels=col_labels, colWidths=col_widths, loc='center', cellLoc='center', colLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(9.2)
table.scale(1.15, 2.35)
for (r, c), cell in table.get_celld().items():
    cell.set_edgecolor('#cbd5e1')
    if r == 0:
        cell.set_facecolor('#E0F2FE')
        cell.set_text_props(weight='bold', color='#0f172a')
    elif r == 1:
        cell.set_facecolor('#F8FAFC')
    elif r == 2:
        cell.set_facecolor('#F0FDF4')
    elif r == 3:
        cell.set_facecolor('#FFF7ED')
ax.set_title('Integrated-solver summary across regimes\nV8.2 helps when pressure is real, not universally', pad=16)
fig.subplots_adjust(top=0.82, bottom=0.06)
save(fig, 'fig_regime_summary_table')


# helper for box diagrams

def rounded_box(
    ax, x, y, w, h, title, body, fc, ec='#cbd5e1', title_color='#0f172a',
    title_size=14, body_size=10.5, title_y=0.18, body_y=0.33, body_linespacing=1.5
):
    patch = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.015,rounding_size=0.03',
                           linewidth=1.2, edgecolor=ec, facecolor=fc)
    ax.add_patch(patch)
    ax.text(x + 0.03*w, y + h - title_y*h, title, fontsize=title_size, fontweight='bold', color=title_color, va='top')
    ax.text(x + 0.03*w, y + h - body_y*h, body, fontsize=body_size, color='#334155', va='top', linespacing=body_linespacing)


def arrow(ax, x1, y1, x2, y2, color='#64748b'):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=16,
                                 linewidth=1.6, color=color))


# 3. 22.03 vs 22.04 role split schematic
fig, ax = plt.subplots(figsize=(14.2, 7.2))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')
rounded_box(
    ax, 0.05, 0.18, 0.38, 0.64,
    '22.03controller_line\nRetained paper-facing backbone',
    '• controller / policy-centered rolling-horizon line\n'
    '• main experiment spine: EXP00, EXP01, Scenario1\n'
    '• clear progression: v2 → v4 → v5 → v6f → v6g\n'
    '• strongest claim guardrails and thesis-safe evidence\n'
    '• best for baseline, pressure, and retained endpoint narrative',
    fc='#EEF2FF', ec='#C7D2FE', title_color=COLORS['controller']
)
rounded_box(
    ax, 0.57, 0.18, 0.38, 0.64,
    '22.04fresh_solver\nIntegrated solver and diagnostic line',
    '• controller + routing + depot-repair architecture\n'
    '• Julia-first fresh solver with bucket-aware diagnostics\n'
    '• identifies morning picking-wave bottlenecks\n'
    '• develops dynamic shadow-price line (V8 → V8.2)\n'
    '• best for architecture, mechanism, and regime analysis',
    fc='#ECFDF5', ec='#A7F3D0', title_color=COLORS['fresh']
)
arrow(ax, 0.43, 0.50, 0.57, 0.50)
ax.text(0.5, 0.56, 'synthesized into', ha='center', color='#475569', fontsize=11)
rounded_box(
    ax, 0.24, 0.015, 0.52, 0.13,
    '22.01paper',
    'The thesis manuscript uses 22.03 as the retained evidence backbone\nand 22.04 as the architecture / diagnostics extension.',
    fc='#FFF7ED', ec='#FED7AA', title_color=COLORS['accent'],
    title_size=13, body_size=9.8, title_y=0.16, body_y=0.48, body_linespacing=1.35
)
ax.set_title('Role split in the thesis\nretained reference line vs integrated-solver line', pad=12)
fig.subplots_adjust(top=0.90, bottom=0.04)
save(fig, 'fig_role_split_schematic')


# 4. Integrated architecture diagram
fig, ax = plt.subplots(figsize=(14.8, 7.8))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')
rounded_box(ax, 0.05, 0.70, 0.90, 0.15,
            'Input state',
            'Visible orders • carryover • customer windows • vehicle capacities • road-network matrices • depot resources',
            fc='#F8FAFC', title_size=13.5, body_size=8.8, title_y=0.20, body_y=0.45)
rounded_box(ax, 0.05, 0.44, 0.25, 0.18,
            '1. Controller',
            'Admission, protection, clipping\nCross-day risk control\nProtected vs risky flex demand',
            fc='#EEF2FF', ec='#C7D2FE', title_color=COLORS['controller'],
            title_size=15, body_size=9.1, title_y=0.22, body_y=0.42, body_linespacing=1.32)
rounded_box(ax, 0.375, 0.44, 0.25, 0.18,
            '2. Routing backend',
            'Daily route construction\nInsertion / trip logic\nDynamic shadow-price guidance',
            fc='#ECFEFF', ec='#A5F3FC', title_color='#155e75',
            title_size=15, body_size=9.1, title_y=0.22, body_y=0.42, body_linespacing=1.32)
rounded_box(ax, 0.70, 0.44, 0.25, 0.18,
            '3. Depot-repair',
            'Bucket diagnostics\nOverload reduction\nShift / rollback / refill',
            fc='#ECFDF5', ec='#A7F3D0', title_color=COLORS['fresh'],
            title_size=15, body_size=9.1, title_y=0.22, body_y=0.42, body_linespacing=1.32)
rounded_box(ax, 0.20, 0.14, 0.60, 0.16,
            'Rolling outputs',
            'Assigned today • deferred events • deadline failures • depot penalty • overload buckets • next-day state',
            fc='#FFF7ED', ec='#FED7AA', title_color=COLORS['accent'],
            title_size=14.5, body_size=8.8, title_y=0.23, body_y=0.47)
arrow(ax, 0.50, 0.70, 0.175, 0.62)
arrow(ax, 0.50, 0.70, 0.50, 0.62)
arrow(ax, 0.50, 0.70, 0.825, 0.62)
arrow(ax, 0.30, 0.53, 0.375, 0.53)
arrow(ax, 0.625, 0.53, 0.70, 0.53)
arrow(ax, 0.825, 0.44, 0.73, 0.30)
arrow(ax, 0.50, 0.44, 0.50, 0.30)
arrow(ax, 0.175, 0.44, 0.27, 0.30)
ax.text(0.50, 0.35, 'daily feasible plan + depot feedback', ha='center', fontsize=10.5, color='#475569')
ax.set_title('Integrated planning architecture used in the fresh-solver line', pad=12)
fig.subplots_adjust(top=0.92)
save(fig, 'fig_integrated_architecture')

print('Generated figures in', OUT)
for p in sorted(OUT.glob('fig_*')):
    print(p.name)
