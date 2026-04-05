# 决策与假设（持续维护）

## 假设

- 本仓库当前只维护 `EXP00` / `EXP01` 两个基线实验。
- `data/raw` 只读，`data/processed` 可再生成。
- 论文实验以滚动多日 VRP 仿真为核心评估手段。

## 决策

- [2026-03-05] 决策：22.03 以 22.02 的目录结构为骨架。
  理由：结构清晰，适合长期维护与实验管理。
  影响：所有入口、文档与数据路径以该结构为准。
- [2026-03-05] 决策：使用 OSRM 路网矩阵替代欧氏距离。
  理由：欧氏距离近似误差较大，不适用于论文级结果。
  影响：实验必须读取 `data/processed/vrp_matrix_latest/`。
- [2026-03-05] 决策：正式实验统一走 HPC，默认每车每日最多两趟。
  理由：避免登录节点生成非正式结果，并统一车辆日内利用约束。
  影响：`master_runner` 在非 LSF 环境默认拒绝正式运行；HPC 作业显式导出 `VRP_MAX_TRIPS_PER_VEHICLE=2`。
- [2026-03-11] 决策：仓库时间线收缩为 `EXP00` / `EXP01` 完成时的状态。
  理由：删除所有后续实验、学习增强链路、风险门和对应文档残留，避免混入更晚阶段的内容。
  影响：实验注册、脚本、数据产物和论文 Markdown 只保留 `EXP00` / `EXP01`。
- [2026-03-14] 决策：`scenario1_robust_v6g_deadline_reservation_v6d_compute300` 升级为当前 thesis 主线最终候选。
  理由：`v6g` 在 Herlev `Scenario1 / compute300` 上将服务率提升到 `97.9885%`，失败单降到 `21.0`，同时在 `Aalborg / Odense / Aabyhoj` 三个 OOD depot 上均达到 `100%` 服务率与 `0` 失败单。此前的 `mt3 / fleet increase / max_duration relax` probe 均未显著超过该版本，说明当前剩余 gap 更接近 solver execution feasibility，而不是简单物理资源不足。
  影响：论文主线更新为 `v2 -> v4 -> v5 -> v6f -> v6g`，其中 `v6f` 用于说明 execution-aware guard 的机制增益，`v6g` 作为最终 main candidate；`v6h` 仅作为 solver-side follow-up，不作为主线定稿前提。
- [2026-03-21] 决策：论文口径进一步统一为“一条 Herlev 主线 + 一条动态算时 follow-up + east/west 单条辅助线”。
  理由：如果同时保留 `cap05`、`automode`、`v6g60/v6g90r`、以及多条 `DATA003` sweep，正文会退化为 tuning 结果堆叠，而不是清晰的方法线。`scenario1_robust_v6g_deadline_reservation_v6d_compute300` 是当前最干净的 `v6f -> v6g` 机制比较基线，因此应作为唯一 paper-facing main candidate；`cap05` 仅保留为 Herlev best-service rollback；`automode` 仅保留为动态算时工程 follow-up；`DATA003 east/west` 只各保留一条 `v6g_v6d` 辅助线以支持扩展性讨论。
  影响：`paper/`、`THESIS_EXPERIMENT_WRITING_MAP.md`、`CLAIM_GUARDRAILS.md`、`AGENTS.md` 与 `experiments.md` 应统一以 `scenario1_robust_v6g_deadline_reservation_v6d_compute300` 为唯一主线终点；`data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt` 与 `data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt` 作为唯一 retained `DATA003` 口径；动态算时只保留 `scenario1_robust_v6g_deadline_reservation_v6d_automode` 对 `scenario1_robust_v6g_deadline_reservation_v6d_fixed300_cap05_control` 的比较。

- [2026-03-21] 决策：`jobs/` 目录收缩为 retained paper-facing 最小集合，其余脚本统一归档到 `jobs/archive/`。
  理由：如果保留所有旧 sweep、probe、cap 和 stress 脚本，后续维护者很容易误把历史调参入口当成当前正式实验入口。归档比直接删除更安全，也更符合 thesis evidence traceability。
  影响：`jobs/` 只保留 baseline backbone、主线 controller progression、runtime-policy follow-up、三城 OOD、retained east/west auxiliary line 与 DATA003 matrix build 脚本；其余脚本默认视为历史入口，不再作为论文结论依据。
- [2026-03-22] 决策：`EXP_EXP01` 结果目录按 `_retained/` 与 `_historical/` 两层收拢，分析脚本改为递归发现 endpoint。
  理由：如果继续把 retained mainline、历史 sweep、OOD tuning 与 probe 端点全部平铺在 `EXP_EXP01/` 根层，维护者和写作者都很容易误读当前 paper-facing 边界；但直接搬目录而不改脚本，又会破坏聚合与审计入口。
  影响：`EXP_EXP01` 的当前主线、supplementary 与 retained auxiliary lines 统一落在 `_retained/`；历史 endpoint 统一落在 `_historical/`；`aggregate_suite_results.py`、`aggregate_scenario1_suite.py`、`audit_v6_residual_failures.py`、`evaluate_v6_value_rerank.py`、`distill_dynamic_runtime_rule.py` 与 `v6_value_model.py` 改为递归解析 endpoint；后续新的 `EXP01` 运行也按 endpoint 分类自动写入 `_retained/` 或 `_historical/`。

## 未决问题

- 是否需要继续压缩 `paper/Chapters/` 的叙述范围，使正文也只显式讨论 `EXP00` / `EXP01`。
