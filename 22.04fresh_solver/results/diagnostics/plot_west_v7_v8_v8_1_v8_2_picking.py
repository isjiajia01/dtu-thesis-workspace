import csv
from pathlib import Path
import matplotlib.pyplot as plt

root = Path('/Users/zhangjiajia/Life-OS/20-29 Study/22 DTU Semester 6/22.04fresh_solver/results/diagnostics')
curve_csv = root / 'west_v7_v8_v8_1_v8_2_picking_curve_compare.csv'
out_png = root / 'west_v7_v8_v8_1_v8_2_picking_curve_compare.png'

buckets = []
v7 = []
v8 = []
v81 = []
v82 = []
with curve_csv.open() as f:
    for r in csv.DictReader(f):
        buckets.append(r['bucket_hhmm'])
        v7.append(float(r['v7_total_picking_over']))
        v8.append(float(r['v8_total_picking_over']))
        v81.append(float(r['v8_1_total_picking_over']))
        v82.append(float(r['v8_2_total_picking_over']))

x = list(range(len(buckets)))
plt.figure(figsize=(14, 6))
plt.plot(x, v7, label='V7', linewidth=2.5)
plt.plot(x, v8, label='V8', linewidth=2.0)
plt.plot(x, v81, label='V8.1', linewidth=2.0)
plt.plot(x, v82, label='V8.2', linewidth=2.5)
plt.xticks(x[::2], buckets[::2], rotation=45)
plt.ylabel('Aggregated total picking overload')
plt.xlabel('Bucket (HH:MM)')
plt.title('West picking overload curve: V7 vs V8 vs V8.1 vs V8.2')
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(out_png, dpi=200)
print(out_png)
