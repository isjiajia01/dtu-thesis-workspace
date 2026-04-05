# OR 支线实验 v4：bucket-aware insertion scoring

## 1. 目的
把 OR 内生化从“后端 veto”进一步前移到 route construction 阶段：

> 在 insertion scoring 中直接对晚窗、trip2、重货、以及高 staging-risk 的候选施加 bias，尽量减少高风险结构在构造阶段被建立出来。

对应脚本：
- `src/algorithms/fresh_solver/julia/scripts/run_multiday_or_v4.jl`

输出：
- `results/raw_runs/herlev_multiday_or_v4_julia.json`

---

## 2. 实现方式
在 `RoutingConfig` 中新增：
- `bucket_aware_insertion_bias`
- `late_bucket_start_min`
- `trip2_late_bias_weight`
- `heavy_late_bias_weight`
- `staging_risk_bias_weight`

在 `routing.jl` 中新增 `insertion_bucket_bias(...)`，并把该 bias 加到：
- 现有 route insertion penalty
- new-route seed penalty

当前 bias 逻辑主要惩罚：
- late bucket + trip2
- late bucket + heavy order
- late bucket + high staging-risk route volume

---

## 3. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1043 | 1 | 99.90% | 219 | 2878.24 | 7 |
| Strict v1 | 1031 | 13 | 98.75% | 915 | 4439.76 | 3 |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |
| OR-V4 | 1025 | 19 | 98.18% | 535 | 4681.28 | 5 |

---

## 4. 解释
### 4.1 OR-V4 取得了“更低部分 depot 风险，但更差服务”的结果
相比 OR-V2：
- `service_rate: 99.43% -> 98.18%`
- `expired: 6 -> 19`
- `max_depot_penalty: 4983.48 -> 4681.28`
- `max_overloads: 6 -> 5`

这说明当前 insertion bias 确实在更早阶段改变了结构，但它过于保守，明显牺牲了服务。

### 4.2 启示
bucket-aware insertion scoring 方向本身是有效的，因为：
- depot metrics 发生了方向性改善；
- 说明前移 bias 已经成功改变 route construction；

但当前 bias 权重太强、太粗，导致：
- 它在构造阶段过早抑制了大量本来还能接受的服务机会；
- 还没有形成“结构变好且服务保持”的平衡点。

### 4.3 这比 OR-V1 更有研究价值
OR-V1 只是整体更保守；
OR-V4 则证明：
- **构造阶段 bias 确实是有杠杆的位置；**
- 只是当前 bias 设计还不够精细。

---

## 5. 下一步建议
### OR-V4.1：targeted insertion bias
把当前粗粒度 bias 缩成更针对性的模式：
- 只惩罚 `late bucket + trip2 + risky flex`；
- 不普遍打压所有 late/heavy 结构；
- 减小 staging-risk bias 权重。

### OR-V5：controller-to-routing bucket feedback
让 controller 输出 bucket-risk signal，只对高风险 flex 子集施加 insertion bias。

---

## 6. 当前结论
OR-V4 表明：
- **route construction 是正确的前移发力点；**
- 但当前 bucket-aware insertion bias 过于粗糙，下一步需要转向更 targeted 的 bias 设计。
