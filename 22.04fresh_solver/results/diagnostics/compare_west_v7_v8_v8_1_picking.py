import csv, json
from collections import defaultdict
from pathlib import Path

root = Path('/Users/zhangjiajia/Life-OS/20-29 Study/22 DTU Semester 6/22.04fresh_solver/results/diagnostics')
files = {
    'v7': root / 'west_or_v7_picking_buckets.csv',
    'v8': root / 'west_or_v8_picking_buckets.csv',
    'v8_1': root / 'west_or_v8_1_picking_buckets.csv',
}

agg = {k: defaultdict(float) for k in files}
peaks = {}
for label, path in files.items():
    with path.open() as f:
        for r in csv.DictReader(f):
            agg[label][r['bucket_hhmm']] += float(r['total_picking_over'])
    peaks[label] = sorted(agg[label].items(), key=lambda kv: kv[1], reverse=True)[:12]

all_buckets = sorted({b for d in agg.values() for b in d.keys()})
out_rows = []
for b in all_buckets:
    out_rows.append({
        'bucket_hhmm': b,
        'v7_total_picking_over': agg['v7'].get(b, 0.0),
        'v8_total_picking_over': agg['v8'].get(b, 0.0),
        'v8_1_total_picking_over': agg['v8_1'].get(b, 0.0),
    })

out_csv = root / 'west_v7_v8_v8_1_picking_curve_compare.csv'
out_json = root / 'west_v7_v8_v8_1_picking_curve_compare.json'
with out_csv.open('w') as f:
    f.write('bucket_hhmm,v7_total_picking_over,v8_total_picking_over,v8_1_total_picking_over\n')
    for r in out_rows:
        f.write(f"{r['bucket_hhmm']},{r['v7_total_picking_over']},{r['v8_total_picking_over']},{r['v8_1_total_picking_over']}\n")

summary = {'top_peaks': peaks}
with out_json.open('w') as f:
    json.dump(summary, f, indent=2)

print(out_csv)
print(out_json)
