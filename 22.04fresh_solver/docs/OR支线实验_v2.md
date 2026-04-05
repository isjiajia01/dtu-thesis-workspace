# OR 支线实验 v2：severe bucket guard

## 1. 目的
在 OR-V1 的基础上，不再采用“全面更保守”的粗放策略，而是引入一个更结构化的前移机制：

> **severe bucket guard**：当 split / refill 候选会把当前方案的 worst depot bucket penalty 推高到严重阈值之上时，直接 veto。

这是一种 hard-like guard：
- 不再只是整体提高 depot proxy penalty；
- 而是针对最危险的时间桶做结构化否决。

对应脚本：
- `src/algorithms/fresh_solver/julia/scripts/run_multiday_or_v2.jl`

输出：
- `results/raw_runs/herlev_multiday_or_v2_julia.json`

---

## 2. 实现方式
在 `routing.jl` 中新增：
- `routing_bucket_stats(...)`
- `worst_bucket_penalty`
- `overload_bucket_count`

并在：
- split acceptance
- refill acceptance

中加入 severe bucket veto 逻辑：
- 若 trial 方案的 `worst_bucket_penalty` 高于 `max(severe_threshold, base_worst_bucket_penalty)`，则拒绝该候选。

这代表 OR 主线从“全局更紧”转向“针对最坏 bucket 的结构化前移控制”。

---

## 3. Herlev 结果对比

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1043 | 1 | 99.90% | 219 | 2878.24 | 7 |
| Strict v1 | 1031 | 13 | 98.75% | 915 | 4439.76 | 3 |
| OR-V1 | 1026 | 18 | 98.28% | 600 | 5061.20 | 5 |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |

---

## 4. 解释
### 4.1 OR-V2 明显优于 OR-V1
相比 OR-V1：
- SR 回升：`98.28% -> 99.43%`
- expired 降低：`18 -> 6`
- deferred events 降低：`600 -> 528`

这说明 severe bucket guard 比“整体更保守”更接近正确方向。

### 4.2 但 OR-V2 还没有真正赢过 baseline
相比 baseline：
- service 仍略低；
- max depot penalty 仍更高；
- max overload 也没有明显压下去。

因此，当前 severe bucket guard 说明了方向对，但实现还不够强。

### 4.3 关键启示
OR 主线下一步应继续沿：
- **bucket-aware**
- **structure-aware**
- **局部 veto / acceptance redesign**

而不是回到单纯整体 tightening。

---

## 5. 下一步建议
### OR-V3：refill veto under depot stress
在 severe bucket guard 之外，再专门约束 refill 对 worst bucket 的二次放大。

### OR-V4：bucket-aware insertion scoring
把晚窗 / trip2 / high-staging-risk 直接写进 insertion bias，而不只是接受阶段 veto。

---

## 6. 当前结论
OR-V2 证明：
- **结构化前移控制比粗放全局收缩更有效；**
- 但当前 bucket guard 还只是第一步，尚未形成足够强的 depot-aware 内生化方案。
