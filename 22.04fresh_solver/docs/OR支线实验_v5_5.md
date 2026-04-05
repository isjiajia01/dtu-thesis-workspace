# OR 支线实验 v5.5：regime-aware normalization + structured shield

## 1. 目的
在 V5.4 的基础上，进一步把 high-pressure stabilization 做得更系统化：
- 不只按总体压力缩放 shadow price；
- 还按 `pressure_mode` 做 regime-aware normalization；
- 同时把 service shield 从简单 protected relief 升级为更结构化的 shield：对 protected、高分订单、非 risky_flex 订单分层减免。

本轮继续以 West 为主验证。

---

## 2. West 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 4548 | 3 | 99.934% | 2477 | 22860.08 | 23 |
| OR-V5.4 | 4541 | 10 | 99.780% | 2625 | 20942.56 | 24 |
| OR-V5.5 | 4534 | 17 | 99.626% | 2619 | 21060.88 | 25 |

---

## 3. 解释
相比 V5.4：
- 服务更差（`expired 10 -> 17`）
- depot penalty 略回升（`20942.56 -> 21060.88`）
- overload 也略差（`24 -> 25`）

这说明当前更复杂的 regime-aware normalization + structured shield 组合并没有进一步改善 West，反而略微过拟合/过调节。

---

## 4. 当前结论
- V5.4 目前仍是高压实例稳定化的更优版本；
- V5.5 说明继续在“保护层设计”上加复杂度，并不自动带来收益；
- 当前更值得继续的方向，不是继续堆 normalization/shield 细节，而是回到更根本的问题：价格信号本身与 service target 的耦合方式是否需要更结构化设计。
