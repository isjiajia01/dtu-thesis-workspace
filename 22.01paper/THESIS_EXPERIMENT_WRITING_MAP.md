# Thesis Experiment Writing Map

## Scope

当前 thesis manuscript 的 paper-facing 主结果仍只保留 `22.03controller_line` 的 retained experiment scope：

- `EXP00`
- `EXP01`
- `EXP01` 下的 `Scenario1` controller line（`v2 -> v4 -> v5 -> v6f -> v6g`）

`22.04fresh_solver` 的结果可以在 architecture / discussion / mechanism-analysis 相关章节中被有选择地引用，但不应直接替代这里定义的主实验 spine。

## Chapter Mapping

下表中的 chapter role 仍以 `22.03controller_line` 作为 retained experiment backbone；如果 later manuscript 需要吸收 `22.04fresh_solver`，也应保持这种主次关系不变。

| Chapter | Purpose | Evidence |
| --- | --- | --- |
| Ch. 4 Architecture | 说明当前保留的实验运行链，以及 `Scenario1` controller stack | `scripts/`, `code/`, `src/` |
| Ch. 6 Experimental Design | 定义 `EXP00` / `EXP01` 的种子、HPC 运行方式与数据路径，并交代 `Scenario1` endpoint matrix | `scripts/experiment_definitions.py`, `experiments.md`, `jobs/` |
| Ch. 7 Results | 先展示 `EXP00` 与 `EXP01` 的基线差异，再展示 `Scenario1` controller line、OOD transfer 与 `DATA003` 辅助扩展性证据 | `data/results/EXP_EXP00/_analysis_suite/`, `data/results/EXP_EXP01/_analysis_suite/`, `data/results/EXP_EXP01/_analysis_scenario1/` |

## Evidence Table

| Experiment | Role | Output path |
| --- | --- | --- |
| `EXP00` | BAU reference | `22.03controller_line/data/results/EXP_EXP00/_analysis_suite/suite_endpoint_summary.csv` |
| `EXP01` | Crunch baseline | `22.03controller_line/data/results/EXP_EXP01/_analysis_suite/suite_endpoint_summary.csv` |
| `scenario1_robust_v5_risk_budgeted_compute300` | 说明 admission / commitment / release 已能逼近 `98\%` 前的主线水平 | `22.03controller_line/data/results/EXP_EXP01/_retained/scenario1_robust_v5_risk_budgeted_compute300/Seed_*/summary_final.json` |
| `scenario1_robust_v6f_execution_guard_compute300` | 说明问题主瓶颈已从 phase/value 转到 execution-aware dispatch；为 `v6g` 的前置机制证据 | `22.03controller_line/data/results/EXP_EXP01/_retained/scenario1_robust_v6f_execution_guard_compute300/Seed_*/summary_final.json` |
| `scenario1_robust_v6g_deadline_reservation_v6d_compute300` | 当前唯一 paper-facing Herlev main candidate；用于 `v6f -> v6g` 的最终机制比较 | `22.03controller_line/data/results/EXP_EXP01/_retained/scenario1_robust_v6g_deadline_reservation_v6d_compute300/Seed_*/summary_final.json` |
| `scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05` | supplementary Herlev best-service rollback result | `22.03controller_line/data/results/EXP_EXP01/_retained/scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05/Seed_*/summary_final.json` |
| `scenario1_robust_v6g_deadline_reservation_v6d_automode` | 唯一保留的动态算时工程 follow-up；只与 fixed300 control 对照 | `22.03controller_line/data/results/EXP_EXP01/_retained/scenario1_robust_v6g_deadline_reservation_v6d_automode/Seed_*/summary_final.json` |
| `scenario1_robust_v6b3_diversified_value_rerank*` | 反例：diversification 改善 stress robustness，但损伤主线 base / compute300 最优性 | `22.03controller_line/data/results/EXP_EXP01/_historical/scenario1_robust_v6b3_*/Seed_*/summary_final.json` |
| `scenario1_ood_*_v6g_v6d_compute300` | OOD 证据：在保持 `Scenario1 / EXP01` shock 口径不变的前提下，跨 depot 仍可保持 `100\%` 服务率 | `22.03controller_line/data/results/EXP_EXP01/_retained/scenario1_ood_*_v6g_v6d_compute300/Seed_*/summary_final.json` |
| `data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt` | retained east auxiliary scaling line | `22.03controller_line/data/results/EXP_EXP01/_retained/data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt/Seed_*/summary_final.json` |
| `data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt` | retained west auxiliary scaling line | `22.03controller_line/data/results/EXP_EXP01/_retained/data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt/Seed_*/summary_final.json` |

## Final Narrative

