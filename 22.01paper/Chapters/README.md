# `22.01paper/Chapters/` Rewrite Map

## 目的

本文件是 `22.01paper/Chapters/` 的正式重写地图，用来指导最终毕业论文正文的章节重建。

当前 thesis 的整体结构应理解为一条连续研究线，而不是几个仓库或工作区的机械拼接：

- 更早期的 broad research material 提供广义问题定义、数据语义、正式建模、方法探索与附录级算法深度；
- `22.03controller_line/` 提供最终保留的实验主线、controller progression、结果叙事与 claim guardrails；
- `22.04fresh_solver/` 提供更新的 integrated-solver 架构、depot-aware 诊断、OR / shadow-price 机制探索与 solver-side 讨论素材；
- `22.01paper/` 是最终毕业论文成稿位置。

因此，`22.01paper/Chapters/` 的改写原则是：

1. 按研究逻辑组织章节，不按仓库分章节；
2. 用 broader research material 讲深问题与方法背景；
3. 用 `22.03controller_line` 收敛 retained experiment 主线与结果结论；
4. 用 `22.04fresh_solver` 补充当前 solver 架构、诊断洞察与 discussion 中真正需要的新内容；
5. 全文读起来必须像一篇 thesis，而不是多个 project 的并列总结。

---

## 总体写作原则

### 1. 统一主叙事
整篇论文应写成：

- 从一个 rich multi-day rolling-horizon delivery problem 出发；
- 经过较广的方法探索；
- 最终收敛为一个 retained thesis line；
- 同时在更后期工作中形成了更强的 integrated-solver 结构与诊断理解；
- 并在这一统一研究程序上给出实验、结果、讨论与结论。

### 2. 广到窄，再到结构深化，而不是并列拼接
自然的叙事顺序应该是：

- 问题为什么复杂；
- 数据和业务语义如何支持这个问题；
- 初始方法空间为什么更广；
- 为什么 thesis 最终收敛到 retained controller line；
- retained line 如何评估并形成论文主结果；
- newer solver-side work 带来了哪些额外机制理解；
- 还有哪些限制与未来方向。

### 3. 章节分工
- broader earlier material 主要支撑：背景、数据语义、建模、广义方法空间、discussion、appendix；
- `22.03controller_line` 主要支撑：retained experiment scope、controller line、results、guardrails、conclusion；
- `22.04fresh_solver` 主要支撑：architecture refinement、solver-side mechanism discussion、depot diagnostics、limitations / future work 的新洞察；
- `22.01paper/Chapters/` 负责把这些内容重写成自然流畅的正式论文章节。

---

## 推荐目标章节结构

建议把当前模板章节改写为以下目标结构，并同步更新 `22.01paper/main.tex` 的章节引用顺序。

### 推荐目标文件名
1. `01_introduction.tex`
2. `02_literature_review.tex`
3. `03_problem_setting.tex`
4. `04_methodological_evolution.tex`
5. `05_architecture_and_retained_method.tex`
6. `06_experimental_design.tex`
7. `07_results.tex`
8. `08_discussion_and_limitations.tex`
9. `09_conclusion.tex`

说明：

- 这里采用顺序化编号，便于最终论文维护；
- 如果后续章节名继续微调，也应保持本 README 中的章节功能分工不变；
- Appendix 相关内容应主要进入 `Backmatter/Appendix.tex`，而不是把过多技术细节塞回正文。

---

## 章节逐一重写地图

## Chapter 1 — `01_introduction.tex`

### 章节目标
建立 thesis 问题背景与研究动机，说明为什么这不是普通的静态单日 VRP。

### 本章应回答的问题
- 现实配送为什么需要 rolling-horizon planning；
- 为什么 flexible service windows 会引入跨日决策；
- 为什么 routing 不是唯一难点；
- 为什么 depot resource constraints 与 plan stability 值得纳入 thesis；
- 本 thesis 的最终研究目标是什么。

### 主要来源
来自 broader earlier material：
- 问题背景、业务语义、广义问题框架。

来自 `22.03controller_line`：
- `problem.md`
- `docs/decisions.md`

来自 `22.04fresh_solver`：
- `docs/问题背景.md`
- `docs/最优算法架构.md`

### 推荐写法
本章前半用广义问题框架立题，说明问题复杂性。  
本章后半明确 thesis 的两个关键落点：
- 论文主结果依托 `22.03controller_line` 的 retained experiment line；
- 后续 solver-side 架构深化与 depot-aware 机制理解则在 `22.04fresh_solver` 中进一步展开。

