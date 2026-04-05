# OR 支线：V7 在大实例（East / West）上的初步验证

## 1. 目的
针对“Herlev 上 OR-V7 = OR-V5 是否只是因为实例压力不够强”的问题，进一步在更大实例 East / West 上验证 pattern-aware feedback（V7）是否会显现优势。

对照对象：
- `east_multiday_or_v5_julia.json` vs `east_multiday_or_v7_julia.json`
- `west_multiday_or_v5_julia.json` vs `west_multiday_or_v7_julia.json`

---

## 2. East 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V5 | 3268 | 0 | 100.00% | 1963 | 29894.08 | 14 | 488.7 |
| OR-V7 | 3268 | 0 | 100.00% | 1963 | 30338.44 | 15 | 428.2 |

### East 解释
- 服务完全一致；
- depot 结构并未改善，反而略差；
- 说明在 East 上，pattern-aware feedback 仍未形成有效额外杠杆。

---

## 3. West 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V5 | 4547 | 4 | 99.912% | 2623 | 24102.64 | 24 | 689.6 |
| OR-V7 | 4546 | 5 | 99.890% | 2623 | 24102.64 | 24 | 613.8 |

### West 解释
- V7 轻微劣于 V5；
- depot metrics 完全不变；
- 说明即使在更敏感的大实例上，当前“pressure mode 标签 + insertion bias 映射”仍未改变核心结构。

---

## 4. 阶段结论
1. `V7 = V5` 不是 Herlev 特例，在 East / West 上同样没有显现 pattern-aware 优势；
2. 这支持一个更强的研究判断：**当前问题不在于反馈标签是否足够丰富，而在于反馈耦合深度不够。**
3. 也就是说，单靠 metadata label → insertion bias 这一弱耦合路径，已经接近触顶。

---

## 5. 对下一步研究的启示
更合理的后续不应继续：
- 增加更多标签；
- 细化更多模式；
- 小幅调 bias 映射权重。

更有价值的方向是：
- 把 feedback 从 insertion bias 推向更早的 seeding / route-type selection；
- 或者从“标签反馈”升级为“价格反馈 / shadow-price-like signal”；
- 或者转向基于资源状态的 adaptive operator scheduling。
