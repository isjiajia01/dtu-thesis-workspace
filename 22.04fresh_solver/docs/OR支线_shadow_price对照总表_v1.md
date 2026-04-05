# OR 支线 shadow-price 对照总表 v1

## 1. 目的
把当前 shadow-price 路线的关键版本与三实例结果收成一张 paper-facing 对照表，便于后续写作与继续迭代。

涉及版本：
- `OR-V5`：controller-to-routing feedback
- `OR-V5.2`：quasi-shadow-price feedback
- `OR-V5.3`：refined resource-usage proxies
- `OR-V5.4`：normalized shadow-price + service shield

---

## 2. Herlev

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V5 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |
| OR-V5.2 | 1038 | 6 | 99.43% | 580 | 4485.08 | 7 |
| OR-V5.3 | 1043 | 1 | 99.90% | 577 | 4424.36 | 5 |

### Herlev 结论
- `V5.2` 证明了从 label feedback 升级到 price-style internalization 会实质改变行为；
- `V5.3` 证明 refined proxies 是关键杠杆，几乎恢复 baseline-level service；
- 在 Herlev 上，当前最强 shadow-price 版本是 `V5.3`。

---

## 3. East

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 3268 | 0 | 100.00% | 1865 | 30752.72 | 13 |
| OR-V5.3 | 3268 | 0 | 100.00% | 1963 | 30119.88 | 14 |
| OR-V5.4 | 3268 | 0 | 100.00% | 1963 | 30428.28 | 15 |

### East 结论
- East 对 shadow-price 路线整体不敏感；
- `V5.3 / V5.4` 都未显示明显额外增益；
- `V5.4` 没有破坏服务，但更多是防守型保护层而非收益来源。

---

## 4. West

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 4548 | 3 | 99.934% | 2477 | 22860.08 | 23 |
| OR-V5.3 | 4473 | 78 | 98.286% | 2696 | 19244.68 | 24 |
| OR-V5.4 | 4541 | 10 | 99.780% | 2625 | 20942.56 | 24 |

### West 结论
- `V5.3` 在 West 上发生明显服务坍塌，但 depot penalty 改善显著；
- `V5.4` 通过 normalization + shield 成功修复大部分坍塌；
- 但 `V5.4` 仍未追平 `OR-V2` 的服务表现。

---

## 5. 当前整体判断

### 当前最关键机制发现
> **proxy quality, not merely adding price terms, is the key lever in shadow-price-based depot internalization.**

### 当前版本定位
- `OR-V2`：最稳主保留版本
- `OR-V5`：controller-to-routing 协同机制版本
- `OR-V5.3`：Herlev 上最强的 refined shadow-price 版本
- `OR-V5.4`：高压实例下的 stabilization layer

### 当前研究边界
- refined shadow-price 路线是成立的；
- 但它不是天然跨实例稳定；
- 高压实例需要更系统的 normalization regime 与更结构化的 service shield。

---

## 6. 下一步
下一阶段继续沿 shadow-price 路线推进时，重点应放在：
1. 更系统的 regime-aware normalization；
2. 更结构化的 service shield；
3. 避免在高压实例上把资源价格推成近似 hard gate。
