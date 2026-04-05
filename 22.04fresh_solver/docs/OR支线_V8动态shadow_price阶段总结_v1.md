# OR 支线：V8 动态 shadow-price 阶段总结 v1

## 1. 本阶段目标

V8 阶段的核心目标，不再只是笼统地“让 depot penalty 更低”，而是更具体地解决 West 大实例中已经被 bucket-level diagnostics 明确识别出的主导问题：

> **Picking overload 主要集中在首波发车前的 morning wave，尤其是 05:30–06:15。**

因此，V8 的目标是把 OR 支线从：
- 静态/粗粒度的 depot-aware bias
- 或 instance-level 的压力标签反馈

推进到：

> **基于 bucket-level utilization 的动态 shadow-price 内生化**

即：
1. 用上一日 diagnostics 生成每个时间桶、每类资源的动态价格；
2. 在 controller 层减少会继续推高高压桶的需求进入；
3. 在 routing insertion cost 中显式计入候选解对高压 bucket 的边际资源代价；
4. 观察其是否能够真正实现 West morning picking wave 的“削峰平谷”。

---

## 2. 机制定义

V8 在 Julia 中实现了第一版动态 shadow-price 机制，支持以下可配置超参数：

- `shadow_price_activation_utilization`
- `shadow_price_convex_gamma`
- `shadow_price_peak_eta`
- `alpha_gate`, `alpha_picking`, `alpha_staging`
- `beta_gate`, `beta_picking`, `beta_staging`

其思想是：

- 当某资源桶 utilization 低于阈值 `tau` 时，不激活价格；
- 当 utilization 超过阈值后，按凸函数逐步抬价；
- 当 utilization 超过 1（进入 overload 区间）后，再由 `beta` 项进一步放大峰值惩罚；
- controller 与 routing 都读取上一日 bucket-level diagnostics 生成的动态价格图。

这一机制的价值在于：
- 不再手写 `if West then picking_bias`；
- 而是统一地让系统根据 diagnostics 自动决定该强调 gate / picking / staging 哪一个资源；
- 从论文角度，它更接近“通用机制设计”，而非 case-specific tuning。

---

## 3. West 的前置诊断事实

在进入 V8 之前，West OR-V7 的 bucket-level 诊断已经得到一个关键发现：

- `total_picking_over = 15267.15`
- `morning_picking_over = 14901.30`
- `midday_picking_over = 365.85`
- `late_picking_over = 0`

也即：

> **约 97.6% 的 picking overload 发生在 12:00 前，主峰集中于 05:30–06:15。**

这说明 West 的问题不是“全天总产能缺口”，而是典型的：

> **first-wave dispatch preparation surge / morning wave smoothing problem**

因此，V8 的评估重点不应只看 service rate，还应同时看：
- 是否削弱原始 06:00 尖峰；
- 是否避免把压力粗暴推迟成新的 08:00–09:00 峰；
- 是否在保持高 service 的同时降低 total / morning picking overload。

---

## 4. V8 / V8.1 / V8.2 结果总表

| Variant | Assigned | Expired | SR | Deferred events | Total picking over | Morning picking over | Key curve behavior |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| V7 | 4548 | 3 | 99.93% | 2477 | 15267.15 | 14901.30 | 原始 06:00 尖峰很高 |
| V8 | 4414 | 137 | 96.99% | 2692 | 16224.23 | 16022.23 | 过强抑制，峰值被推到 08:00–09:15 |
| V8.1 | 4479 | 72 | 98.42% | 2672 | 14908.22 | 14633.64 | 06:00 spike 明显削弱，但出现较强 08:00 次峰 |
| V8.2 | 4524 | 27 | 99.41% | 2216 | 14256.81 | 13997.09 | 保住 morning smoothing，同时显著恢复 service |

---

## 5. 分阶段解读

### 5.1 V8：第一版动态价格机制“有作用，但过强”

V8 第一版已经证明：
- bucket-level dynamic shadow price 会改变路线结构；
- 它不是无效机制，而是确实能重塑 picking curve。

但问题也非常明显：
- service rate 从接近 100% 掉到约 96.99%；
- total / morning picking overload 不降反升；
- 原本 05:30–06:15 的峰值被粗暴推迟到 08:00–09:15。

这说明：

> **第一版 V8 不是没有“削峰”，而是通过过度控制把波峰“搬家”了。**

也就是说，V8 的问题不在于动态价格机制本身，而在于：
- controller clipping 太硬；
- `beta_picking` 太大；
- routing dynamic price 强度过高。

---

### 5.2 V8.1：开始出现正确方向的 service–smoothing trade-off