### 不应做的事
- 不要在这一章就展开大量公式；
- 不要把 controller 版本细节全部放进引言；
- 不要把多个工作区介绍成多个彼此独立项目。

---

## Chapter 2 — `02_literature_review.tex`

### 章节目标
把 thesis 放到相关研究脉络中，说明它与已有 dynamic / rolling / robust dispatch / integrated warehouse-routing 类工作的关系。

### 本章应回答的问题
- 本 thesis 属于哪些研究方向；
- 相比经典 VRP / VRPTW，本 thesis 多了哪些现实要素；
- 与 rolling-horizon planning、dynamic VRP、robust dispatch / admission control 的关系是什么；
- 与 integrated picking-routing / depot-resource coupling 的关系是什么；
- thesis 的方法定位在哪里。

### 主要来源
- `22.01paper/bibliography.bib`
- broader literature notes
- `22.03controller_line` 中已收敛的 paper-facing literature framing
- `22.04fresh_solver` 中围绕 integrated solver / depot-aware realism 的问题定义补充

### 推荐写法
以 thesis 真实会使用的文献主线为中心，服务于 retained thesis line 与 integrated-solver discussion，而不是写成无限扩张的 survey。

### 不应做的事
- 不要写成与 thesis 主线无关的泛泛综述；
- 不要把 exact / branch-price 相关文献写成全文中心；
- 不要引入正文中不会再使用的术语体系。

---

## Chapter 3 — `03_problem_setting.tex`

### 章节目标
正式定义 thesis 的问题、数据语义、输入输出与约束结构。

### 本章应回答的问题
- 订单、天、车辆、仓库、矩阵的定义是什么；
- release day、due day、service window 如何进入问题；
- rolling-horizon 决策流程是什么；
- objective 包含哪些部分；
- 为什么需要 stability / plan-churn 概念；
- 原始业务字段如何映射到模型语义。

### 主要来源
来自 broader earlier material：
- 正式问题定义、数据语义、字段解释、rolling-horizon 执行逻辑。

来自 `22.03controller_line`：
- `problem.md`
- 相关数据语义与 retained 实验口径材料。

来自 `22.04fresh_solver`：
- `docs/问题背景.md`
- `docs/最优算法架构.md`

### 推荐写法
这一章应先给出比 retained experiment 更一般的问题定义，再清楚说明：论文最终主实验会在这个一般问题之上收敛，而更新的 fresh-solver 工作则帮助更明确地表达 depot-aware realism 在问题结构中的位置。

### 推荐结构
- 3.1 Operational context
- 3.2 Data and semantic interpretation
- 3.3 Formal problem definition
- 3.4 Objectives and KPIs
- 3.5 Rolling-horizon execution logic
- 3.6 Scope narrowing for the retained thesis line

### 不应做的事
- 不要把所有广义扩展都写成最终实验已经全部覆盖；
- 不要省略数据语义来源，否则问题会显得过于抽象；
- 不要把本章写成 purely code walkthrough。

---

## Chapter 4 — `04_methodological_evolution.tex`

### 章节目标
解释 thesis 如何从 broad research program 收敛到 retained controller line，并进一步过渡到对 integrated solver 架构的更清晰理解。

### 本章应回答的问题
- 最初考虑过哪些方法方向；
- 为什么 thesis 一开始不是单纯 controller-only line；
- 为什么最终主实验主线收敛到 `EXP00` / `EXP01` 与 `Scenario1`；
- 为什么 final controller progression 写成 `v2 -> v4 -> v5 -> v6f -> v6g`；
- 为什么后续还需要 fresh-solver / integrated-solver 这条新线。

### 主要来源
来自 broader earlier material：
- 较宽的方法空间与历史探索记录。

来自 `22.03controller_line`：
- `docs/decisions.md`
- `experiments.md`
- `22.01paper/THESIS_EXPERIMENT_WRITING_MAP.md`

来自 `22.04fresh_solver`：
- `docs/最优算法架构.md`
- `docs/22.03controller_line_vs_22.04fresh_solver_关系与口径说明.md`

### 推荐写法
这是最重要的“自然化”章节。  
必须明确说明：
- 前期研究存在更宽的方法空间；
- 毕业论文主结果需要收敛到一个可复现、可解释、可写成完整 thesis 的 retained line；
- 而 `22.04fresh_solver` 不是要推翻 retained line，而是帮助把 thesis 主问题的 solver-side 结构讲得更完整。

