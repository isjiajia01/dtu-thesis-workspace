# `paper/Chapters/` Rewrite Map

## 目的

本文件是 `thesis/paper/Chapters/` 的正式重写地图，用来指导最终毕业论文正文的章节重建。

当前 thesis 的整体结构应理解为一条连续研究线，而不是两个仓库的拼接：

- `22.02thesis/` 提供广义问题定义、数据语义、正式建模、方法探索与附录级算法深度
- `22.03controller_line/` 提供最终保留的实验主线、controller progression、结果叙事与 claim guardrails
- `paper/` 是最终毕业论文成稿位置

因此，`paper/Chapters/` 的改写原则是：

1. 按研究逻辑组织章节，不按仓库分章节
2. 用 `22.02` 讲深问题与方法背景
3. 用 `22.03` 收敛实验主线与结果结论
4. 全文读起来必须像一篇 thesis，而不是两个 project 的并列总结

---

## 总体写作原则

### 1. 统一主叙事
整篇论文应写成：

- 从一个 rich multi-day rolling-horizon delivery problem 出发
- 经过较广的方法探索
- 最终收敛为一个 retained thesis line
- 在该主线上给出实验、结果、讨论与结论

而不是：

- 先写 `22.02`
- 再写 `22.03`

### 2. 广到窄，而不是并列拼接
自然的叙事顺序应该是：

- 问题为什么复杂
- 数据和业务语义如何支持这个问题
- 初始方法空间为什么更广
- 为什么 thesis 最终收敛到 retained controller line
- retained line 如何评估
- retained line 得到了什么结果
- 还有哪些限制与未来方向

### 3. 章节分工
- `22.02` 主要支撑：背景、数据语义、建模、广义方法空间、discussion、appendix
- `22.03` 主要支撑：retained experiment scope、controller line、results、guardrails、conclusion
- `paper/Chapters/` 负责把二者重写成自然流畅的正式论文章节

---

## 推荐目标章节结构

建议把当前模板章节改写为以下目标结构，并同步更新 `paper/main.tex` 的章节引用顺序。

### 推荐目标文件名
1. `01_introduction.tex`
2. `02_literature_review.tex`
3. `03_problem_setting.tex`
4. `04_methodological_evolution.tex`
5. `05_architecture_and_implementation.tex`
6. `06_experimental_design.tex`
7. `07_results.tex`
8. `08_discussion_and_limitations.tex`
9. `09_conclusion.tex`

说明：

- 这里采用顺序化编号，便于最终论文维护
- 如果后续为了兼容旧版 `22.03controller_line/paper/` 文件名而保留旧命名，也应保持本 README 中的章节功能分工不变
- Appendix 相关内容应主要进入 `Backmatter/Appendix.tex`，而不是把过多技术细节塞回正文

---

## 章节逐一重写地图

## Chapter 1 — `01_introduction.tex`

### 章节目标
建立 thesis 问题背景与研究动机，说明为什么这不是普通的静态单日 VRP。

### 本章应回答的问题
- 现实配送为什么需要 rolling-horizon planning
- 为什么 flexible service windows 会引入跨日决策
- 为什么 routing 不是唯一难点
- 为什么 depot resource constraints 与 plan stability 值得纳入 thesis
- 本 thesis 的最终研究目标是什么

### 主要来源
来自 `22.02thesis`：
- `problem.md`

来自 `22.03controller_line`：
- `problem.md`
- `docs/decisions.md`

### 推荐写法
本章前半用 `22.02` 的广义问题框架立题，说明问题复杂性。  
本章后半用 `22.03` 的收敛口径说明 thesis 最终落点，即 retained experiment line。

### 不应做的事
- 不要在这一章就展开大量公式
- 不要把 controller 版本细节全部放进引言
- 不要把 exact line 写成主结论
- 不要把两个仓库当成两个项目来介绍

---

## Chapter 2 — `02_literature_review.tex`

### 章节目标
把 thesis 放到相关研究脉络中，说明它与已有 dynamic / rolling / robust dispatch 类工作的关系。

### 本章应回答的问题
- 本 thesis 属于哪些研究方向
- 相比经典 VRP / VRPTW，本 thesis 多了哪些现实要素
- 与 rolling-horizon planning、dynamic VRP、robust dispatch / admission control 的关系是什么
- thesis 的方法定位在哪里