- `EXP00` 与 `EXP01` 仍然是论文的实验骨架，用于定义正常运营与单波压力口径。
- `Scenario1` controller line 是 `EXP01` 之上的方法线，不是额外独立场景。
- 结果章节的最终主线应写成：`v2 -> v4 -> v5 -> v6f -> v6g`。
- 当前唯一 Herlev paper-facing main candidate 应明确写为 `scenario1_robust_v6g_deadline_reservation_v6d_compute300`。
- `scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05` 只保留为 supplementary rollback result，不作为正文 headline endpoint。
- `v6f` 负责支撑 “execution-aware guard” 的机制过渡；`v6g` 负责最终结果收口。
- 动态算时只保留 `scenario1_robust_v6g_deadline_reservation_v6d_automode` 这一条 follow-up 线，并且只与 `fixed300` control 比较。
- `v6b3` 不作为主线最优版本，而作为“candidate diversification helps stress but hurts base” 的反例。
- `DATA003 east/west` 只承担辅助扩展性证据，不进入 Herlev 主线 ranking，并且各 depot 只保留一条 canonical `v6g_v6d` 线。
- OOD 写作应以 10-seed 的 `scenario1_ood_*_v6g_v6d_compute300` 为主；`cap05 / dyn60 / dyn90` 的 5-seed OOD sweep 不再进入 paper-facing main text。

## Final Ranking

以当前 paper-facing Herlev mainline 均值为准：

1. `scenario1_robust_v6g_deadline_reservation_v6d_compute300`
   - `service_rate = 97.9885%`
   - `failed_orders = 21.0`
   - `penalized_cost = 9788.13`
2. `scenario1_robust_v6f_execution_guard_compute300`
   - `service_rate = 97.8161%`
   - `failed_orders = 22.8`
   - `penalized_cost = 10272.60`
3. `scenario1_robust_v5_risk_budgeted_compute300`
   - `service_rate = 97.3659%`
   - `failed_orders = 27.5`
   - `penalized_cost = 10235.64`

Supplementary Herlev results:

- `scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05`
  - `service_rate = 98.3238%`
  - `failed_orders = 17.5`
  - `penalized_cost = 12024.20`
- `scenario1_robust_v6g_deadline_reservation_v6d_automode`
  - `service_rate = 98.1992%`
  - `failed_orders = 18.8`
  - `penalized_cost = 12189.20`
- `scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05_reopt`
  - `service_rate = 98.2280%`
  - `failed_orders = 18.5`
  - `penalized_cost = 12126.29`

这些结果只作为 supplementary comparison，不替代 `v6g_v6d_compute300` 的 paper-facing main candidate 身份。

## DATA003 Auxiliary Evidence

`DATA003` 不进入主线 controller ranking，但可安全写为辅助扩展性证据：

- `EXP00 / east / BAU`
  - 最佳服务率：`data003_east_bau_v6g90r_w12h_reopt` 与 `data003_east_bau_v6g_v6d_compute300_w12h_dyn90_reopt` 均为 `99.9969%`
  - 最低 penalized cost：`data003_east_bau_v6g60_w12h_reopt = 57543.02`
- `EXP00 / west / BAU`
  - 四条主结果线均为 `100%` 服务率与 `0` 失败单
  - 最低 penalized cost：`data003_west_bau_v6g_v6d_compute300_w16h_reopt = 176157.05`
- `EXP01 / east / crunch`
  - retained auxiliary line：`data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt`
  - `service_rate = 99.8898%`
  - `failed_orders = 3.6`
  - `penalized_cost = 59911.87`
- `EXP01 / west / crunch`
  - retained auxiliary line：`data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt`
  - `service_rate = 99.4748%`
  - `failed_orders = 23.9`
  - `penalized_cost = 181414.89`
- 其他 `DATA003` sweep 可以用于内部调参与诊断，但不再作为 paper-facing canonical endpoint。
写作建议：

- 若强调“最终主线 controller”，应写 `v6g_v6d_compute300` 为当前唯一 paper-facing main candidate。
- 若强调“机制推进路径”，应写 `v6f` 识别并修复 execution-aware dispatch 问题，`v6g_v6d_compute300` 完成 deadline-reservation 收口。
- 若强调 runtime-policy，应只写 `automode` 相对 `fixed300 control` 的工程 follow-up 结果，不把它写成新的主方法线。
- 若强调泛化，应补一句：`v6g_v6d_compute300` 在 `Aalborg / Odense / Aabyhoj` 三个 OOD depot 上均达到 `100%` 服务率与 `0` 失败单。
- 若强调扩展性，应补一句：`DATA003 east/west` 只保留单条 `v6g_v6d` 辅助线，用于说明 retained policy 在更大实例上仍然保持高服务率，但不进入主线 ranking。

## Writing Guardrail

- 不再在本文件中维护与 `EXP00` / `EXP01` 无关的实验。
- 不把 `v6c` 作为有效路线写入正文；该线已被放弃。
- 不把 `v6b3` 写成 best model；它只承担 stress-side counterexample 角色。
- 不把 `v6h` 写成定稿主线；它只是 solver-side follow-up，用于测试是否还能把 `v6g` 推过 `98%`。
- 不把 `cap05` 或 `automode` 升级成新的 paper-facing main candidate。
- 不把 `DATA003` 的 east/west 结果与 Herlev 主线直接做同一张“best model” ranking。
- 不把 `v6g60 / v6g90r` 之类的 `DATA003` tuning 线写成 retained east/west canonical endpoint。
- 不把只有 `summary_partial.json` 的 endpoint 写成正式结论；当前 `data003_east_crunch_r060_v6g_v6d_compute300_w16h_dyn90_reopt`、`data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt_memlean_probe`、`data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt_probe` 仍不应进入 paper-facing aggregate claim。
