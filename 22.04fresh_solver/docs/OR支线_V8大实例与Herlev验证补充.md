# OR 支线：V8 大实例与 Herlev 验证补充

## 1. 目的

在 `OR支线_V8动态shadow_price阶段总结_v1.md` 中，V8.2 已经在 West 上表现出当前最好的 service–smoothing trade-off。为了判断这条动态 shadow-price 路线是否只对 West 有利，还是具备更广的解释力，本补充进一步比较：

- **West**：高压大实例
- **Herlev**：中压实例
- **East**：相对宽松的大实例

目标不是简单问“V8.2 是否 everywhere 最优”，而是更进一步识别：

> **V8.2 的价值是否具有 regime dependence，以及这种 dependence 与不同实例的压力模式有何关系。**

---

## 2. 总结结论

本轮补充验证得到三个清晰结论：

1. **West：V8.2 是当前最好 trade-off**
   - 在保持接近 99.4% service rate 的同时，显著压低了 total / morning picking overload；
   - 也是目前最接近论文主文可用的 V8 版本。

2. **Herlev：V8.2 也改善了服务**
   - 相比 OR-V7，V8.2 提升了 service rate，并降低了 expired 与 deferred；
   - 说明动态 wave-smoothing 逻辑不只对 West 这种极端高压实例有效。

3. **East：V8.2 不具普适统治性**
   - East 从 OR-V7 的 100% SR 掉到约 99.72%；
   - 说明 V8.2 不是应在所有实例上一律强行激活的全局最优规则，而需要更强的 **regime-aware activation**。

---

## 3. 结果对照

### 3.1 West

| Variant | Assigned | Expired | SR | Deferred events | Total picking over | Morning picking over |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V7 | 4548 | 3 | 99.93% | 2477 | 15267.15 | 14901.30 |
| OR-V8 | 4414 | 137 | 96.99% | 2692 | 16224.23 | 16022.23 |
| OR-V8.1 | 4479 | 72 | 98.42% | 2672 | 14908.22 | 14633.64 |
| **OR-V8.2** | **4524** | **27** | **99.41%** | **2216** | **14256.81** | **13997.09** |

### 3.2 Herlev

| Variant | Assigned | Expired | SR | Deferred events |
| --- | ---: | ---: | ---: | ---: |
| OR-V7 | 1035 | 9 | 99.14% | 550 |
| **OR-V8.2** | **1039** | **5** | **99.52%** | **474** |

### 3.3 East

| Variant | Assigned | Expired | SR | Deferred events |
| --- | ---: | ---: | ---: | ---: |
| OR-V7 | 3268 | 0 | 100.00% | 1963 |
| **OR-V8.2** | **3259** | **9** | **99.72%** | **1680** |

---

## 4. 三个实例的阶段判断

### 4.1 West：V8.2 是当前最好 trade-off

West 的结果最清楚地支持 V8.2：

- V8 第一版证明了动态价格机制**确实能改曲线**，但过强，导致 service collapse；
- V8.1 证明放松后可以把 total / morning picking overload 压回 V7 以下；
- V8.2 则进一步把 service rate 拉回到约 **99.41%**，同时保持 curve smoothing gain。

也就是说，West 上最重要的不是“有没有 smoothing”，而是：

> **能否在削峰的同时不把 throughput 压垮。**

V8.2 当前是最成功的一版，因为它第一次实现了：
- 服务率接近原强基线；
- 06:00 主峰仍明显低于 V7；
- total / morning overload 都低于 V7；
- 又没有像 V8 那样把主峰粗暴推迟到 09:00。

因此，West 上的结论非常明确：

> **V8.2 是当前动态 shadow-price 路线中最好的 service–smoothing trade-off 版本。**

---

### 4.2 Herlev：V8.2 也改善了服务

Herlev 的结果说明，V8.2 不是只在 West 上有效：

- `assigned: 1035 -> 1039`
- `expired: 9 -> 5`
- `deferred events: 550 -> 474`

这意味着：
- Herlev 虽然不是 West 那种极端高压大实例，
- 但它仍存在足够明显的 depot/picking 波动，
- 使得 bucket-level smoothing 逻辑能够真正帮到服务结果。

换句话说：

> **V8.2 不只是“大实例特攻”，它对中压实例也能有实质改善。**

这对于论文非常有价值，因为它说明：
- V8.2 的机制不是完全依赖 West 特有结构；
- 它至少对“中压且存在可平滑波峰”的实例具备一定泛化性。

---

### 4.3 East：V8.2 不具普适统治性

East 的结果则给出一个重要边界：

- OR-V7：`3268 / 3268 = 100%`
- OR-V8.2：`3259 / 3268 ≈ 99.72%`

虽然：
- deferred events 降低了，

但同时：
- expired 从 `0` 变成 `9`，
- 也就是说出现了真实 service loss。

这说明：

> **在 East 这种相对宽松实例上，V8.2 的 smoothing 机制并不是“免费收益”，而是会引入不必要的 conservatism。**

因此不能把 V8.2 表述成：
- “一个 everywhere better 的 universal improvement”，

而更准确的定位应是：

> **一个对 pressure-sensitive regime 更有价值的动态控制机制。**

---

## 5. Herlev / West 与 East 的压力模式差异

这是本补充最关键的部分。

V8.2 在 West 与 Herlev 上有效、在 East 上不占优，并不是随机现象，而是与三者的**压力模式（pressure regime）**差异一致。

### 5.1 West：高压、强 morning-wave、明显 picking-dominant

West 的 bucket-level 诊断已经明确表明：

