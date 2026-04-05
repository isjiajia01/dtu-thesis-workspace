# 22.03 `docs/` 使用说明

本目录用于保存 `22.03controller_line` 这条**最终 thesis 主线**的说明性文档。  
它不是结果产物目录，也不是代码入口目录，而是：

- 定义当前论文主线的研究口径
- 说明系统结构、数据路径和实验假设
- 记录关键决策与收缩边界
- 为 `paper/` 中的正式写作提供解释性支撑

---

## 1. 本目录在整个 thesis 中的定位

整个 thesis 工作区可以理解为两层：

- `22.02thesis/`：更广的研究与建模基础盘  
- `22.03controller_line/`：最终保留的论文主线与实验收敛线

因此，`22.03controller_line/docs/` 的职责不是重复 `22.02` 的全部内容，而是做三件事：

1. **收敛**：明确当前论文究竟保留哪些实验、哪些口径、哪些方法线  
2. **约束**：防止后续写作把历史分支、废弃路线、超范围 claim 混回正文  
3. **桥接**：把代码、实验、数据和 `paper/` 中的写作计划连接起来

一句话概括：

> `22.03controller_line/docs/` 是当前毕业论文主线的“解释层”和“边界控制层”。

---

## 2. 当前 thesis 主线

当前 `22.03controller_line` 只服务于下列主线：

- `EXP00`
- `EXP-BASELINE`
- `EXP01`
- `EXP01 / Scenario1` 下的 controller line：
  - `v2`
  - `v4`
  - `v5`
  - `v6f`
  - `v6g`

当前论文的最终方法叙事应收敛为：

- `EXP00`：正常运营参考
- `EXP01`：单波压力基线
- `Scenario1`：在 `EXP01` 之上的 controller 改进链
- 当前 best main candidate：`v6g`
- `v6f`：机制过渡点
- `v6b3`：反例，不是最优主线
- `v6h`：后续探索，不作为定稿前提

---

## 3. 目录内文档说明

## `architecture.md`
**作用：**  
说明 `22.03controller_line` 当前保留实现的结构与数据流。

**主要回答：**
- 代码入口在哪里
- `code/`、`scripts/`、`src/` 分别做什么
- 数据从 `data/raw` 到 `data/processed` 再到 `data/results` 的流向是什么
- OSRM matrix 在哪里、为什么必须使用

**论文用途：**
- 对应 `paper` 中的“系统架构 / 实现”章节
- 可支撑架构图、模块关系图、实验执行链说明

---

## `decisions.md`
**作用：**  
记录当前 thesis 主线中已经做出的关键收缩决策。

**主要回答：**
- 为什么只保留 `EXP00 / EXP01`
- 为什么采用 OSRM matrix
- 为什么正式实验统一走 HPC
- 为什么主线演化最终收敛到 `v2 -> v4 -> v5 -> v6f -> v6g`

**论文用途：**
- 支撑方法演化章节
- 支撑 discussion 中“为何选择这条主线而不是其他分支”
- 防止正文回退到已经放弃的版本叙事

**维护原则：**
- 只记录会影响论文结构、结论或实验口径的决策
- 不记录零碎实现细节

---

## `literature.md`
**作用：**  
保存与当前 thesis 主线相关的文献梳理线索。

**主要回答：**
- 本 thesis 属于哪类问题
- 可以与哪些研究方向建立对照：
  - rolling-horizon planning
  - dynamic / online VRP
  - robust dispatch / control
  - execution-aware planning

**论文用途：**
- 对应 literature review 章节
- 用于构建“本 thesis 与已有工作差异”的桥段

**维护原则：**
- 只保留与最终主线相关的文献口径
- 不把与当前 thesis 无关的大量历史阅读笔记堆进来

---

## `raw_data_intake_20260305.md`
**作用：**  
解释原始业务数据和 workbook 语义。

**主要回答：**
- 原始 Excel 包含哪些 sheet
- 订单、仓库、车辆参数如何解释
- Herlev、Aalborg、Odense、Aabyhoj 等 depot 的统计与范围
- dispatch window 与 picking window 如何区分
- 为什么这些语义会影响建模与实验

**论文用途：**
- 对应数据来源与 operational semantics 小节
- 支撑 problem setting 与 data description
- 为“不是纯 toy benchmark”的可信度提供依据

---

## `workflow.md`
**作用：**  
说明当前仓库内软件任务与优化任务的工作方式。

