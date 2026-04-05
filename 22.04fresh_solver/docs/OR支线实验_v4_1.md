# OR 支线实验 v4.1：targeted insertion bias

## 1. 目的
在 OR-V4 的 bucket-aware insertion scoring 基础上，把过于粗糙的 bias 收细为更有针对性的模式：
- 只重点惩罚 `late bucket + trip2 + risky flex`
- 不再普遍打压所有 late/heavy 结构
- 降低 staging-risk bias
- 对 `protected / near-deadline` 订单给出 bias relief

对应脚本：
- `src/algorithms/fresh_solver/julia/scripts/run_multiday_or_v4_1.jl`

输出：
- `results/raw_runs/herlev_multiday_or_v4_1_julia.json`

---

## 2. 实现方式
在 `RoutingConfig` 中新增/使用：
- `targeted_insertion_bias`
- `protect_near_deadline_bias_relief`

并将 `insertion_bucket_bias(...)` 分为两种模式：
1. broad mode（OR-V4）
2. targeted mode（OR-V4.1）

在 targeted mode 中：
- 主要对 `late departure + trip2 + risky_flex` 加强惩罚；
- 只有 `risky_flex + heavy` 才施加较轻的 heavy bias；
- 只有 `risky_flex + late + high-volume route` 才施加较轻的 staging bias；
- `near_deadline / hard_protected` 会获得 bias relief。

---

## 3. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1043 | 1 | 99.90% | 219 | 2878.24 | 7 |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |
| OR-V4 | 1025 | 19 | 98.18% | 535 | 4681.28 | 5 |
| OR-V4.1 | 1035 | 9 | 99.14% | 498 | 4778.20 | 5 |

---

## 4. 解释
### 4.1 OR-V4.1 明显优于 OR-V4
相比 OR-V4：
- `service_rate: 98.18% -> 99.14%`
- `expired: 19 -> 9`
- `deferred_events: 535 -> 498`
- `max_overloads: 5 -> 5`（保持）

这说明 targeted insertion bias 成功修复了 OR-V4 过于粗暴的问题。

### 4.2 但 OR-V4.1 仍未超过 OR-V2
相比 OR-V2：
- service 仍略低（`99.43% -> 99.14%`）
- max depot penalty 也仅略改善（`4983.48 -> 4778.20`）

因此，当前 targeted insertion bias 虽然比 broad insertion bias 更合理，但仍未形成优于 OR-V2 的整体 trade-off。

### 4.3 启示
这表明：
- route construction 确实是正确的前移发力点；
- 但 insertion bias 本身还不是足够强的最终机制；
- 更有前景的下一步可能是把 targeted bias 与更明确的 bucket signal / controller feedback 再耦合，而不是单独靠局部 penalty 调节。

---

## 5. 当前结论
OR-V4.1 证明：
- **从 broad bias 收细到 targeted bias 是正确方向；**
- 它明显缓和了 OR-V4 的服务损失；
- 但当前最佳 OR 支线点仍更接近 OR-V2，而不是 OR-V4.1。
