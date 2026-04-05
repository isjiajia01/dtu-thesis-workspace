# OR 支线阶段总结 v1

## 1. 目的
本文档对当前 `22.04` 的 OR 支线进行阶段性收口，总结：
- OR-V1 ~ OR-V6 在 Herlev 上的演化结果；
- East / West 上的关键对照；
- 哪些方向被排除；
- 哪些方向应被主保留；
- 下一步如何继续迭代 V5。

本文档的角色不是最终论文定稿，而是当前研究推进中的“支线决策备忘录”。

---

## 2. 支线起点：为什么要开 OR 分支
当前 thesis 的主痛点不是“搜索还不够聪明”，而是：
1. 高 service rate 与非零 depot penalty 并存；
2. 后置 repair 虽然能改善结构，但不能完全闭合 execution realism；
3. 仓库约束（gate / picking / staging）尚未充分内生到 admission 与 route construction 中。

因此，OR 支线的核心问题被定义为：
> **如何把 depot-aware realism 更早地内生到 rolling controller + routing backend 中。**

这也是为什么当前支线优先走 OR，而不是直接转向 RL-ALNS 主线。

---

## 3. Herlev 上 OR-V1 ~ OR-V6 的主要结果

| Variant | Main idea | SR | Expired | Deferred events | Max depot penalty | Max overloads | 阶段判断 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| OR-V1 | 全局更早 depot-aware tightening | 98.28% | 18 | 600 | 5061.20 | 5 | 排除：过于粗暴 |
| OR-V2 | severe bucket guard | 99.43% | 6 | 528 | 4983.48 | 6 | 当前最稳服务型 OR 点 |
| OR-V3 | refill-specific worst-bucket veto | 99.43% | 6 | 528 | 4983.48 | 6 | 与 V2 相同，说明 refill 不是主杠杆 |
| OR-V4 | broad bucket-aware insertion bias | 98.18% | 19 | 535 | 4681.28 | 5 | 方向对，但 bias 太粗 |
| OR-V4.1 | targeted insertion bias | 99.14% | 9 | 498 | 4778.20 | 5 | 比 V4 合理，但仍不如 V2 |
| OR-V5 | controller-to-routing bucket feedback | 99.14% | 9 | 550 | 4399.96 | 4 | 当前最优结构型 OR 点 |
| OR-V5.1 | narrower V5 targeting | 98.85% | 12 | 554 | 4642.76 | 4 | 排除：targeting 过窄 |
| OR-V6 | fine-grained pressure score | 99.14% | 9 | 550 | 4399.96 | 4 | 与 V5 相同，说明 gain 来自 feedback structure 本身 |

---

## 4. Herlev 阶段结论

## 4.1 已经被排除的方向
### A. 粗暴全局 tightening（OR-V1）
结论：
- 只会损伤服务；
- 不能有效改善最关键的 depot structure；
- 不是正确的 OR 内生化方式。

### B. 继续在 refill 端堆 veto（OR-V3）
结论：
- 与 OR-V2 完全一致；
- 说明当前 refill 阶段已经不是主要杠杆点。

### C. 过窄的 feedback targeting（OR-V5.1）
结论：
- 同时损害服务与 depot structure；
- 当前 V5 的广义 risky-flex targeting 更合理。

---

## 4.2 已经确认有效的方向
### A. severe bucket guard（OR-V2）
说明：
- 结构化 veto 比全局收缩更有效；
- severe bucket 作为 hard-like guard 是合理的；
- 这是当前最稳、最可迁移的 OR 支线版本。

### B. route construction 是可发力的前移位置（OR-V4 / V4.1）
说明：
- broad insertion bias 太粗；
- 但 targeted insertion bias 明显比 broad bias 更好；
- 这证明 route construction 的确是 OR 内生化的有效杠杆位置。

### C. controller-to-routing feedback（OR-V5）
说明：
- 把 controller 风险判断显式传给 routing 是正确方向；
- 在不进一步损伤服务的前提下，可以改善 depot structure；
- 当前 V5 是“结构更干净”的最佳 Herlev OR 版本。

---

## 5. East / West 上 OR-V2 vs OR-V5