**主要回答：**
- 做代码改动时应遵循什么流程
- 做实验/优化变更时应遵循什么流程
- 如何把临时工作整理成持续可维护的记录

**论文用途：**
- 一般不直接进入论文正文
- 但对 reproducibility 和未来维护很重要

---

## `workflow/`
该子目录存放更细的工作流说明。

### `workflow/optimization.md`
用于优化研究相关变更的工作规范，例如：
- 改实验
- 改方法线
- 改参数口径
- 改分析与评估逻辑

### `workflow/software.md`
用于软件维护相关变更的工作规范，例如：
- CLI
- runner
- analysis 脚本
- 测试和工程结构

**论文用途：**
- 通常不直接引用
- 但对后续 AI agent 或人工维护者很重要

---

## 4. 本目录与其他目录的关系

## 与 `22.03controller_line/code/` 的关系
- `code/` 是算法与仿真实现
- `docs/` 解释这些实现为何存在、在 thesis 中代表什么

## 与 `22.03controller_line/scripts/` 的关系
- `scripts/` 是运行与分析入口
- `docs/` 解释实验如何组织、为什么这样组织

## 与 `22.03controller_line/paper/` 的关系
- `paper/` 中的 Markdown 文件定义**正式写作地图**
- `docs/` 提供其背后的背景、边界与结构说明

推荐理解为：

- `docs/`：研究解释层
- `paper/`：论文写作规划层

---

## 5. 与 `22.02thesis` 的关系

`22.02thesis` 保存的是更广的研究基础，包括：

- 更丰富的问题建模
- 更宽的方法空间
- 更重的 exact / matheuristic / formulation 内容
- 更广的实验协议与历史探索

`22.03controller_line/docs/` 不应复制这些内容，而应：

1. 只吸收对最终 thesis 主线仍然必要的部分  
2. 用更收敛、更可写作的口径重新表达  
3. 把 broad research program 收缩为 final thesis line

因此：

- 如果你要解释“问题为什么这么复杂”，优先参考 `22.02`
- 如果你要解释“论文最后为什么只写这些内容”，优先参考 `22.03/docs/`

---

## 6. 在论文中的编排建议

本目录中的文档大致对应到 `paper` 的章节如下：

### Introduction / Problem Motivation
可参考：
- `raw_data_intake_20260305.md`
- `architecture.md`

### Literature Review
可参考：
- `literature.md`

### Problem Setting
可参考：
- `raw_data_intake_20260305.md`
- `architecture.md`

### Architecture / Implementation
可参考：
- `architecture.md`

### Method Evolution / Thesis Scope Narrowing
可参考：
- `decisions.md`

### Experimental Design
可参考：
- `architecture.md`
- `decisions.md`

### Discussion / Limitations
可参考：
- `decisions.md`
- `literature.md`

---

## 7. 本目录不应该放什么

为了保持清爽，本目录**不应**承担下列内容：

- 大型结果文件
- 临时日志
- 编译产物
- 空目录占位
- 已放弃路线的大量残留说明
- 与当前 thesis 主线无关的历史试验笔记
- 论文正式章节正文草稿（那应该放在 `paper/`）

---

## 8. 更新原则

修改本目录时，请遵守以下原则：

### 应当更新的情况
- thesis 主线发生收缩或替换
- 实验口径发生正式变化
- 数据路径、矩阵口径、运行规范发生变化
- 某个方法版本被正式升格为主线或降级为反例

### 不必更新的情况
- 单次调试
- 小范围实现修复
- 不影响论文主叙事的临时脚本改动

### 更新风格
- 优先追加明确结论
- 用简洁、可引用、可写入论文的语言
- 避免把文档写成流水账

---

## 9. 最小维护清单

每次 thesis 主线有实质变化时，至少检查以下文件是否需要同步：

- `docs/decisions.md`
- `experiments.md`
- `paper/THESIS_EXPERIMENT_WRITING_MAP.md`
- `paper/CLAIM_GUARDRAILS.md`
- `paper/CHAPTER_REWRITE_PLAN.md`

如果这些文件之间出现冲突，优先修正，使它们重新一致。

---

## 10. 简短结论

如果把 `22.02thesis` 看作“研究基础盘”，  
那么 `22.03controller_line/docs/` 就是“最终 thesis 主线的说明与约束层”。

它存在的目的不是记录一切，而是帮助你做到三件事：

1. **知道当前论文真正要写什么**
2. **知道哪些历史内容不该混回正文**
3. **让 `paper/` 的正式章节写作有清晰、稳定、可维护的依据**