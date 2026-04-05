# Optimization Workflow

1. 阅读 `problem.md`，确认问题定义与数据路径。
2. 以 `experiments.md` 为当前实验矩阵依据。
3. 使用 `scripts/cli.py` 运行 `EXP00` / `EXP01`。
4. 所有实验必须使用 `data/processed/vrp_matrix_latest/` 路网矩阵。
5. 记录结果并更新 `experiments.md` 和 `docs/decisions.md`。
6. 清理失败或非当前矩阵的结果目录，只保留必要实验。
7. 正式实验必须通过 HPC (`bsub`) 提交，登录节点只允许 `--dry-run`、脚本生成与文档维护。
8. 默认 `max_trips_per_vehicle = 2`，除非实验定义显式覆盖。

## 核心实验提交

- `python -m scripts.cli hpc-generate --all`
- `bsub < jobs/submit_exp00.sh`
- `bsub < jobs/submit_exp01.sh`

## 结果命名与清理规则

- 结果目录必须使用实验 ID + 语义名称，不使用纯时间戳。
- 只保留 `EXP00` / `EXP01` 及其审计或图表产物。
- 失败实验必须立即删除对应输出目录，不保留半成品。