### 不应做的事
- 不要把这一章写成周报；
- 不要机械枚举所有历史版本；
- 不要让 exploratory fresh-solver line 抢走 retained controller line 的主结果地位。

---

## Chapter 5 — `05_architecture_and_retained_method.tex`

### 章节目标
说明 thesis 最终系统如何组织、如何运行，以及 retained method 与 newer integrated-solver architecture 之间的关系。

### 本章应回答的问题
- 数据从哪里来，到哪里去；
- `scripts/`、`code/`、`src/`、`data/` 的分工是什么；
- retained controller-centered pipeline 如何运行；
- controller 与 routing / execution backend 如何交互；
- 为什么 `22.04fresh_solver` 需要把 `controller + routing + depot-aware repair` 写成更明确的体系结构。

### 主要来源
来自 `22.03controller_line`：
- `docs/architecture.md`
- `code/`
- `scripts/`
- `src/`

来自 `22.04fresh_solver`：
- `README.md`
- `docs/最优算法架构.md`
- `src/algorithms/fresh_solver/julia/README.md`

### 推荐写法
正文应先把 retained experiment line 真正依赖的系统结构讲清楚，再用一个更克制的小节解释 `22.04fresh_solver` 如何把 thesis 主算法架构显式化、集成化，而不是把本章写成两个代码库的并列导览。

### 不应做的事
- 不要逐文件罗列源码；
- 不要把本章写成 API 文档；
- 不要让 exploratory implementation detail 淹没 thesis 主方法表达。

---

## Chapter 6 — `06_experimental_design.tex`

### 章节目标
定义 retained thesis line 的实验框架、实验范围、指标、运行方式和 audit 逻辑。

### 本章应回答的问题
- 为什么选 `EXP00` 与 `EXP01`；
- `Scenario1` 在 thesis 中处于什么位置；
- seed、HPC、数据路径、输出路径如何组织；
- KPI 包括什么；
- 为什么 stability / robustness / OOD 是重要补充维度；
- 哪些实验属于正文主线，哪些只是 counterexample 或 supplementary support。

### 主要来源
来自 `22.03controller_line`：
- retained experiments、jobs、definitions、claim guardrails。

来自 `22.01paper`：
- `CHAPTER_REWRITE_PLAN.md`
- `THESIS_EXPERIMENT_WRITING_MAP.md`
- `CLAIM_GUARDRAILS.md`

必要时来自 `22.04fresh_solver`：
- solver-side diagnosis / supplementary experiment framing，但不取代 retained scope。

### 推荐写法
这一章要以 `22.03controller_line` 的 retained scope 为准绳。  
`22.04fresh_solver` 只在需要交代补充机制验证或 solver-side regime analysis 时作为次级支持。

### 不应做的事
- 不要把所有历史实验都重新纳入正文；
- 不要让协议细节淹没主实验定义；
- 不要写超出 retained writing map 的结论预告。

---

## Chapter 7 — `07_results.tex`

### 章节目标
作为 thesis 的结果主章节，严格按 retained writing map 展示结果，并明确 newer solver-side work 在文中的合理位置。

### 本章应回答的问题
- `EXP00` 定义了什么正常参考水平；
- `EXP01` 如何体现压力下退化；
- `Scenario1` controller line 如何逐步改进；
- 为什么 `v6f` 是机制转折点；
- 为什么 `v6g` 是 current main candidate；
- OOD depot evidence 应如何表述；
- `22.04fresh_solver` 的结果应如何作为 architecture-side / diagnostic-side 补充，而不是混成同一排名表。

### 主要来源
来自 `22.03controller_line`：
- retained outputs 与 writing map。

来自 `22.04fresh_solver`：
- strict / optimistic baseline、OR 支线、V8 系列、bucket diagnostics 等，仅在需要支持机制讨论或补充对照时使用。

### 推荐结果顺序
1. `EXP00`
2. `EXP01`
3. `v2 -> v4`
4. `v4 -> v5`
5. `v5 -> v6f`
6. `v6f -> v6g`
7. OOD evidence
8. supplementary / counterexample lines
9. selective solver-side discussion hooks if they are needed for later discussion

