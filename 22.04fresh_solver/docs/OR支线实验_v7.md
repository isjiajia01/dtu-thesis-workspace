# OR 支线实验 v7：pattern-aware controller-to-routing feedback

## 1. 目的
基于 OR-V5 的 controller-to-routing feedback，不再只传递“压力大小”，而进一步传递“压力模式”：
- 在 runner 中根据 depot diagnostics 判断上一日压力主导来源：`gate / picking / staging / balanced`
- controller 将 `pressure_mode` 连同 `bucket_pressure_score` 一并传给 routing
- routing 根据不同模式，对 targeted insertion bias 的 trip2 / heavy / staging 三类结构偏置做不同调整

目标是检验：
> 仅靠 pressure size 不够时，pattern-aware feedback 是否能改善 V5 的泛化问题。

输出：
- `results/raw_runs/herlev_multiday_or_v7_julia.json`

---

## 2. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |
| OR-V5 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |
| OR-V7 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |

---

## 3. 解释
在 Herlev 上，OR-V7 与 OR-V5 仍然完全一致。

这说明：
- 当前 V5 的 gain 主要来自“feedback structure 本身”；
- 仅增加 `pressure_mode` 作为额外模式标签，在 Herlev 上并没有改变可见行为；
- 这可能意味着：Herlev 上当前触发的 pressure mode 过于单一，或者 routing 中的结构模式映射还不够强。

---

## 4. 当前结论
OR-V7 说明：
- V5 的下一步不应只是往 metadata 里继续堆更多标签；
- 若要继续深挖 feedback 内容，可能需要更强地改变 feedback 的作用时机（如 seeding / route-type selection），而不只是 insertion bias 权重映射；
- 当前 OR-V5 仍是机制探索版本中的代表性版本。
