# EXP00 Results

这个目录是 `EXP00` 的 canonical result root。

## Paper-Facing入口

优先读取：

- `_analysis_suite/suite_endpoint_summary.csv`
- `_analysis_suite/suite_metric_aggregate.csv`
- `_analysis_suite/suite_per_seed.csv`
- `_analysis_suite/suite_report.md`

`EXP00` 在当前 thesis 中首先承担：

- 无压力 BAU reference
- 与 `EXP01` 的 baseline-to-baseline 对照基线

## 结果分层

### 主 baseline

- `baseline/Seed_*/`

这是 `EXP00` 最核心、最直接的 paper-facing baseline 证据。

### DATA003 BAU lines

目录中还保留了多条 `data003_*` BAU 结果线。

这些结果可以用于：

- 说明更大 depot 上的 BAU / retained policy 背景
- 支撑 `DATA003` 辅助扩展性讨论

这些结果不应被直接写成：

- Herlev 主线 controller ranking
- 当前 thesis 的核心方法终点

## 使用原则

- 想写 `EXP00 vs EXP01` 的主基线差异，先看 `_analysis_suite/`
- 想回查某个 endpoint 的 seed-level 输出，再看 `<endpoint>/Seed_*/summary_final.json`
- 除非是在做 `DATA003` 辅助说明，否则不要先从 `data003_*` 目录开始读
