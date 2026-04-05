# OR 支线 shadow-price 路线阶段总结 v1

## 1. 目的
本文档对 OR 支线中从 `OR-V5` 延伸出的 shadow-price 路线做阶段性收口，总结：
- 为什么从 label feedback 转向 quasi-shadow-price feedback；
- `V5 / V5.2 / V5.3 / V5.4` 的关键实验结果；
- 哪个发现最有学术意义；
- 当前该如何在 thesis 中定位这条路线。

---

## 2. 起点：为什么从 V5 往 shadow-price 路线转
在 OR-V5 / V6 / V7 上，我们已经得到几个重要结论：
1. `controller -> routing` feedback 结构本身是有效的；
2. 仅仅增加更多 label（如 `pressure_mode`）并不能继续带来收益；
3. `V7 = V5` 在 Herlev、East、West 上都成立，说明单纯的 `label -> insertion bias` 这条弱耦合路径已经接近饱和。

因此，后续深化的关键问题被重新定义为：
> **不是标签是否够多，而是资源压力能否被内生为 routing 中的价格信号。**

这就形成了 shadow-price 路线：
- 从 `risk label -> insertion bias`
- 升级到 `resource pressure -> shadow-price-like cost internalization`

---

## 3. 各版本演化

## 3.1 OR-V5：controller-to-routing bucket feedback
### 机制
- controller 输出 `bucket_risk_signal`
- routing 对高风险 flex 子集施加 targeted insertion bias

### Herlev 结果
- `SR = 99.14%`
- `expired = 9`
- `max depot penalty = 4399.96`
- `max overloads = 4`

### 意义
V5 是这条线的起点，证明：
- controller-to-routing 协同反馈是有价值的；
- 但它仍属于 `label -> bias` 路径。

---

## 3.2 OR-V5.2：quasi-shadow-price feedback
### 机制
- controller 生成启发式 `lambda_gate / lambda_picking / lambda_staging`
- routing 把这些价格乘到对应资源增量上
- insertion cost 从 “heuristic bias” 开始转向 “resource-price cost”

### Herlev 结果
- `SR = 99.43%`
- `expired = 6`
- `max depot penalty = 4485.08`
- `max overloads = 7`

### 意义
V5.2 的关键发现是：
- 影子价格式内生化确实改变了行为；
- 它把服务拉回到 OR-V2 水平；
- 但没有保住 V5 的结构收益。

### 阶段判断
这说明：
> **“有价格”这件事本身是有用的，但当前资源使用代理还太粗。**

---

## 3.3 OR-V5.3：refined resource-usage proxies
### 机制
对三类资源 usage proxy 做结构化重写：
- gate proxy：更贴近 departure bucket 占用
- picking proxy：更贴近 per-bucket picking intensity
- staging proxy：更贴近 duration-volume pressure

### Herlev 结果
- `SR = 99.90%`
- `expired = 1`
- `max depot penalty = 4424.36`
- `max overloads = 5`

### 意义
V5.3 是 shadow-price 路线的关键正向突破：
- 比 V5.2 明显更强；
- 几乎恢复 baseline-level service；
- 同时保持比 V5.2 更合理的 depot structure。

### 阶段判断
V5.3 的核心结论是：
> **真正的杠杆不在“有没有价格”，而在“价格乘的资源增量 proxy 是否足够贴近真实 depot usage”。**

---

## 3.4 OR-V5.3 的跨实例验证
### East
- 服务维持 `100%`
- depot metrics 与 V2/V5 差异不大
- 未显现 Herlev 那种明显额外收益

### West
- `expired: 4 -> 78`
- `SR: 99.91% -> 98.29%`
- 但 `max depot penalty` 明显下降

### 阶段判断
这说明：
- refined proxy 路线是有效的；
- 但在高压大实例上，价格会过度放大 depot-safe 偏好，形成近似 hard gate；
- 当前 V5.3 还不具备跨实例稳定性。

---

## 3.5 OR-V5.4：normalized shadow-price + service shield
### 机制
针对 V5.3 的 West 坍塌，引入：
1. **normalized shadow-price**：按当前实例/压力水平对 `lambda` 缩放；
2. **service shield**：对 protected / near-deadline / 高分订单给予 shadow-cost relief。

### West 结果
- `OR-V5.3: expired = 78, SR = 98.29%`
- `OR-V5.4: expired = 10, SR = 99.78%`
- 同时 `max depot penalty` 仍低于 OR-V2

### East 结果
- 服务仍为 `100%`
- 没有额外收益，但也没有破坏性能

### 阶段判断
V5.4 的作用不是成为“所有实例都更优”的统一版本，而是：
> **作为高压实例下的 shadow-price stabilization layer。**

---

## 4. 当前路线的学术结论

## 4.1 最关键发现
从这条线目前的结果看，最有学术价值的一句话是：
> **proxy quality, not merely adding price terms, is the key lever in shadow-price-based depot internalization.**

翻成更直白的话就是：
- 不是“加 λ 就赢了”；
- 而是“λ 乘的资源增量是否真的近似了 depot 资源占用”。

这是目前 shadow-price 路线最值得写进 thesis 的机制发现。

---

## 4.2 当前路线的边界
当前这条线也暴露出明确边界：
1. refined proxy 可以显著改善 Herlev；
2. 但若不做 normalization / shield，在高压实例上会失真；
3. V5.4 能把高压实例从坍塌里救回来，但它更像保护层，而不是普适收益层。

也就是说：
> **shadow-price 路线成立，但它不是“裸 price term”就足够，还必须考虑跨实例压力归一化与服务保护。**

---

## 5. 当前应如何在 thesis 中定位这条路线

### 5.1 不应写成
- “OR-V5.4 已经统一优于 OR-V2”
- “shadow-price 路线已经完全成熟并稳定跨实例”

### 5.2 更合适的写法
- OR-V5.x 说明：从 label feedback 升级到 quasi-shadow-price internalization 是有效方向；
- refined resource-usage proxies 是当前最关键的方法增益来源；
- 高压实例需要 normalized shadow-price + service shield 才能避免服务坍塌；
- 因此，shadow-price 路线应被视为当前 OR 支线中最有理论提升潜力、但尚未完全收口的深化方向。

---

## 6. 当前版本定位
### 当前主保留版本（稳态主线）
- **OR-V2**

### 当前机制探索版本（controller-routing feedback）
- **OR-V5**

### 当前理论深化版本（shadow-price 路线）
- **OR-V5.3 / OR-V5.4**
  - `V5.3`：说明 refined proxies 很关键
  - `V5.4`：说明高压实例上 normalization + shield 必不可少

---

## 7. 下一步建议
若继续沿 shadow-price 路线推进，建议的重点不是再回到 label/bias 调参，而是：
1. 继续优化 resource-usage proxy 的跨实例稳定性；
2. 让 normalization 与 pressure regime 结合得更系统化；
3. 明确 service shield 的作用边界，避免其沦为纯粹补丁；
4. 逐步把这一条包装为更明确的 quasi-dual / resource-pricing 方法论。

---

## 8. 阶段一句话总结
当前 shadow-price 路线已经从“概念探索”推进到“机制成形”：
- `V5.2` 证明价格内生化有效；
- `V5.3` 证明 proxy 质量是关键；
- `V5.4` 证明高压实例下需要 normalization + service shield。

因此，这条线当前最重要的学术贡献，不是“已经赢了 OR-V2”，而是：
> **它揭示了 depot shadow-price internalization 的真正技术难点与可行突破口。**
