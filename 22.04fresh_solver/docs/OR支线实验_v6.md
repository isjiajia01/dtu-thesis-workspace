# OR 支线实验 v6：fine-grained bucket-pressure signal

## 1. 目的
在 OR-V5 的 controller-to-routing bucket feedback 基础上，把 controller 输出从三档分类信号升级为细粒度压力分数：
- `bucket_risk_signal` 仍保留为 `normal / elevated / severe`
- 新增 `bucket_pressure_score`，由上一日 depot penalty 与 overload bucket count 共同归一化形成
- routing 使用连续 pressure score 调整 targeted insertion bias 强度

目标是检验：
> 比起分档信号，细粒度压力分数是否能进一步改善 controller-to-routing 协同质量。

输出：
- `results/raw_runs/herlev_multiday_or_v6_julia.json`

---

## 2. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |
| OR-V5 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |
| OR-V6 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |

---

## 3. 解释
在 Herlev 上，OR-V6 与 OR-V5 完全一致。

这说明：
- 当前三档 `bucket_risk_signal` 已经足够覆盖 Herlev 上触发的主要反馈状态；
- 连续 pressure score 在该实例上没有带来额外可见行为变化；
- 当前 OR-V5 的改进主要来自“controller-to-routing feedback 这个结构本身”，而不是信号离散化是否足够细。

---

## 4. 当前结论
基于 Herlev：
- OR-V5 仍是当前最佳的“结构更干净”的 controller-to-routing 协同版本；
- OR-V6 说明更细粒度的 score 在 Herlev 上暂时没有额外增益；
- 若继续探索，下一步更有价值的是做 multi-instance 验证（East/West）或进一步改变信号内容，而不是仅改变 signal granularity。
