## `scripts/` 目录说明

`scripts/` 现在只保留 `EXP00` / `EXP01` 所需的最小入口层：

- `runner/`
  - `master_runner.py`：运行 `EXP00` / `EXP01`
  - `generate_hpc_jobs.py`：生成对应 LSF 作业脚本
- `preflight/`
  - `verify_repo_hygiene.py`：检查 CLI、wrapper 与 `src` facade
- `analysis/`
  - `aggregate_exp_baseline.py`：聚合 `EXP-BASELINE` 的 per-seed 与均值/标准差结果
  - `aggregate_scenario1_suite.py`：聚合 `EXP01` 下 `scenario1_*` 端点结果
  - `export_v6_value_dataset.py`：从 `simulation_results.json` 导出 `v6b` value-to-go 训练数据
  - `train_v6_value_model.py`：训练最小线性 `v6b` value model 并输出 JSON artifact
  - `evaluate_v6_value_rerank.py`：在 held-out seeds 上离线重放 `v6b2` 候选并评估 value rerank
- `Scenario1` 研究线
  - `scenario1_greedy`：shock 下 greedy 对照
  - `scenario1_robust_v2*`：failure-first 字典序鲁棒控制器
  - `scenario1_robust_v3_commitment*`：引入 reserve / admission / carryover bias 的 commitment 控制器
  - `scenario1_robust_v4_event_commitment*`：加入 event mode、priority class 和 scenario-consensus commitment 的控制器
  - `scenario1_robust_v5_risk_budgeted*`：加入自适应 reserve/release、order-level risk scoring 和 compute coupling 的风险预算控制器
  - `scenario1_robust_v6a_execaware*`：加入 execution-aware effective capacity 与 DR risk frontier 的控制器
  - `scenario1_robust_v6a1_execaware*`：对 `v6a` 放松 trip/effective capacity 折扣并增强 compute 红利传导的校准版
  - `scenario1_robust_v6b_value_rerank*`：保留 `v5` 主骨架，用 execution-aware 特征和 value-to-go 对候选动作重排序
  - `scenario1_robust_v6b1_value_rerank*`：扩候选集并引入 action-conditioned value 特征的 `v6b` 校准版
  - `scenario1_robust_v6b2_guarded_value_rerank*`：在 `v6b1` 上增加 release/push guardrail，抑制单一极端动作塌缩
  - `scenario1_robust_v6b3_diversified_value_rerank*`：基于 `v6b2` 增加更干净的风险谱系候选集，扩大 rerank 的动作覆盖
  - `scenario1_ood_*`：在 `Aalborg` / `Odense` / `Aabyhoj` benchmark 上验证主线 controller 的跨 depot 泛化
- 顶层兼容 wrapper
  - `scripts/master_runner.py`
  - `scripts/generate_hpc_jobs.py`

## 推荐入口

- 配置检查：
  - `python -m scripts.cli run-exp --exp EXP01 --seed 1 --dry-run`
- 生成作业脚本：
  - `python -m scripts.cli hpc-generate --all`
- 仓库检查：
  - `python -m scripts.preflight.verify_repo_hygiene`
