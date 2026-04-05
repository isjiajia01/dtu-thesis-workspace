# Workflow (living document)

## Defaults

- 优先小改动。
- 复用已有结构与脚本。
- 记录关键假设与决策。
- 实验必须可复现（输入、参数、矩阵版本、输出路径）。

## Commands

- Tests: `python3 -m pytest -q`

## Template Patch Log

## Template Patch (2026-03-05)
Change:
- [Add] Rule: 路网距离统一使用 OSRM 矩阵，禁止欧氏距离近似。

Reason:
- 保证实验与结果可信度。

Applies to:
- Optimization

Verification:
- 检查实验运行是否读取 `data/processed/vrp_matrix_latest/`。

Links:
- problem.md
- docs/workflow/optimization.md

## Template Patch (2026-03-05)
Change:
- [Add] Rule: 正式实验必须通过 HPC (`bsub` / LSF) 提交，登录节点只允许 `--dry-run`、脚本生成与文档维护。
- [Add] Rule: 默认 `max_trips_per_vehicle = 2`，除非实验定义显式覆盖。
- [Add] Rule: 失败实验输出目录必须立即删除，不保留半成品。

Reason:
- 统一实验执行环境，并避免残缺结果污染复现状态。

Applies to:
- Optimization

Verification:
- 非 LSF 环境执行 `python -m scripts.runner.master_runner --exp EXP00 --seed 1` 应被拒绝。
- 生成的 HPC 脚本应包含 `export VRP_MAX_TRIPS_PER_VEHICLE=2`。
- 失败运行后不应遗留对应结果目录。

Links:
- scripts/runner/master_runner.py
- scripts/runner/generate_hpc_jobs.py
- docs/workflow/optimization.md

## Template Patch (2026-03-11)
Change:
- [Add] Rule: 当实验矩阵被主动收缩时，必须同步裁剪实验注册表、作业脚本、CLI 入口与论文草稿，避免仓库留下失效入口。

Reason:
- 只删实验文件本身会留下大量还能调用但一定失败的残余路径，后续维护成本更高。

Applies to:
- Optimization

Verification:
- `scripts/experiment_definitions.py`、`jobs/`、`paper/*.md` 中保留的实验范围应一致。
- 非 retained 的作业脚本应移入 `jobs/archive/`，避免误提交。

Links:
- scripts/experiment_definitions.py
- jobs
- jobs/archive
- paper

## Template Patch (2026-03-12)
Change:
- [Add] Rule: 当比较控制器新版本时，必须至少同时保留 `base`、`compute`、`max_trips` 三类对照，以区分控制逻辑增益、求解预算增益和物理扩容增益。

Reason:
- 如果只看单条主线结果，容易把服务率提升错误归因到算时增加或车次扩容，而不是控制策略本身。

Applies to:
- Optimization

Verification:
- 保留的 paper-facing 主线应至少覆盖 `v2 -> v4 -> v5 -> v6f -> v6g` 的单一 compute300 比较链。
- 额外 `max_trips`、`cap`、`probe`、`sweep` 结果只保留在 supplementary 或 archive 层，不再进入主线作业集合。

Links:
- jobs/submit_scenario1_robust_v2_compute300.sh
- jobs/submit_scenario1_robust_v4_event_commitment_compute300.sh
- jobs/submit_scenario1_robust_v5_risk_budgeted_compute300.sh
- jobs/submit_scenario1_robust_v6f_execution_guard_compute300.sh
- jobs/submit_scenario1_robust_v6g_deadline_reservation_v6d_compute300.sh
