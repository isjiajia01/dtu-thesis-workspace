# OR 支线实验 v5.1：narrow controller-to-routing feedback

## 1. 目的
在 OR-V5 的 controller-to-routing bucket feedback 基础上，进一步缩窄反馈目标：
- 不再对所有 `risky_flex` 子集施加 feedback bias；
- 只针对 `risky_flex` 中同时具有 `trip2_sensitive` 或 `late_window` 特征的子集；
- 同时减弱 feedback / heavy / staging bias 权重。

目标是检验：
> OR-V5 的结构收益是否来自过强的广覆盖 bias，还是来自真正精准 targeting。

输出：
- `results/raw_runs/herlev_multiday_or_v5_1_julia.json`

---

## 2. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |
| OR-V5 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |
| OR-V5.1 | 1032 | 12 | 98.85% | 554 | 4642.76 | 4 |

---

## 3. 解释
OR-V5.1 相比 OR-V5：
- 服务更差（`99.14% -> 98.85%`）
- max depot penalty 反而回升（`4399.96 -> 4642.76`）
- overload bucket 持平（`4 -> 4`）

这说明当前 OR-V5 的更广泛 `risky_flex` feedback targeting 反而更有效；
把 feedback 目标缩得过窄，会同时损失服务与 depot 结构。

---

## 4. 当前结论
基于 Herlev：
- OR-V5 目前仍是“结构更干净”的最佳 controller-to-routing 协同版本；
- OR-V5.1 说明当前 feedback 不宜收得过窄；
- 下一步若继续基于 V5 探索，更合理的是提升信号质量（更细粒度 bucket pressure），而不是继续缩窄受控子集。
