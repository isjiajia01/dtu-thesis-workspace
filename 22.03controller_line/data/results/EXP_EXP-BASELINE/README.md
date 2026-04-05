# EXP-BASELINE Results

这个目录是 `EXP-BASELINE` 的 canonical result root。

## 先看哪里

- `_analysis/exp_baseline_aggregate.csv`
- `_analysis/exp_baseline_per_seed.csv`
- `_analysis/exp_baseline_report.md`

这些文件是 `EXP-BASELINE` 的默认读取入口。

## 目录含义

- `_analysis/`：paper-facing aggregate
- `baseline/Seed_*/`：每个 seed 的 canonical seed-level 输出

## 使用边界

`EXP-BASELINE` 只承担 BAU implementation baseline context。

它可以用于：

- 对照 `EXP00` / `EXP01` 的基础实现表现
- 解释 greedy baseline 的 seed 级波动

它不承担：

- `Scenario1` controller ranking
- Herlev mainline endpoint 排名
- `DATA003` 扩展性主证据
