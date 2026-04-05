# Retained EXP01 Endpoints

这个目录是索引层，不是结果存储层。

这里不复制任何 `summary_final.json`，只定义：

- 当前仍属于 paper-facing scope 的 endpoint
- 它们在正文中的角色
- 应该回到哪个原始 sibling 目录读取实际结果

这样做的目的，是在不改动现有结果路径的前提下，把 retained mainline 和历史探索区分清楚。

## Mainline endpoints

这些 endpoint 构成当前正文主线：

- `../baseline/`
- `../scenario1_robust_v2_compute300/`
- `../scenario1_robust_v4_event_commitment_compute300/`
- `../scenario1_robust_v5_risk_budgeted_compute300/`
- `../scenario1_robust_v6f_execution_guard_compute300/`
- `../scenario1_robust_v6g_deadline_reservation_v6d_compute300/`

正文应将它们写成：

- `EXP01` baseline
- `v2 -> v4 -> v5 -> v6f -> v6g`

## Supplementary retained endpoints

这些 endpoint 仍可进入 thesis，但不是主线终点：

- `../scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05/`
- `../scenario1_robust_v6g_deadline_reservation_v6d_automode/`
- `../scenario1_robust_v6g_deadline_reservation_v6d_fixed300_cap05_control/`
- `../scenario1_ood_aalborg_v6g_v6d_compute300/`
- `../scenario1_ood_odense_v6g_v6d_compute300/`
- `../scenario1_ood_aabyhoj_v6g_v6d_compute300/`
- `../data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt/`
- `../data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt/`

对应角色：

- `cap05` = supplementary Herlev rollback result
- `automode` = runtime-policy follow-up
- `OOD` = cross-depot transfer evidence
- `DATA003` = auxiliary scaling evidence

## 默认读取顺序

1. 先读 `../_analysis_suite/`
2. 再读 `../_analysis_scenario1/`
3. 然后只进入本文件列出的 retained endpoint

如果某个 endpoint 不在本文件里，默认不要先把它当作当前正文证据。

## 重要说明

这里列出的就是当前 canonical retained 路径本身，例如：

- `../scenario1_robust_v6g_deadline_reservation_v6d_compute300/Seed_*/summary_final.json`

分析脚本已经兼容这一层级，因此不需要再回退到旧的 root-level sibling 布局。