### 主要来源
来自 `22.02thesis`：
- `docs/literature.md`

来自 `22.03controller_line`：
- `docs/literature.md`

### 推荐写法
以 `22.02` 的 broader literature context 为底，结合 `22.03` 的最终主线定位，形成一个服务于 retained thesis line 的文献综述，而不是无限扩张的 literature survey。

### 不应做的事
- 不要写成与 thesis 主线无关的泛泛综述
- 不要把 exact / branch-price 相关文献写成全文中心
- 不要引入正文中不会再使用的术语体系

---

## Chapter 3 — `03_problem_setting.tex`

### 章节目标
正式定义 thesis 的问题、数据语义、输入输出与约束结构。

### 本章应回答的问题
- 订单、天、车辆、仓库、矩阵的定义是什么
- release day、due day、service window 如何进入问题
- rolling-horizon 决策流程是什么
- objective 包含哪些部分
- 为什么需要 PlanChurn / stability 概念
- 原始业务字段如何映射到模型语义

### 主要来源
来自 `22.02thesis`：
- `problem.md`
- `model/formulation.md`
- `model/xlsx_field_to_constraints.md`
- `docs/raw_data_intake_20260305.md`
- `docs/experiments/plan_churn_protocol_week6.md`

来自 `22.03controller_line`：
- `problem.md`
- `docs/raw_data_intake_20260305.md`

### 推荐写法
这一章应以 `22.02/model/formulation.md` 为正式模型骨架。  
但要明确说明：完整问题定义比最终 retained experimental line 更一般，而后续方法与实验章节会在这一一般问题之上进行收敛。

### 推荐结构
- 3.1 Operational context
- 3.2 Data and semantic interpretation
- 3.3 Formal problem definition
- 3.4 Objectives and KPIs
- 3.5 Rolling-horizon execution logic
- 3.6 Scope narrowing for the retained thesis line

### 不应做的事
- 不要把所有广义扩展都写成最终实验已经全部覆盖
- 不要省略数据语义来源，否则问题会显得过于抽象
- 不要把本章写成 purely code walkthrough

---

## Chapter 4 — `04_methodological_evolution.tex`

### 章节目标
这是连接 `22.02` 和 `22.03` 的桥梁章节，解释 thesis 如何从 broad research program 收敛到 final retained line。

### 本章应回答的问题
- 最初考虑过哪些方法方向
- 为什么 thesis 一开始不是单纯 controller-only line
- baseline heuristic、ALNS、restricted master、exact-track 各自处于什么位置
- 为什么最终主线收敛到 `EXP00` / `EXP01` 与 `Scenario1`
- 为什么 final controller progression 写成 `v2 -> v4 -> v5 -> v6f -> v6g`

### 主要来源
来自 `22.02thesis`：
- `model/solver.md`
- `model/exact_track.md`
- `model/branch_price_design.md`
- `docs/architecture.md`
- `experiments.md`

来自 `22.03controller_line`：
- `docs/decisions.md`
- `experiments.md`
- `paper/THESIS_EXPERIMENT_WRITING_MAP.md`

### 推荐写法
这是最重要的“自然化”章节。  
必须明确说明：前期研究存在更宽的方法空间，但毕业论文主线需要收敛到一个可复现、可解释、可写成完整 thesis 的 retained line。

### 推荐结构
- 4.1 Broad candidate methodology in the early research phase
- 4.2 Why the thesis scope was narrowed
- 4.3 Retained experiment scope
- 4.4 Final controller progression and endpoint selection

### 不应做的事
- 不要把这一章写成周报
- 不要机械枚举所有历史版本
- 不要让 exact line 抢走 retained controller line 的主角地位

---

## Chapter 5 — `05_architecture_and_implementation.tex`

### 章节目标
说明最终 thesis 系统如何组织、如何运行、模块之间如何协作。

### 本章应回答的问题
- 数据从哪里来，到哪里去
- `scripts/`、`code/`、`src/`、`data/` 的分工是什么
- rolling simulation pipeline 如何运行
- controller 与 routing solver 如何交互
- 为什么系统结构能支持 retained experiments

### 主要来源
来自 `22.02thesis`：
- `docs/architecture.md`
- `src/optimization/instance_builder.py` 对应的实现逻辑
- `src/optimization/run_day.py`
- `src/optimization/run_horizon.py`
- `julia/` 与 `restricted_master` 相关材料，可做补充说明

