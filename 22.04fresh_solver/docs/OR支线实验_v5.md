# OR 支线实验 v5：controller-to-routing bucket feedback

## 1. 目的
在 OR-V4.1 的 targeted insertion bias 基础上，进一步把 controller 的 depot-risk 反馈显式传到 routing：

> controller 输出 `bucket_risk_signal`（normal / elevated / severe），routing 仅对高风险 flex 子集施加 targeted insertion bias，并根据 signal 强度增加 bias。

目标是从“局部 insertion bias”推进到“controller-to-routing 协同内生化”。

对应脚本：
- `src/algorithms/fresh_solver/julia/scripts/run_multiday_or_v5.jl`

输出：
- `results/raw_runs/herlev_multiday_or_v5_julia.json`

---

## 2. 实现方式
### Controller 侧
在 `controller.jl` 中新增：
- `bucket_risk_signal`

依据上一日：
- `last_depot_penalty`
- `last_overload_bucket_count`

把状态分成：
- `normal`
- `elevated`
- `severe`

### Routing 侧
在 `build_routes_for_day(...)` 中：
- 若 signal 不是 `normal`，仅把 admitted flex 中带 `risky_flex` tag 的订单加入 `targeted_bias_ids`；
- insertion bias 只对这些 targeted ids 生效；
- 若 signal 为 `elevated / severe`，再额外增加 feedback bias。

这使得 bucket-aware bias 从“对所有候选一视同仁”变成“由 controller 风险判断驱动、只对高风险 flex 子集生效”。

---

## 3. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1043 | 1 | 99.90% | 219 | 2878.24 | 7 |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |
| OR-V4.1 | 1035 | 9 | 99.14% | 498 | 4778.20 | 5 |
| OR-V5 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |

---

## 4. 解释
### 4.1 OR-V5 相对 OR-V4.1 保持了服务，但改善了 depot 结构
相比 OR-V4.1：
- `service_rate` 持平：`99.14%`
- `expired` 持平：`9`
- `max_depot_penalty: 4778.20 -> 4399.96`
- `max_overloads: 5 -> 4`

这说明 controller-to-routing bucket feedback 确实带来了更好的 depot-safe 结构，而且没有进一步伤害服务。

### 4.2 但 OR-V5 仍未超过 OR-V2 的总体服务表现
相比 OR-V2：
- service 仍略低（`99.43% -> 99.14%`）
- expired 更高（`6 -> 9`）
- 但 depot metrics 更好（penalty / overload 更低）

因此 OR-V5 更像一个“结构更干净”的协同版本，而不是当前最佳服务版本。

### 4.3 研究意义
OR-V5 是当前 OR 支线里第一个真正体现“controller 与 routing 协同信号联动”的版本。它说明：
- 单独 local bias 不够；
- 让 controller 给出风险信号，再让 routing 对高风险 flex 子集做定向偏置，是更合理的协同方式；
- 该方向已经开始展现出比 OR-V4.1 更清晰的结构收益。

---

## 5. 当前结论
OR-V5 表明：
- **controller-to-routing bucket feedback 是值得继续深挖的主方向；**
- 它在不额外损伤服务的前提下，改善了 worst depot structure；
- 下一步应考虑进一步把这类 feedback 从 binary/ternary signal 升级为更精细的 bucket-pressure signal，或做 multi-instance 验证。