### 不应做的事
- 不要在结果章重新展开 broad method history；
- 不要把 abandoned lines 写成 equally important alternatives；
- 不要把 `22.03controller_line` 与 `22.04fresh_solver` 塞进一张平面 best-model ranking 表。

---

## Chapter 8 — `08_discussion_and_limitations.tex`

### 章节目标
解释结果意味着什么、还不能说明什么，以及 broader line 与 fresh-solver line 如何为 thesis 增加深度。

### 本章应回答的问题
- retained line 的主要学术与实践意义是什么；
- 为什么 broader formulation 仍然重要；
- 为什么当前结果不能等同于真实物理上限；
- solver-side 与 controller-side 的边界在哪里；
- `22.04fresh_solver` 带来了哪些新的机制理解，例如 depot-aware realism、bucket diagnostics、morning-wave smoothing；
- 还有哪些 limitation 和 future work。

### 推荐写法
这一章是 `22.04fresh_solver` 发挥最大价值的位置之一。  
正文主结果仍来自 retained line，但 discussion 中可以合理吸收 fresh-solver 的结构化洞察，用来解释：
- 为什么 integrated solver 值得继续做；
- 为什么 depot-side realism 改变了问题理解；
- 为什么某些实例呈现 regime-dependent behavior。

### 不应做的事
- 不要在 discussion 里偷偷把 thesis scope 又扩宽；
- 不要把 speculative follow-up 写成已证实结论；
- 不要把 modeled execution limit 写成 real-world physical limit。

---

## Chapter 9 — `09_conclusion.tex`

### 章节目标
总结 thesis 的核心贡献与最终结论，简洁收口。

### 本章应回答的问题
- thesis 研究了什么问题；
- 为什么这个问题重要；
- thesis 如何从 broader research program 收敛到 retained line；
- 最终主贡献是什么；
- `v6g` 为什么是当前 retained endpoint；
- integrated-solver line 为 thesis 增加了什么结构化理解；
- 本 thesis 的边界在哪里。

### 推荐写法
结论应以 retained thesis line 为主，不应再重新引入大量历史分支。  
同时可以非常克制地补一句：后续 `22.04fresh_solver` 工作进一步强化了 thesis 对 integrated controller-routing-repair architecture 与 depot-aware realism 的理解，但并不改变 retained paper-facing result spine 的主地位。

### 不应做的事
- 不要在结论章扩展新的主线；
- 不要把 appendix-level methods 写成 thesis main contribution；
- 不要使用超出证据边界的表述。

---

## 与 Appendix 的关系

以下内容优先进入 `Backmatter/Appendix.tex`，而不是正文：

- 更宽的方法探索细节；
- exact / branch-price / pricing 细节；
- 过深的 backend implementation notes；
- `22.04fresh_solver` 中只对内部调参或机制验证有用、但不适合占正文篇幅的扩展实验；
- targeted validation / audit details if needed。

Appendix 的作用是：
- 保存技术深度；
- 不打断 retained thesis line；
- 给答辩或审稿式阅读提供更强支撑。

---

## 推荐改写优先级

建议按以下顺序重写 `22.01paper/Chapters/`：

1. `03_operational_context_and_problem_setting.tex`
2. `04_methodological_evolution.tex`
3. `05_architecture_and_retained_method.tex`
4. `06_experimental_design.tex`
5. `07_results.tex`
6. `08_discussion_and_limitations.tex`
7. `01_introduction.tex`
8. `02_literature_review.tex`
9. `09_conclusion.tex`

原因：
- 问题定义、方法桥梁、系统架构、实验设计和结果主线先确定后，其他章节更容易自然收口；
- 引言和结论最好在主干形成后再写；
- 文献综述可以在主叙事稳定后再更有针对性地补齐。

---

## 未来维护规则

如果以下任一内容发生变化，本 README 应同步更新：

1. 最终章节结构变化；
2. retained controller line 变化；
3. `22.03controller_line` 与 `22.04fresh_solver` 的分工变化；
4. 结果章节顺序变化；
5. appendix 与正文的边界变化；
6. `22.01paper/main.tex` 的章节文件命名方案变化。

---

## 一句话总结

`22.01paper/Chapters/` 的最终任务不是复制几个工作区的内容，而是把：

- broader research material 的问题厚度与方法深度，
- `22.03controller_line` 的实验收敛与 paper-facing 主结果，
- `22.04fresh_solver` 的结构化 solver 洞察与诊断理解，

重写成一篇自然、统一、可答辩的毕业论文。