来自 `22.03controller_line`：
- `docs/architecture.md`
- `code/`
- `scripts/`
- `src/`

### 推荐写法
正文应以后期 `22.03` 的 retained architecture 为主。  
`22.02` 的内容主要用于补充 broader system design 背景与实现深度。

### 推荐结构
- 5.1 Repository and system layout
- 5.2 Data flow and artifact flow
- 5.3 Rolling simulation loop
- 5.4 Controller layer and solver layer
- 5.5 Reproducibility and execution environment

### 不应做的事
- 不要逐文件罗列源码
- 不要把本章写成 API 文档
- 不要让 Julia / exact backend 占据正文中心

---

## Chapter 6 — `06_experimental_design.tex`

### 章节目标
定义 retained thesis line 的实验框架、实验范围、指标、运行方式和 audit 逻辑。

### 本章应回答的问题
- 为什么选 `EXP00` 与 `EXP01`
- `Scenario1` 在 thesis 中处于什么位置
- seed、HPC、数据路径、输出路径如何组织
- KPI 包括什么
- 为什么 stability / robustness / OOD 是重要补充维度
- 哪些实验属于正文主线，哪些只是 counterexample 或 appendix support

### 主要来源
来自 `22.02thesis`：
- `experiments.md`
- `docs/experiments/protocol.md`
- `docs/experiments/tracks_week6.md`
- `docs/experiments/plan_churn_protocol_week6.md`
- `docs/experiments/resistance_suite.md`

来自 `22.03controller_line`：
- `experiments.md`
- `paper/CHAPTER_REWRITE_PLAN.md`
- `paper/THESIS_EXPERIMENT_WRITING_MAP.md`
- `paper/CLAIM_GUARDRAILS.md`
- `scripts/experiment_definitions.py`
- `jobs/`

### 推荐写法
这一章要以 `22.03` 的 retained scope 为准绳。  
`22.02` 在这里主要提供实验方法学的深度与设计 rationale。

### 推荐结构
- 6.1 Retained experimental scope
- 6.2 Baseline experiments: `EXP00` and `EXP01`
- 6.3 Scenario1 controller comparison design
- 6.4 KPIs and auditing logic
- 6.5 HPC and reproducibility workflow
- 6.6 Robustness and OOD rationale

### 不应做的事
- 不要把所有历史实验都重新纳入正文
- 不要让协议细节淹没主实验定义
- 不要写超出 retained writing map 的结论预告

---

## Chapter 7 — `07_results.tex`

### 章节目标
作为 thesis 的结果主章节，严格按 retained writing map 展示结果。

### 本章应回答的问题
- `EXP00` 定义了什么正常参考水平
- `EXP01` 如何体现压力下退化
- `Scenario1` controller line 如何逐步改进
- 为什么 `v6f` 是机制转折点
- 为什么 `v6g` 是 current main candidate
- OOD depot evidence 应如何表述
- 哪些版本只能作为反例或 follow-up

### 主要来源
来自 `22.03controller_line`：
- `paper/THESIS_EXPERIMENT_WRITING_MAP.md`
- `paper/CLAIM_GUARDRAILS.md`
- `paper/FIGURE_BUILD_RECIPES.md`
- `experiments.md`
- 未来重新生成的 `data/results/` 输出

来自 `22.02thesis`：
- 只在解释 KPI 价值或 broader evaluation philosophy 时作为弱支撑

### 推荐结果顺序
1. `EXP00`
2. `EXP01`
3. `v2 -> v4`
4. `v4 -> v5`
5. `v5 -> v6f`
6. `v6f -> v6g`
7. OOD evidence
8. `v6b3` 作为 counterexample
9. `v6h` 仅作为 narrow follow-up mention

### 不应做的事
- 不要在结果章重新展开 broad method history
- 不要把 abandoned lines 写成 equally important alternatives
- 不要写超出 claim guardrails 的强因果表述

---

## Chapter 8 — `08_discussion_and_limitations.tex`

### 章节目标
解释结果意味着什么、还不能说明什么，以及 broad research line 如何为 thesis 增加深度。

