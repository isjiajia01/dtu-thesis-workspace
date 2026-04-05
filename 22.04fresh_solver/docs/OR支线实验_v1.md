# OR 支线实验 v1：更早 depot-aware admission + routing tightening

## 1. 目的
作为 `OR / 仓库约束更深内生化` 支线的第一步，先不改主架构，只通过配置把 depot 风险更早地推入：
- controller admission
- routing route packing
- trip2 使用
- repair 风险惩罚

目标是检查：
> 更早 depot-aware 控制，是否能在不过度损失 service 的情况下改善 realism。

对应脚本：
- `src/algorithms/fresh_solver/julia/scripts/run_multiday_or_v1.jl`

输出文件：
- `results/raw_runs/herlev_multiday_or_v1_julia.json`

---

## 2. OR-V1 的关键改动
相对 baseline，OR-V1 主要做了：
- 更高 protected reserve / hard protected ratio
- 更低 flex admission cap / risky flex cap
- 更早触发 depot feedback clipping
- 更高 depot proxy penalty / trip2 penalty / service buffer
- 更保守的 split / refill 权重
- 更高 gate / picking / staging penalty

这代表一种“前移式内生化”尝试：
不是等 routing 完再修，而是更早让 controller 与 route construction 对 depot risk 做出反应。

---

## 3. Herlev 初步结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1043 | 1 | 99.90% | 219 | 2878.24 | 7 |
| Strict v1 | 1031 | 13 | 98.75% | 915 | 4439.76 | 3 |
| OR-V1 | 1026 | 18 | 98.28% | 600 | 5061.20 | 5 |

---

## 4. 解释
### 4.1 OR-V1 没有取得理想 trade-off
当前 OR-V1 相比 baseline：
- SR 明显下降；
- expired 增加；
- max overload 没有像 strict 那样进一步降到更低；
- max depot penalty 反而更高。

### 4.2 这说明什么
这说明“仅靠更保守 admission + 更高 route penalty”还不够。
换句话说：
- 只是更早收紧，不一定就能更好地协同；
- 如果前移控制过于粗暴，可能只会牺牲服务率，而没有真正改善 worst-bucket realism；
- 真正有效的 OR 内生化，可能需要更结构化的 bucket-aware acceptance / veto，而不是单纯整体收紧。

### 4.3 这不是坏结果
这个结果很有价值，因为它说明：
> OR 主线不应被简单理解为“更保守”。

真正要探索的是：
- 哪些 depot risk 该被前移；
- 以什么粒度前移；
- 如何让前移约束是“结构化协同”，而不是“全局收缩”。

---

## 5. 下一步更合理的 OR 实验
### OR-V2：severe bucket guard
把 severe overload bucket 变成 hard-like veto，而不是普遍提高整体保守度。

### OR-V3：refill veto under depot stress
当 refill 会进一步推高 worst bucket 时，直接禁止。

### OR-V4：bucket-aware insertion scoring
不只是提高整体 depot proxy penalty，而是显式对“晚窗 / trip2 / 高 staging 风险”结构打分。

---

## 6. 当前结论
OR 支线已经正式启动，但第一步结果说明：
- **正确方向不是简单整体收紧**；
- **更有前景的是结构化的、bucket-aware 的前移内生化。**
