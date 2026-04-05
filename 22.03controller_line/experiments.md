# 实验清单与复现计划

当前仓库只保留两个基线实验：

- `EXP00`：BAU 基线（无压力）
- `EXP-BASELINE`：BAU 下的 `greedy` 基线
- `EXP01`：Crunch 基线（单波压力）

## Scenario1

- 术语统一：
  - 不把当前日内求解器写成 `ALNS`。
  - 正文优先写 `daily routing backend` 或 `routing solver`。
  - 需要实现细节时写 `OR-Tools GLS solver`。
  - 整个实验链写成 `controller + routing backend`。

- `Scenario1` = `strict-online` 的突然 shock 口径。
- `EXP01` 是 `Scenario1` baseline。
- 基于 `EXP01` 的在线改进候选会写到 `data/results/EXP_EXP01/` 下，并按当前 retained 口径自动归入 `_retained/` 或 `_historical/`。
- 当前 thesis 主线：
  - `scenario1_robust_v6g_deadline_reservation_v6d_compute300`
  - 论文唯一主线终点：`service_rate = 97.9885%`, `failed_orders = 21.0`, `penalized_cost = 9788.13`
  - supplementary Herlev rollback：`scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05`
    - `service_rate = 98.3238%`, `failed_orders = 17.5`, `penalized_cost = 12024.20`
  - retained runtime-policy follow-up：`scenario1_robust_v6g_deadline_reservation_v6d_automode`
  - OOD：`Aalborg / Odense / Aabyhoj` 均为 `100%` 服务率与 `0` 失败单
  - retained `DATA003` auxiliary lines：
    - east: `data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt`
    - west: `data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt`
- 当前方法线应写为：
  - `v2 -> v4 -> v5 -> v6f -> v6g`
  - `v6f`：execution-aware guard 的机制过渡
  - `v6g`：deadline reservation 的最终收口版本
  - `v6h`：solver-side follow-up，不作为主线定稿前提
- 当前 paper-facing活跃作业：
  - `jobs/submit_exp00.sh`
  - `jobs/submit_exp-baseline_greedy.sh`
  - `jobs/submit_exp01.sh`
  - `jobs/submit_scenario1_robust_v2_compute300.sh`
  - `jobs/submit_scenario1_robust_v4_event_commitment_compute300.sh`
  - `jobs/submit_scenario1_robust_v5_risk_budgeted_compute300.sh`
  - `jobs/submit_scenario1_robust_v6f_execution_guard_compute300.sh`
  - `jobs/submit_scenario1_robust_v6g_deadline_reservation_v6d_compute300.sh`
  - `jobs/submit_scenario1_robust_v6g_deadline_reservation_v6d_automode.sh`
  - `jobs/submit_scenario1_robust_v6g_deadline_reservation_v6d_fixed300_cap05_control.sh`
  - `jobs/submit_scenario1_ood_aalborg_v6g_v6d_compute300.sh`
  - `jobs/submit_scenario1_ood_odense_v6g_v6d_compute300.sh`
  - `jobs/submit_scenario1_ood_aabyhoj_v6g_v6d_compute300.sh`
  - `jobs/submit_data003_east_crunch_r060_v6g_v6d_w12h_dyn90_reopt.sh`
  - `jobs/submit_data003_west_crunch_r060_v6g_v6d_w16h_reopt.sh`

## 运行方式

- 配置检查：`python -m scripts.cli run-exp --exp EXP01 --seed 1 --dry-run`
- 生成作业：`python -m scripts.cli hpc-generate --all`
- 正式运行：`bsub < jobs/submit_exp00.sh`、`bsub < jobs/submit_exp-baseline_greedy.sh` 或 `bsub < jobs/submit_exp01.sh`

## 写作建议

- 描述 `v2 -> v4 -> v5 -> v6f -> v6g` 时，把增益归因写在 `controller` 机制上，而不是写成底层 route heuristic 名称的升级。
- 说明日内求解时，写 `fixed-budget daily routing backend` 比写 `ALNS solve` 更准确。
- 如果需要解释工程结构，安全写法是：`the controller updates admission and reservation logic, while the OR-Tools GLS routing backend computes daily routes under a fixed time budget`.

## 数据要求

- 订单数据：`data/processed/multiday_benchmark_herlev.json`
- 路网矩阵：`data/processed/vrp_matrix_latest/`
- DATA003 原始 Excel：`data/raw/RangeOfDaysSimulation - Data 003.xlsx`

## 清理规则

- 只保留 `EXP00` / `EXP-BASELINE` / `EXP01` 及其结果目录
- 失败实验输出必须立即删除
- 非当前主线、动态算时 follow-up、以及 retained `DATA003` auxiliary line 的历史实验脚本不再作为论文结论依据
- 已归档脚本统一移入 `jobs/archive/`

## 复现状态

- [ ] EXP00
- [ ] EXP-BASELINE
- [x] EXP01
- [x] `Scenario1` Herlev 主线（`v6g_v6d_compute300`）
- [x] `Scenario1` OOD 三城（`v6g_v6d_compute300`）