- 主导瓶颈是 **picking**，不是 gate，也不是 staging；
- 约 **97.6%** 的 picking overload 发生在 12:00 前；
- 峰值集中在 **05:30–06:15**；
- 原始曲线存在非常突出的首波发车前 surge。

这类实例的本质是：

> **仓内生产速率与路由释放节奏之间存在严重失配。**

因此对 West 来说，动态 shadow-price 的作用非常自然：
- 它能识别最危险的 high-utilization picking buckets；
- 并把部分最危险的 route construction pressure 从红区桶中挤出去；
- smoothing gain 是真实可兑现的。

### 5.2 Herlev：中压、可被平滑、仍有可见 depot pressure

Herlev 虽然不如 West 极端，但它并不是低压实例：

- 它在 OR-V7 下仍有 `expired = 9`、`deferred = 550`；
- 说明 depot-side pressure 足以影响服务；
- 但其压力不像 West 那样“尖刺极端且持续高压”，而更像一个**中压、可调节、可被平滑改善**的 regime。

这意味着：
- V8.2 的动态价格不会像在 East 那样变成多余的保守控制；
- 也不会像 V8 第一版在 West 上那样必须面对极端结构风险；
- 它更像一个适度的 bucket-level guidance，因而能改善服务而不至于大幅牺牲 throughput。

因此，Herlev 可以理解为：

> **中压且对 smoothing 有响应的实例。**

### 5.3 East：相对宽松、原本 already feasible、smoothing gain 小于 conservatism cost

East 的信号与前两者不同：

- OR-V7 已经达到 `100%` SR；
- 这说明在当前模型下，East 的主要问题不是“必须强力削峰才可执行”；
- 相反，它更像一个**容量较宽松、原 baseline 已足够可行**的 regime。

在这种情况下，V8.2 的动态 shadow-price 机制会出现一个典型副作用：

- 系统仍然识别到某些 picking pressure；
- 但这些 pressure 未必已经严重到值得牺牲服务；
- 于是 smoothing bias 带来的收益，小于其引入的 conservatism cost。

也就是说，East 的问题不是“缺少 smoothing”，而是：

> **不该在一个 already-loose regime 上过度激活 smoothing mechanism。**

因此 East 的最重要启示是：

> **V8.2 需要 regime-aware activation，而不能在所有实例上以相同强度开启。**

---

## 6. 由此得到的研究结论

综合 West / Herlev / East，可以得到一个比“V8.2 好不好”更高级的结论：

> **动态 shadow-price 的价值具有明显的 regime dependence。**

更具体地说：

- 当实例呈现 **high-pressure / wave-dominant / picking-sensitive** 特征时（如 West），V8.2 的 smoothing 逻辑最有价值；
- 当实例处于 **medium-pressure but still depot-sensitive** 特征时（如 Herlev），V8.2 也能产生改善；
- 当实例已处于 **relatively loose / already-feasible** 状态时（如 East），V8.2 不具普适统治性，甚至会带来不必要的 service loss。

这使得论文中的表述可以从“某个版本更强”升级为：

> **不同 instance regime 需要不同强度的动态资源价格激活策略。**

---

## 7. 对后续算法设计的启示

基于这一轮验证，下一步最合理的不是继续把 V8.2 当成无条件默认主线，而是：

### 7.1 做 regime-aware activation

让 V8.2 不再一律全强度开启，而是根据实例/前一日 diagnostics 决定是否激活、激活多强，例如：

- 若 `morning picking pressure score` 很高 → 强激活 V8.2；
- 若 pressure 虽存在但 service 已很稳 → 弱激活；
- 若已明显 loose 且 baseline 几乎无 service loss → 几乎关闭 dynamic shadow price。

### 7.2 区分“必须削峰”与“没必要过控”

West/Herlev/East 的差异已经说明：
- 不是所有 picking pressure 都值得用服务率去换；
- 只有当 morning surge 真正主导可执行性时，V8.2 才应强介入。

### 7.3 把 V8.2 定位为“机制代表版”而非“最终 universally best”

当前更合理的结构是：
- **West**：V8.2 作为最好 trade-off 的代表；
- **Herlev**：V8.2 作为机制能改善服务的补充证据；
- **East**：作为 regime-aware activation 必要性的反例。

---

## 8. 可直接用于论文的表述

可写成：

> West, Herlev, and East jointly show that the value of dynamic shadow pricing is regime-dependent rather than universally dominant. On West, where the system is clearly picking-dominant and morning-wave constrained, V8.2 delivers the best service–smoothing trade-off so far. On Herlev, which is less extreme but still depot-sensitive, the same mechanism also improves service outcomes. By contrast, East already operates in a relatively loose regime under OR-V7, so activating V8.2 at similar strength introduces unnecessary conservatism and causes avoidable service loss. This suggests that dynamic shadow pricing should be paired with regime-aware activation rather than applied uniformly across all instances.

对应中文可写成：

> West、Herlev 与 East 的联合验证表明，动态 shadow-price 的价值具有明显的 regime dependence，而非普适统治性。对于 West 这类已明确呈现 picking-dominant 且受 morning wave 主导的高压实例，V8.2 给出了当前最好的 service–smoothing trade-off；对于 Herlev 这类压力较弱但仍 depot-sensitive 的中压实例，V8.2 也带来了正向改善；而对于 East 这类在 OR-V7 下已较宽松、已接近 fully feasible 的实例，以相近强度激活 V8.2 会引入不必要的 conservatism，并产生可避免的 service loss。因此，动态 shadow-price 更适合与 regime-aware activation 结合，而非统一强度地施加于所有实例。
