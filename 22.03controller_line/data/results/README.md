# Results Layout

`22.03controller_line/data/results/` 里同时保存两类结果：

1. canonical experiment roots
2. raw timestamp run outputs

这两类目录都需要保留，但用途不同，不能混读。

## 先看哪里

论文写作、结果核对、聚合分析时，先看这三个 canonical roots：

- `EXP_EXP-BASELINE/`
- `EXP_EXP00/`
- `EXP_EXP01/`

推荐读取顺序：

1. `EXP_EXP-BASELINE/_analysis/`
2. `EXP_EXP00/_analysis_suite/`
3. `EXP_EXP01/_analysis_suite/`
4. `EXP_EXP01/_analysis_scenario1/`

这些目录是当前 paper-facing 的稳定入口。

## 不要先看哪里

不要先从根目录下的时间戳目录开始读结果，例如：

- `20260311_222032/`
- `20260314_131323_212591_scenario1_ood_*`
- `20260318_160141_359032_data003_*`

这类目录是原始运行产物，主要用于：

- 追溯某次作业实际输出
- 调试失败运行
- 回查 seed 级运行细节

它们不是默认的 paper-facing 入口。

## 命名约定

### Canonical experiment roots

- `EXP_EXP-BASELINE/` = `EXP-BASELINE` 的聚合与每 seed 结果
- `EXP_EXP00/` = `EXP00` 的聚合与相关 endpoint 结果
- `EXP_EXP01/` = `EXP01` baseline、`Scenario1` 主线、OOD 与 retained auxiliary lines

### Raw timestamp run outputs

根目录下形如以下模式的目录都应视为 raw run：

- `YYYYMMDD_HHMMSS/`
- `YYYYMMDD_HHMMSS_<job-name>/`

这些目录通常包含：

- `DEFAULT/Proactive/summary_final.json`
- 运行时日志
- 某次单 seed / 单 endpoint 的原始落盘结构

## 证据分层

为了避免把历史运行产物误当成当前论文证据，默认按下面的层次读取：

### 第一层：paper-facing aggregate

- `EXP_EXP-BASELINE/_analysis/`
- `EXP_EXP00/_analysis_suite/`
- `EXP_EXP01/_analysis_suite/`
- `EXP_EXP01/_analysis_scenario1/`

### 第二层：canonical seed-level endpoint results

- `EXP_EXP00/<endpoint>/Seed_*/summary_final.json`
- `EXP_EXP01/_retained/<endpoint>/Seed_*/summary_final.json`
- `EXP_EXP01/_historical/<endpoint>/Seed_*/summary_final.json`

### 第三层：raw timestamp trace

- 根目录下所有时间戳目录

只有在需要追溯某次实际运行、核对落盘一致性或排查问题时，才应该进入第三层。

## 当前清晰边界

- `EXP_*` 目录：默认视为 canonical、可写作、可聚合入口
- 根级时间戳目录：默认视为历史 raw outputs，不直接引用为论文主证据

如果要判断某个 endpoint 是否仍属于当前 thesis scope，请继续看：

- `EXP_EXP-BASELINE/README.md`
- `EXP_EXP00/README.md`
- `EXP_EXP01/README.md`
- `../../paper/THESIS_EXPERIMENT_WRITING_MAP.md`
- `../../paper/CLAIM_GUARDRAILS.md`
