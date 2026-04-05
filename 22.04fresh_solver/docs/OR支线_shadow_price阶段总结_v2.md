# OR 支线 shadow-price 阶段总结 v2

## 1. 目的
本文档在 v1 的基础上，补充：
- `OR-V5.3` 的 East / West 验证；
- `OR-V5.4` 的 West 修复结果与 East 补充验证；
- `OR-V5.5` 的 follow-up 结果；
- 当前 shadow-price 路线的阶段性判断与下一步设计原则。

本文档的重点不是再罗列所有实验，而是把这条线当前已经学到的研究结论收成更稳定的机制认知。

---

## 2. 从 v1 到 v2：新增了什么
相较于 v1，本轮最重要的新信息是：
1. `V5.3` 在 Herlev 上非常强，但在 West 上发生明显服务坍塌；
2. `V5.4` 证明这种坍塌不是路线错误，而是缺少 normalization + service shield；
3. `V5.5` 说明继续在保护层上堆复杂度，并不会自动进一步改善；
4. 因此，shadow-price 路线当前的主要矛盾，已经从“有没有价格/代理够不够精细”转向“价格信号如何与服务目标更稳地耦合”。

---

## 3. 各版本阶段判断

## 3.1 OR-V5.2：quasi-shadow-price feedback
### 作用
- 把路线从 `label -> bias` 推进到 `resource pressure -> price-like cost`

### 结论
- 证明 shadow-price internalization 本身会实质改变行为；
- 但当前资源使用 proxy 还太粗。

### 角色定位
> **概念成立版本**

---

## 3.2 OR-V5.3：refined resource-usage proxies
### 作用
- gate / picking / staging 三类 proxy 从粗粒度启发式，升级到更贴 diagnostics 结构的代理

### Herlev
- `SR = 99.90%`
- `expired = 1`
- 近乎恢复 baseline service

### East
- 服务保持 `100%`
- 无明显额外收益

### West
- `expired = 78`
- `SR = 98.29%`
- 但 depot penalty 显著改善

### 结论
V5.3 是当前 shadow-price 路线里最关键的一次正向突破，因为它明确说明：
> **proxy quality is the key lever.**

但 West 的结果也说明：
> refined proxy 若无保护层，在高压实例上会把 shadow price 推成近似 hard gate。

### 角色定位
> **理论突破版本 / refined proxy 关键发现版本**

---

## 3.3 OR-V5.4：normalized shadow-price + service shield
### 作用
- 对 `lambda` 做 instance-aware normalization
- 对 protected / near-deadline / 高分订单做 service shield

### West
- `expired: 78 -> 10`
- `SR: 98.29% -> 99.78%`
- 同时 depot penalty 仍低于 OR-V2

### East
- 服务保持 `100%`
- 没有额外收益，但没有破坏性能

### 结论
V5.4 证明：
- V5.3 的 West 坍塌不是路线错，而是缺少 stabilization layer；
- normalization + service shield 是高压实例下使 shadow-price 路线变得“可用”的必要条件。

### 角色定位
> **高压实例 stabilization layer**

注意：
V5.4 不应被写成“所有实例统一更优版本”，而应写成：
> 它是在高压 regime 下保证 shadow-price 路线不失真的保护层。

---

## 3.4 OR-V5.5：regime-aware normalization + structured shield
### 作用
- 在 V5.4 基础上继续提高 normalization / shield 复杂度
- 尝试按 pressure mode 做更系统的缩放与分层 service protection

### West
- 相比 V5.4：
  - 服务更差
  - depot penalty 略回升
  - overload 略差

### 结论
V5.5 的结果非常重要，因为它表明：
> **继续在 stabilization layer 上堆复杂度，不会自动继续改善。**

这说明当前问题已经不是：
- normalization 还不够细
- shield 还不够复杂

而是：
> **价格信号本身与服务目标的耦合方式，仍然不够结构化。**

### 角色定位
> **边界发现版本 / 复杂保护层无自动收益的反例**

---

## 4. 当前最重要的学术结论

### 结论 1：不是“加价格项”就够了
shadow-price 路线当前最核心的机制发现，仍然是：
> **proxy quality, not merely adding price terms, is the key lever in shadow-price-based depot internalization.**

### 结论 2：高压实例需要 stabilization layer
West 结果已经说明：
- refined proxy 很强；
- 但如果不做 normalization + shield，会过激失真；
- shadow-price 路线在高压 regime 下必须有稳定化机制。

### 结论 3：当前主要矛盾已升级
经过 V5.5 后，现在更明确：
> 当前 shadow-price 路线的主要矛盾，不再是“有没有价格”或“proxy 是否够细”，而是“价格信号如何与服务目标更稳地耦合”。

这意味着下一步不应继续只是：
- 微调 `lambda_scale`
- 微调 `service_shield_relief_weight`
- 叠更多 normalization/shield 细节

而应转向：
- **更结构化的 price activation / service coupling 设计**

---

## 5. 当前版本定位（v2 更新）

### 当前主保留版本
- **OR-V2**
  - 仍是最稳的跨实例主线版本

### 当前 controller-routing 机制探索版本
- **OR-V5**
  - 证明 feedback structure 本身有价值

### 当前 shadow-price 理论突破版本
- **OR-V5.3**
  - 说明 refined proxies 是关键杠杆

### 当前高压实例可用化版本
- **OR-V5.4**
  - 说明 normalization + service shield 是高压 regime 的必要稳定层

### 当前边界发现版本
- **OR-V5.5**
  - 说明继续加复杂保护层并不会自动变好

---

## 6. 当前最推荐的下一步设计原则
基于 v2 阶段总结，下一步若继续沿 shadow-price 路线推进，设计原则应明确为：

1. **不再继续堆保护层复杂度；**
2. **不再只调强度；**
3. **转向更结构化的 price activation / service coupling。**

更具体地说，下一步应优先思考：
- price signal 是否只在某些 regime / 某些资源模式下局部激活；
- price 是否应更早进入 admission / seeding，而不是只在 insertion 阶段起作用；
- service-first 目标是否应以更显式的约束或 shield 逻辑与价格耦合，而不是只做 ex-post cost relief。

---

## 7. 一句话总结
shadow-price 路线目前已经从“概念探索”推进到“机制成形 + 边界显化”的阶段：
- `V5.2` 证明价格内生化有效；
- `V5.3` 证明 proxy 质量是关键；
- `V5.4` 证明高压实例需要 stabilization layer；
- `V5.5` 证明继续堆保护层复杂度并不能自动解决问题。

因此，当前这条线最重要的研究结论是：
> **shadow-price depot internalization is viable, but its next breakthrough requires more structured coupling between resource pricing and service protection, rather than merely stronger normalization or richer shields.**
