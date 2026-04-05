# Claim Guardrails

## Scope

- 本目录当前只保留 `EXP00` 与 `EXP01` 的写作口径。
- `EXP01` 下的 `Scenario1` controller line 可以作为方法比较口径保留。
- 除 `EXP00` / `EXP01` 及其 `Scenario1` controller line 外，其他实验 claim 都不再作为当前论文草稿的一部分。

## Safe Claims

1. `EXP00` 是无压力参考基线。
- 用于定义正常运营下的服务率、失败数和原始成本水平。

2. `EXP01` 是单波压力基线。
- 用于描述在 thesis reference crunch 条件下系统的退化幅度。

3. `EXP01` 应与 `EXP00` 做基线对基线的受压对比。
- 安全写法：`EXP01` 相比 `EXP00` 体现了容量压力下的服务损失与失败增长。

4. `Scenario1` controller line 可以写成 `EXP01` 之上的方法改进链。
- 安全写法：`v4` 相比 `v2` 说明 event-driven commitment 有效；`v5` 说明风险预算进一步改善主线；`v6f` 说明 execution-aware guard 能显著降低 deadline-day drop；`v6g` 说明在不改 value artifact 的前提下，deadline reservation 能把主线进一步推到接近 `98\%`。

5. `v6b3` 只能写成反例。
- 安全写法：增加 candidate diversification 改善了 stress-side robustness，但损害了 base / compute300 主线最优性，因此未被选为最终 controller。

6. `v6g_v6d_compute300` 可以写成当前唯一 paper-facing main candidate。
- 安全写法：该版本在 Herlev 主线达到 `97.9885\%` 服务率、`21.0` 平均失败单，并在 `Aalborg / Odense / Aabyhoj` 三个 OOD depot 上保持 `100\%` 服务率。

7. `cap05` 只能写成 supplementary Herlev rollback result。
- 安全写法：该版本取得更高的 Herlev 服务率与更少失败单，但它属于轻改控制器 rollback，不替代 canonical main candidate。

8. `automode` 可以写成唯一保留的动态算时 engineering follow-up。
- 安全写法：它用于说明系统如何基于压力信号在 `dyn60 / dyn90 / fixed300` 之间切换，但不应被写成新的主方法线。

9. `DATA003 east/west` 可以写成辅助扩展性证据，但每个 depot 只保留一条 canonical `v6g_v6d` 线。
- 安全写法：`east` 使用 `data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt`，`west` 使用 `data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt`；它们用于说明更大 depot 上的 retained policy 仍可维持很高服务率，但不进入 Herlev 主线 ranking。

## Unsafe Claims

1. 不要把 `v6c` 写成有效路线；该线已被实证否决。
2. 不要把 `v6b3` 写成 best model。
3. 不要把 `compute300` 的微小差异写成强机制证明。
4. 不要把 `EXP00` / `EXP01` 写成因果机制证明，它们首先承担 baseline 与 pressure 口径定义角色。
5. 不要把“当前模型里的执行上限”直接写成“真实物理上限”；当前模型尚未独立建模 driver / dock / reload 等现实资源。
6. 不要把 `v6h` 写成已经定稿的最终版本；在没有结果前，它只能算 solver-side exploratory follow-up。
7. 不要把 `cap05` 写成新的 main candidate，也不要把它写成主要 runtime 提速机制。
8. 不要把 `automode` 写成方法主线终点；它只是 retained runtime-policy follow-up。
9. 不要把 `DATA003 east/west` 和 Herlev 放进同一张“最终 best controller”横向排名表。
10. 不要把 `v6g60 / v6g90r` 之类 tuning 线写成 retained east/west canonical endpoint。
11. 不要把只有 `summary_partial.json` 的 endpoint 写成最终结果。
