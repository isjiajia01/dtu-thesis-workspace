# 22.03 Thesis Line Overview

`22.03controller_line/` 是当前 thesis 的收窄实验主线，不是一个新的独立项目。

它在整个工作区中的职责是：

- 固定最终保留的实验范围
- 固定 paper-facing controller progression
- 固定结果写作顺序、claim 边界与复现实验入口

如果只用一句话概括：

> `22.03controller_line/` 是从 `22.02thesis/` 收窄出来的 final experiment line，服务于最终论文，而不是替代最终论文目录。

## 先看什么

第一次进入 `22.03controller_line/`，建议按这个顺序读：

1. `problem.md`
2. `experiments.md`
3. `docs/architecture.md`
4. `docs/decisions.md`
5. `paper/THESIS_EXPERIMENT_WRITING_MAP.md`
6. `paper/CLAIM_GUARDRAILS.md`
7. `jobs/README.md`

这些文件共同定义当前 `22.03` 的 source of truth。

## 当前保留范围

当前 thesis 只保留：

- `EXP00`
- `EXP-BASELINE`，仅作为 BAU implementation baseline context
- `EXP01`
- `EXP01 / Scenario1` controller line：`v2 -> v4 -> v5 -> v6f -> v6g`

当前唯一 paper-facing Herlev main candidate：

- `scenario1_robust_v6g_deadline_reservation_v6d_compute300`

当前 supplementary / follow-up：

- `scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05`
- `scenario1_robust_v6g_deadline_reservation_v6d_automode`
- `scenario1_ood_*_v6g_v6d_compute300`
- `data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt`
- `data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt`

不应重新升格为主线的内容：

- `v6b3`，只保留为 counterexample
- `v6c`，已放弃
- `v6h`，只算 solver-side exploratory follow-up
- `jobs/archive/` 下的历史 sweep、probe、runtime-policy 旧入口

## 目录怎么读

| Path | Role | How to use it |
| --- | --- | --- |
| `problem.md` | 当前问题口径 | 用于说明 `controller + routing backend` 问题结构 |
| `experiments.md` | 当前实验骨架 | 用于确认保留实验、主线版本与复现入口 |
| `docs/` | 解释层 | 解释架构、决策、数据语义与工作流 |
| `paper/` | 写作控制层 | 不是主论文目录，只保留 writing map、claim guardrails 与 figure plan |
| `scripts/` | 运行与分析入口 | `cli.py`、job generation、analysis 聚合都在这里 |
| `code/` | 当前实现 | controller、routing backend、experiments 的主实现 |
| `src/` | 兼容 facade | 兼容 `src.*` 导入，不是另一套独立实现 |
| `jobs/` | paper-facing HPC 入口 | 只保留当前活跃、可复现、可写作的作业 |
| `jobs/archive/` | 历史入口归档 | 仅保留 traceability，不作为默认正式入口 |
| `data/raw/` | 原始输入 | 只读 |
| `data/processed/` | 可再生成输入 | benchmark 与 OSRM matrix 在这里 |
| `data/results/EXP_EXP00` | `EXP00` canonical aggregate | `EXP00` 相关写作先看这里 |
| `data/results/EXP_EXP01` | `EXP01` canonical aggregate | `Scenario1` 主线写作先看这里 |

## Runtime state note

Heavy runtime state is externalized under `~/thesis-local-state/dtu-sem6/22.03controller_line/` and linked back here via symlinks for `.venv`, `data/processed`, `data/results`, and `logs`.
Default root sync scripts treat those paths as local-only state rather than iCloud-synced source.

## 结果应该从哪里读

优先看 canonical aggregate，而不是先翻 timestamp run 目录。

- `EXP00`:
  - `data/results/EXP_EXP00/_analysis_suite/`
- `EXP01` baseline:
  - `data/results/EXP_EXP01/_analysis_suite/`
- `Scenario1` controller line:
  - `data/results/EXP_EXP01/_analysis_scenario1/`
- 单个 endpoint 的 seed-level 结果：
  - `data/results/EXP_EXP01/_retained/<endpoint>/Seed_*/summary_final.json`
  - 或 `data/results/EXP_EXP01/_historical/<endpoint>/Seed_*/summary_final.json`

`data/results/` 下大量带时间戳的目录主要是原始运行产物；它们有追溯价值，但不应作为 paper-facing 入口层。
`EXP_EXP01/` 内部则进一步按 `_retained/` 与 `_historical/` 收拢 endpoint。

## 运行入口

推荐入口：

- dry run:
  - `python -m scripts.cli run-exp --exp EXP01 --seed 1 --dry-run`
- 生成作业：
  - `python -m scripts.cli hpc-generate --all`
- 正式 HPC 提交：
  - `bsub < jobs/submit_exp00.sh`
  - `bsub < jobs/submit_exp-baseline_greedy.sh`
  - `bsub < jobs/submit_exp01.sh`

`jobs/` 只保留当前 paper-facing entrypoints。
如果一个脚本只在 `jobs/archive/`，默认应视为历史实验，不再作为当前论文结论依据。

## 术语和写作口径

当前 `22.03` 的安全写法是：

- 把整体系统写成 `controller + routing backend`
- 把日内求解写成 `routing solver` 或 `daily routing backend`
- 需要实现细节时，写 `OR-Tools GLS solver`

不推荐把当前主线直接写成：

- `ALNS` 主方法线
- 独立于 `EXP01` 的额外场景项目
- 一堆 tuning sweep 的横向 best-model 排名

## 和最终论文的关系

`22.03controller_line/paper/` 不是最终毕业论文目录。

最终 manuscript 应写在：

- `../paper/`

这里的 `paper/` 只承担写作控制职责：

- `THESIS_EXPERIMENT_WRITING_MAP.md`
- `CLAIM_GUARDRAILS.md`
- `CHAPTER_REWRITE_PLAN.md`
- `FIGURE_BUILD_RECIPES.md`

## 使用原则

- 需要 broad formulation、problem richness、appendix method context 时，回看 `../22.02thesis/`
- 需要 final experiment scope、controller progression、claim wording 时，以本目录为准
- 需要写正式 thesis 章节时，把 `22.02` 与 `22.03` 的内容整理后写入 `../paper/`

## 一句话导航

如果你现在要在 `22.03` 开始工作：

- 想确认“论文最后到底保留了什么”，看 `experiments.md`
- 想确认“哪些话能写，哪些不能写”，看 `paper/CLAIM_GUARDRAILS.md`
- 想确认“结果章节该怎么排”，看 `paper/THESIS_EXPERIMENT_WRITING_MAP.md`
- 想确认“当前目录里的代码和 jobs 各自干什么”，从本文件往下跳转到对应目录即可
