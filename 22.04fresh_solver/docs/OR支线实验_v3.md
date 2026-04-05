# OR 支线实验 v3：refill veto under depot stress

## 1. 目的
在 OR-V2 的 severe bucket guard 基础上，进一步把 depot stress 对 refill 的影响单独显式化：

> 若 refill 候选会使当前方案的 `worst_bucket_penalty` 超过基线 worst bucket 超过容忍增量，则直接拒绝该 refill。

目标是检验：
- OR-V2 的结构化 bucket 控制是否还不够；
- refill 是否仍在放大 worst bucket；
- 单独卡住“worst bucket 放大型 refill”是否会进一步改善 trade-off。

对应脚本：
- `src/algorithms/fresh_solver/julia/scripts/run_multiday_or_v3.jl`

输出：
- `results/raw_runs/herlev_multiday_or_v3_julia.json`

---

## 2. 实现方式
在 `RoutingConfig` 中新增：
- `refill_worst_bucket_veto`
- `refill_worst_bucket_growth_tolerance`

并在 refill acceptance 中加入：
- 若 `trial_worst_bucket_penalty > base_worst_bucket_penalty + tolerance`，则拒绝 refill。

这一步比 OR-V2 更聚焦于：
- **refill 阶段** 的 worst-bucket 风险放大。

---

## 3. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1043 | 1 | 99.90% | 219 | 2878.24 | 7 |
| Strict v1 | 1031 | 13 | 98.75% | 915 | 4439.76 | 3 |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |
| OR-V3 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |

---

## 4. 解释
### 4.1 OR-V3 与 OR-V2 完全一致
在 Herlev 上，OR-V3 与 OR-V2 的结果完全相同。

这意味着：
- 当前 OR-V2 的 severe bucket guard 已经把会明显恶化 worst bucket 的 refill 候选基本挡住了；
- OR-V3 额外增加的 refill-specific veto 在该实例上没有继续改变行为。

### 4.2 启示
这说明当前瓶颈不再是“refill 仍在显著放大 worst bucket”，而更可能是：
- 更早的 insertion / route construction 阶段就已经决定了结构；
- 后续 refill 已经没有太多高风险自由度；
- 下一步该把 OR 内生化继续往更早阶段推进，而不是继续在 refill acceptance 上叠 veto。

---

## 5. 下一步建议
### OR-V4：bucket-aware insertion scoring
把晚窗 / trip2 / staging-risk / severe-bucket pressure 更直接地写进 insertion bias 或 regret selection，而不是仅在 split/refill 后端 veto。

### OR-V5：controller-to-routing bucket feedback
让 controller 输出更明确的 bucket-risk signal，直接影响 route seeding / route type selection。

---

## 6. 当前结论
OR-V3 结果表明：
- refill-specific worst-bucket veto 本身不是当前的主要增益点；
- OR 主线应继续向更早的 route construction / insertion 阶段推进结构化内生化。
