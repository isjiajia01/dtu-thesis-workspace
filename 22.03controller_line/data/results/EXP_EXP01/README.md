# EXP01 Results

这个目录是 `EXP01` 的 canonical result root，也是当前 `22.03` 最重要的结果目录。

## 先看哪里

### Baseline aggregate

- `_analysis_suite/suite_endpoint_summary.csv`
- `_analysis_suite/suite_metric_aggregate.csv`
- `_analysis_suite/suite_per_seed.csv`
- `_analysis_suite/suite_report.md`

### Scenario1 aggregate

- `_analysis_scenario1/scenario1_aggregate.csv`
- `_analysis_scenario1/scenario1_per_seed.csv`

这两组分析目录是当前 paper-facing 的默认结果入口。

本目录内部现在按两层结果桶组织：

- `_retained/`
- `_historical/`

实际结果文件已经收拢到这两个桶中；分析脚本已兼容这一层级。

## 目录分层

本目录下的 endpoint 可以分成三层：

### 1. Retained paper-facing mainline

- `_retained/baseline/`
- `_retained/scenario1_robust_v2_compute300/`
- `_retained/scenario1_robust_v4_event_commitment_compute300/`
- `_retained/scenario1_robust_v5_risk_budgeted_compute300/`
- `_retained/scenario1_robust_v6f_execution_guard_compute300/`
- `_retained/scenario1_robust_v6g_deadline_reservation_v6d_compute300/`

这部分构成当前论文正文的主线：

- `EXP01` baseline
- `Scenario1` controller progression `v2 -> v4 -> v5 -> v6f -> v6g`

更紧凑的 retained 视图见：

- `_retained/README.md`

### 2. Retained supplementary / follow-up evidence

- `_retained/scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05/`
- `_retained/scenario1_robust_v6g_deadline_reservation_v6d_automode/`
- `_retained/scenario1_robust_v6g_deadline_reservation_v6d_fixed300_cap05_control/`
- `_retained/scenario1_ood_aalborg_v6g_v6d_compute300/`
- `_retained/scenario1_ood_odense_v6g_v6d_compute300/`
- `_retained/scenario1_ood_aabyhoj_v6g_v6d_compute300/`
- `_retained/data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt/`
- `_retained/data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt/`

这部分可以进入论文，但角色是 supplementary：

- `cap05` = Herlev rollback result
- `automode` = runtime-policy follow-up
- `OOD` = cross-depot generalization
- retained `DATA003` lines = auxiliary scaling evidence

### 3. Historical / exploratory / non-default evidence

除以上两层之外，本目录其余多数 endpoint 都应默认视为：

- 历史探索
- 调参 sweep
- 已放弃方法线
- 内部分析支撑

典型例子包括：

- `scenario1_robust_v6b*`
- `scenario1_robust_v6c*`
- `scenario1_robust_v6d*`
- `scenario1_robust_v6e*`
- `scenario1_robust_v6h*`
- `scenario1_ood_*_cap05`
- `scenario1_ood_*_dyn60_*`
- `scenario1_ood_*_dyn90_*`
- 非 retained 的 `data003_*`
- `*_probe`
- `*_smoke`

这些目录已经被收拢到 `_historical/`，可保留用于 traceability，但不应作为默认 paper-facing 入口。

历史结果的使用边界说明见：

- `_historical/README.md`

## Analysis目录怎么理解

### Paper-facing aggregate

- `_analysis_suite/`
- `_analysis_scenario1/`

### Internal / exploratory analysis

- `_analysis_v6_value/`
- `_analysis_v6_value_v6b1/`
- `_analysis_v6d_eval/`
- `_analysis_v6d_eval_smoke/`
- `_analysis_v6d_value/`
- `_analysis_v6d_value_smoke/`

后者主要服务于模型开发、诊断和历史方法验证，不应直接当作当前 thesis 的正式结果章节入口。

## 安全读取顺序

1. 先看 `_analysis_suite/` 把 `EXP01` baseline 读清楚
2. 再看 `_analysis_scenario1/` 把 controller progression 读清楚
3. 然后只在需要时进入 `_retained/<endpoint>/Seed_*/summary_final.json`
4. 最后才去看 `_historical/<endpoint>/...` 或 raw timestamp outputs

## 当前主线边界

如果要写正式 thesis 结果章节，默认只把下面这些内容当成当前安全主证据：

- `baseline`
- `v2`
- `v4`
- `v5`
- `v6f`
- `v6g_v6d_compute300`
- supplementary `cap05`
- supplementary `automode`
- `OOD v6g_v6d_compute300`
- retained east/west `DATA003` auxiliary lines

更高层的写作边界仍以这些文件为准：

- `../../paper/THESIS_EXPERIMENT_WRITING_MAP.md`
- `../../paper/CLAIM_GUARDRAILS.md`
- `../../docs/decisions.md`