### 本章应回答的问题
- retained line 的主要学术与实践意义是什么
- 为什么 broad formulation 仍然重要
- 为什么当前结果不能等同于真实物理上限
- solver-side 与 controller-side 的边界在哪里
- exact / bound-oriented line 的价值是什么
- 还有哪些 limitation 和 future work

### 主要来源
来自 `22.02thesis`：
- `model/exact_track.md`
- `model/branch_price_design.md`
- `docs/experiments/resistance_suite.md`
- `docs/paper/week4_tradeoff_notes.md`

来自 `22.03controller_line`：
- `paper/CLAIM_GUARDRAILS.md`
- `docs/decisions.md`

### 推荐写法
这一章是 `22.02` 发挥“研究厚度”的最佳位置。  
正文主结果来自 `22.03`，而 discussion 中的学术拔高、限制与未来方向可以大量借助 `22.02` 的 broader line。

### 推荐结构
- 8.1 Interpretation of the retained controller line
- 8.2 Operational meaning of stability and execution awareness
- 8.3 Limits of current evidence
- 8.4 Role of broader optimization methods
- 8.5 Future work

### 不应做的事
- 不要在 discussion 里偷偷把 thesis scope 又扩宽
- 不要把 speculative follow-up 写成已证实结论
- 不要把 modeled execution limit 写成 real-world physical limit

---

## Chapter 9 — `09_conclusion.tex`

### 章节目标
总结 thesis 的核心贡献与最终结论，简洁收口。

### 本章应回答的问题
- thesis 研究了什么问题
- 为什么这个问题重要
- thesis 如何从 broad research program 收敛到 retained line
- 最终主贡献是什么
- `v6g` 为什么是当前最佳 endpoint
- 本 thesis 的边界在哪里

### 主要来源
来自 `22.03controller_line`：
- `paper/THESIS_EXPERIMENT_WRITING_MAP.md`
- `paper/CLAIM_GUARDRAILS.md`
- `docs/decisions.md`

来自 `22.02thesis`：
- 仅用于补充 broader methodological significance

### 推荐写法
结论应以 retained thesis line 为主，不应再重新引入大量历史分支。  
一句话上，结论应体现：

- broad problem richness
- narrowed retained method line
- final experimental contribution
- disciplined scope

### 不应做的事
- 不要在结论章扩展新的主线
- 不要把 appendix-level methods 写成 thesis main contribution
- 不要使用超出证据边界的表述

---

## 与 Appendix 的关系

以下内容优先进入 `Backmatter/Appendix.tex`，而不是正文：

来自 `22.02thesis`：
- `model/branch_price_design.md`
- `model/pricing_audit.md`
- `model/pricing_certificate_notes.md`
- `model/pricing_strengthening.md`
- `model/rcsp_pricing_notes.md`
- `model/week11_exact_sprint.md`
- `docs/experiments/backend_protocol_week6.md`
- `docs/experiments/rsp_protocol_week6.md`
- `docs/experiments/medium_gap_protocol_week6.md`
- `julia/` backend details
- targeted test / validation notes if needed

Appendix 的作用是：
- 保存技术深度
- 不打断 retained thesis line
- 给答辩或审稿式阅读提供更强支撑

---

## 推荐改写优先级

建议按以下顺序重写 `paper/Chapters/`：

1. `03_problem_setting.tex`
2. `04_methodological_evolution.tex`
3. `06_experimental_design.tex`
4. `07_results.tex`
5. `08_discussion_and_limitations.tex`
6. `01_introduction.tex`
7. `05_architecture_and_implementation.tex`
8. `02_literature_review.tex`
9. `09_conclusion.tex`

原因：
- 问题定义、方法桥梁、实验设计和结果主线先确定后，其他章节更容易自然收口
- 引言和结论最好在主干形成后再写
- literature review 与 architecture chapter 可以在主叙事稳定后补齐

---

## 未来维护规则

如果以下任一内容发生变化，本 README 应同步更新：

1. 最终章节结构变化
2. retained controller line 变化
3. `22.02` 与 `22.03` 的分工变化
4. 结果章节顺序变化
5. appendix 与正文的边界变化
6. `paper/main.tex` 的章节文件命名方案变化

---

## 一句话总结

`paper/Chapters/` 的最终任务不是复制两个仓库的内容，而是把：

- `22.02` 的问题厚度与方法深度
- `22.03` 的实验收敛与结果主线

重写成一篇自然、统一、可答辩的毕业论文。