## 5.1 East
| Variant | SR | Expired | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 100.00% | 0 | 1865 | 30752.72 | 13 |
| OR-V5 | 100.00% | 0 | 1963 | 29894.08 | 14 |

结论：
- East 上二者服务完全相同；
- 结构差异很小；
- East 对当前 OR 分支变化不太敏感。

## 5.2 West
| Variant | SR | Expired | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 99.934% | 3 | 2477 | 22860.08 | 23 |
| OR-V5 | 99.912% | 4 | 2623 | 24102.64 | 24 |

结论：
- West 上 OR-V2 全面优于 OR-V5；
- Herlev 中 V5 的结构优势没有迁移到 West；
- 当前 V5 的反馈机制仍偏 Herlev-specific，泛化不稳。

---

## 6. 当前主保留版本与机制探索版本

## 6.1 当前主保留版本：OR-V2
理由：
1. 在 Herlev 上服务最稳；
2. East / West 上跨实例最稳；
3. severe bucket guard 机制足够结构化；
4. 没有出现 V5 那种“Herlev 结构更优、West 反而更差”的泛化问题。

### 当前定位
> **OR-V2 = 当前 OR 支线的主保留版本 / 稳定版本**

## 6.2 当前机制探索版本：OR-V5
理由：
1. 它第一次真正实现了 controller-to-routing feedback；
2. 在 Herlev 上改善了 depot structure；
3. 证明“controller 输出风险信号 → routing 对高风险 flex 子集做 targeted bias”是有价值的结构；
4. 虽然当前泛化不稳，但值得继续深挖。

### 当前定位
> **OR-V5 = 当前 OR 支线的机制探索版本 / 协同反馈版本**

---

## 7. 当前最重要的认识
当前问题已经不是：
- feedback 强度还不够；
- 只要再调大/调小几个权重就能泛化。

而是：
> **当前 V5 的 feedback 内容与作用时机还不够稳健，导致它在 Herlev 上有效，但在 West 上不泛化。**

因此，接下来继续迭代 V5 的原则应明确为：
1. **不是再微调强度；**
2. **而是重设计 feedback 的内容；**
3. **以及重设计 feedback 进入 routing 的时机。**

---

## 8. 下一步：如何继续迭代 V5

## 8.1 不建议做的事
- 继续只调 `controller_bucket_feedback_weight`
- 继续只调 targeted subset 大小
- 继续只做更细/更粗的 signal granularity

这些方向已经被 V5.1 / V6 基本说明：不是当前主要矛盾。

## 8.2 更合理的方向
### A. 重设计 feedback 内容
当前 V5 反馈的是“总体 bucket pressure”。
下一步更有价值的是让 feedback 携带更结构化的信息，例如：
- 当前压力主要来自 gate 还是 picking/staging；
- 压力主要出现在早桶还是晚桶；
- 哪类 route pattern（trip2 / late / heavy）正在主导 worst bucket。

### B. 重设计 feedback 作用时机
当前 V5 主要在 insertion bias 生效。
下一步可以考虑把 feedback 更早或更明确地进入：
- protected seeding
- flex admission ordering
- new-route selection
- route-type preference（trip1 / trip2 倾向）

### C. 做“模式驱动”而不是“强度驱动”
不是问：
- bias 再强一点会不会更好？

而是问：
- **不同 depot stress pattern 下，routing 应该改变哪类结构决策？**

---

## 9. 建议的下一实验方向
基于以上结论，下一步建议启动：

### OR-V7（建议方向）
**pattern-aware controller-to-routing feedback**

核心思想：
- controller 不只输出压力大小；
- 还输出“压力模式标签”；
- routing 根据模式只改对应结构决策。

示例：
- 若主要是 late-bucket gate congestion → 抑制 trip2 late departures；
- 若主要是 staging-driven overload → 抑制 high-volume late consolidation；
- 若主要是 picking-driven overload → 调整 protected seeding / route release structure。

---

## 10. 阶段一句话总结
当前 OR 支线已经完成从“粗暴 tightening”到“结构化协同反馈”的第一轮探索。结论是：
- **OR-V2 是当前最稳的主保留版本；**
- **OR-V5 是最值得继续深挖的机制探索版本；**
- **继续迭代 V5 的重点不应是调强度，而应是重设计 feedback 的内容与进入 routing 的时机。**