V8.1 通过：
- 降低 controller 侧 clipping；
- 降低 `beta_picking`；
- 轻微放松 routing dynamic shadow price；

使结果显著改善：
- service rate 回升到约 98.42%；
- total / morning picking overload 都降到 V7 以下；
- 原始 06:00 spike 明显被压低。

但 V8.1 仍存在一个结构问题：
- 压力虽然没像 V8 那样崩到 09:00，
- 但仍有较明显的 `08:00` 次峰。

因此 V8.1 更像：

> **它已经证明“削峰平谷”方向成立，但还没找到最优平衡点。**

---

### 5.3 V8.2：当前最有价值的版本

V8.2 进一步放松了：
- controller dynamic shadow clipping；
- routing dynamic price 强度；
- peak amplification；

同时增强了：
- service shield；
- refill throughput；
- 在 depot-safe 前提下的服务恢复能力。

结果是：
- service rate 回升到约 **99.41%**；
- total picking overload 降到 **14256.81**；
- morning picking overload 降到 **13997.09**；
- 都低于 V7；
- 原始 `06:00` 尖峰仍被明显压低：
  - `V7: 1990.4`
  - `V8.2: 1637.08`

更重要的是：
- V8.2 没有像 V8 那样把主峰过度推迟到 09:00；
- 也没有像 V8.1 那样过度制造一个新的 08:00 次峰；
- 它更像是在保持 morning-wave 主结构的同时，让曲线变“矮一点、宽一点”。

因此当前最合理的阶段判断是：

> **V8.2 是目前 V8 系列中最接近“论文主文可用版”的版本。**

---

## 6. 关键 curve-level 证据

聚合 bucket 曲线的 top peak 对比如下：

### V7
- `06:00 -> 1990.4`
- `05:45 -> 1716.22`
- `05:30 -> 1478.97`

### V8
- `09:00 -> 1319.5`
- `09:15 -> 1119.72`
- `08:00 -> 1070.23`

### V8.1
- `05:45 -> 1512.34`
- `05:30 -> 1140.56`
- `06:00 -> 923.7`
- `08:00 -> 906.67`

### V8.2
- `06:00 -> 1637.08`
- `05:30 -> 1321.62`
- `05:45 -> 1218.09`
- `05:00 -> 965.62`

这个对比说明：

1. **V8**：过拟合式过控，把峰值推迟成新的 late-morning peak；
2. **V8.1**：削峰有效，但存在次峰重分布；
3. **V8.2**：保留了削峰，但波形更稳定、服务更高。

因此，当前最值得写进论文的说法是：

> 动态 shadow-price 的价值，不在于简单“把峰值推后”，而在于在控制强度适当时，实现更优的 service–smoothing trade-off。

---

## 7. 当前阶段结论

### 7.1 已经确认的结论

1. West 的主导瓶颈确实是 **morning picking wave**，不是 gate，也不是全天均匀产能缺口；
2. bucket-level dynamic shadow price 机制不是空想，确实能重塑 picking curve；
3. 该机制若过强，会把 morning spike 粗暴推迟成新的 08:00–09:00 峰；
4. 经适度放松后（V8.2），可以在保持较高 service 的同时，把 total / morning picking overload 压到 V7 以下；
5. 因此，V8.2 说明：

> **动态资源价格机制可以在不彻底压制 throughput 的前提下，缓解首波发车前的 picking surge。**

### 7.2 当前最合适的定位

- **稳定主线参考**：OR-V2 / OR-V7 一类相对稳健版本
- **机制探索主代表**：V8.2
- **失败但有价值的对照**：V8（证明过强 dynamic price 会导致 bad peak migration）

---

## 8. 论文中的推荐表述

可以写成：

> West 的实验进一步表明，动态 shadow-price 机制并不必然以显著牺牲服务率为代价。经过适度放松 controller clipping 与 peak amplification 后，V8.2 在保持约 99.4% service rate 的同时，将 total picking overload 与 morning picking overload 均压低至 V7 以下，并显著削弱了原始 06:00 波峰。这支持本文的判断：West 的主要问题不是全天总产能不足，而是首波发车前的时域波峰过高，因此优化重点应从“总量压缩”转向“波峰平滑”。

---

## 9. 下一步建议

1. 把 V7 / V8 / V8.1 / V8.2 的曲线图正式画出来，作为 thesis 的核心图之一；
2. 在 East 上验证 V8.2 是否不会引入不必要的 service loss；
3. 若继续优化，可优先探索：
   - 更精细的 bucket-aware controller budget；
   - 更显式地利用 staging slack，而不是仅靠 picking price 间接调节；
   - 对 V8.2 做 instance-aware normalization，提升跨实例稳定性。
