# Chapter Rewrite Plan

## Active Experiment Scope

The paper-facing retained experiment scope still centers on `22.03controller_line`:

- `EXP00`
- `EXP01`
- `EXP01` / `Scenario1` controller line: `v2`, `v4`, `v5`, `v6f`, `v6g`

`22.04fresh_solver` can support architecture/discussion sections and carefully selected mechanism-side comparisons, but it should not replace this retained result spine unless the thesis narrative is explicitly redesigned.

## Chapter Priorities

1. 用 `EXP00` 写清正常运营参考场景。
2. 用 `EXP01` 写清单波压力下的基线退化。
3. Chapter 6 保留 `EXP00` / `EXP01` 的实验设计、种子和 HPC 执行路径，并用一个小节交代 `Scenario1` endpoint matrix。
4. Chapter 7 先写 `EXP00` vs `EXP01` 的 baseline 差异，再写 `Scenario1` controller line 的方法升级，并补一个 OOD 小节说明 `v6g` 的跨 depot 稳定性。
5. Chapter 8 明确写：当前证据支持 `v6g` 已接近模型化执行上限，但并未证明真实物理上限；`v6h` 只作为 solver-side exploratory follow-up。

## Required Inputs

- `22.03controller_line/data/results/EXP_EXP00/`
- `22.03controller_line/data/results/EXP_EXP01/`
- `22.03controller_line/data/results/EXP_EXP01/_analysis_scenario1/`
- `22.03controller_line/experiments.md`
- `22.03controller_line/scripts/experiment_definitions.py`

## Result Writing Order

This ordering is for the main thesis result chapter. If `22.04fresh_solver` material is cited, it should appear only as secondary architecture-side or diagnostic support, not as a flat co-equal ranking track.

1. `EXP00` normal reference.
2. `EXP01` crunch baseline degradation.
3. `v2 -> v4`: show event-driven commitment beats failure-first robust baseline.
4. `v4 -> v5`: show risk-budgeted controller improves the main line.
5. `v5 -> v6f`: show the primary bottleneck has shifted from phase/value to execution-aware dispatch.
6. `v6f -> v6g`: show deadline reservation yields the best final controller line and closes the remaining Herlev gap to near `98%`.
7. OOD: show `v6g_v6d_compute300` preserves `100%` service rate on `Aalborg / Odense / Aabyhoj`.
8. `v6h`: mention only as a narrow solver-side follow-up, not as the main thesis result.
