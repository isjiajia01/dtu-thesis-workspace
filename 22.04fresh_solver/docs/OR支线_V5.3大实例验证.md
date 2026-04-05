# OR 支线：V5.3 在 East / West 上的验证

## 1. 目的
在 Herlev 上，OR-V5.3 通过 refined resource-usage proxies 显著改善了 V5.2，说明：
- shadow-price-like 内生化是有效的；
- 关键杠杆在资源使用代理质量。

本轮验证的目标是检查：
> 这种 gain 能否在更大实例 East / West 上站住。

对照对象：
- East：`OR-V2` vs `OR-V5` vs `OR-V5.3`
- West：`OR-V2` vs `OR-V5` vs `OR-V5.3`

---

## 2. East 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 3268 | 0 | 100.00% | 1865 | 30752.72 | 13 | 431.4 |
| OR-V5 | 3268 | 0 | 100.00% | 1963 | 29894.08 | 14 | 488.7 |
| OR-V5.3 | 3268 | 0 | 100.00% | 1963 | 30119.88 | 14 | 418.1 |

### East 解释
- 三者在服务层面完全一致；
- V5.3 的 depot penalty 介于 V2 与 V5 之间；
- 没有出现 Herlev 那种“V5.3 显著改变 trade-off”的效果。

结论：
- 在 East 上，V5.3 没有显示出明显额外优势；
- East 仍属于当前 OR 分支差异不大的相对宽松 regime。

---

## 3. West 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 4548 | 3 | 99.934% | 2477 | 22860.08 | 23 | 626.6 |
| OR-V5 | 4547 | 4 | 99.912% | 2623 | 24102.64 | 24 | 689.6 |
| OR-V5.3 | 4473 | 78 | 98.286% | 2696 | 19244.68 | 24 | 596.4 |

### West 解释
- V5.3 在 West 上出现了明显的服务坍塌：
  - `expired: 4 -> 78`
  - `SR: 99.91% -> 98.29%`
- 同时 depot penalty 确实下降：
  - `24102.64 -> 19244.68`

这说明 refined shadow-price proxies 在 West 上变成了一个过强的“资源价格闸门”：
- 它成功压下了 depot pressure；
- 但以明显牺牲服务为代价；
- 当前 price internalization 对大实例高压 regime 还不够稳健。

---

## 4. 综合结论
### 4.1 V5.3 的 gain 目前并没有稳定跨实例迁移
- Herlev：显著正向
- East：几乎无差别
- West：明显负向（服务坍塌）

### 4.2 这说明什么
这说明当前 refined proxy 的研究方向是对的，但：
- 资源价格一旦进入高压大实例，当前 price magnitudes / usage proxies 会过度放大 depot-safe 偏好；
- 结果是 depot structure 改善，但服务目标被过度牺牲。

### 4.3 学术意义
这不是简单的“V5.3 失败”，而是一个很有价值的发现：
> **proxy 质量是关键，但 proxy 的跨实例稳定性同样关键。**

也就是说，shadow-price 路线不仅需要“更像资源使用”，还需要：
- 在不同实例压力水平下不过度失真；
- 避免在高压 regime 中把资源价格推成近似 hard gate。

---

## 5. 当前判断
- OR-V2 仍是当前最稳的大实例 OR 主保留版本；
- OR-V5 保留为机制探索版本；
- OR-V5.3 证明了 refined shadow-price 思路在 Herlev 上很强，但目前还不能直接当跨实例版本。

## 6. 下一步建议
若继续走 V5.3 路线，更合理的方向不是简单加大/减小价格强度，而是：
1. 对 shadow-price 使用做 instance-aware normalization；
2. 对资源价格增加服务保护（例如 protected / near-deadline shield）；
3. 或只在 elevated/severe 且特定资源模式下局部激活 refined price，而不是全程统一启用。
