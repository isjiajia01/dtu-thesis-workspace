# Runtime Policy And Scaling Notes

本文件用于沉淀近期关于 `Herlev`、`DATA003 east/west`、动态计算时间、以及 depot feasibility 瓶颈的论文写作要点。

它不是最终论文正文，而是后续撰写 Chapter 6-8 时的统一备忘。

## 1. 当前可安全写入论文的核心结论

### 1.1 Herlev retained line

- 在保留的 `Herlev / EXP01 / Scenario1 / v6g cap05` 主线中，动态计算时间是有价值的。
- `CTRL / DYNNS / DYN90 / DYN90R` 的比较表明：
  - `DYNNS` 最快，但会明显伤解。
  - `DYN90` 在运行时间与解质量之间给出最平衡的折中。
  - `DYN90R` 质量略好，但几乎把时间收益吃回去。
- 因此，若论文需要一个主推的动态算时版本，应优先使用 `DYN90`。

### 1.2 DATA003 east/west

- `east/west` 结果不能直接和 `Herlev` 的服务率横向比较。
- 原因不是算法主线不同，而是：
  - 数据集不同
  - 场景口径不同
  - depot resource profile 不同
  - BAU 与 crunch 结果被混在一起时会放大误解
- 对 `DATA003`，应始终区分：
  - `EXP00 / BAU`
  - `EXP01 / R060 crunch`

### 1.3 运行时间爆炸的主因

- `DATA003 east/west` 早期的时间爆炸，并不是 `trip2` 主导，也不是 controller candidate evaluation 直接调用 solver 导致。
- 最关键的放大器是：
  - routing candidate 已经找到
  - 但 `warehouse/depot feasibility` 过不去
  - 系统进入 repeated repair / repeated re-solve
- 旧版中，这会把一个 simulation day 放大成大量完整 solve 调用。

### 1.4 当前已识别的具体 bottleneck

- 通过 west probe，当前已确认的最关键失败原因是：
  - `warehouse_reason = due_to_picking_throughput_or_staging`
- 因此，`DATA003` 的主问题不是“routing solver 完全不会解”，而是：
  - **routing candidate 与 depot-side feasibility repair 的耦合在大实例上失控**

## 2. 论文里应如何表述

### 2.1 关于动态时间

推荐表述：

- Dynamic runtime control is beneficial on the retained Herlev line.
- However, the benefit is instance-dependent and should not be extrapolated mechanically to larger datasets.
- On larger DATA003 instances, runtime is strongly influenced by depot-side feasibility repair, so the value of dynamic time control depends on whether the instance is routing-dominated or depot-feasibility-dominated.

避免表述：

- “动态时间永远更好”
- “计算时间越多越好”
- “计算时间越少越好”

正确口径应是：

- runtime-quality tradeoff is regime-dependent

### 2.2 关于 east/west 的高服务率

推荐表述：

- `DATA003` 的高服务率不应直接与 `Herlev` 主线的 `97-98%` 横向排名。
- 原因是 benchmark 口径不同，尤其 BAU 与 crunch 的可服务性基线不同。

避免表述：

- “east/west 比 Herlev 更容易”
- “Herlev 算法更差，因此只有 97-98%”

### 2.3 关于扩展性

推荐表述：

- The retained controller line remains effective on the medium-scale Herlev benchmark.
- Larger DATA003 instances reveal a scaling bottleneck in the depot-feasibility repair chain.

注意：

- 这比直接说 “算法 handle 不了大实例” 更准确。
- 当前证据更支持：
  - implementation / repair-chain bottleneck is dominant
  - rather than a clean proof that the whole method family is fundamentally invalid

## 3. 当前工程判断

### 3.1 默认策略

- 对新数据集，不建议先拍一个固定秒数。
- 当前最合理的工程默认起点是：
  - `DYN90 + reopt`

### 3.2 何时退回 fixed300

- 若新数据集出现如下信号，应退回更稳妥的 `fixed300 + reopt`：
  - `warehouse_reason_code = due_to_picking_throughput_or_staging` 高频出现
  - `solver_status = no_solution` 高频出现
  - `vrp_dropped / planned_today` 偏高
  - depot repair 成为主导瓶颈

### 3.3 何时进一步压到 DYN60

- 若实例显示：
  - routing success 稳定
  - depot feasibility 不敏感
  - 提前停不明显伤解
- 则可以尝试：
  - `DYN60 + reopt`

### 3.4 工程落地口径

- 对公司落地，不应把 `chunk=60/90` 等底层 solver 参数直接暴露给用户。
- 更合理的形式是：
  - `Fast`
  - `Balanced`
  - `Stable`
  或者系统内部完全自动切换。
- 系统根据实时信号决定使用：
  - `DYN60 + reopt`
  - `DYN90 + reopt`
  - `fixed300 + reopt`

## 4. 推荐写入结果讨论章节的结构

建议在结果与讨论章节中按以下层次组织：

1. `Herlev` 主线先给出动态时间对 retained line 的收益。
2. 再说明该结论不能直接机械外推到 `DATA003`。
3. 引入 `east/west` 的扩展性诊断，指出主瓶颈来自 depot-side feasibility repair。
4. 最后再讨论工程部署：
   - medium-scale instances: dynamic time is valuable
   - large depot-constrained instances: runtime policy must be coupled with depot-feasibility signals

## 5. 当前最值得保留的具体实验含义

- `Herlev DYN90`
  - 作为 retained line 上最平衡的动态算时证据
- `DATA003 fixed300 + reopt`
  - 作为大实例上的稳妥参考基线
- `west probe`
  - 作为 depot feasibility bottleneck 的强证据
  - 已明确抓到 `due_to_picking_throughput_or_staging`

## 6. 一句话版本

若正文需要一段高浓度总结，可用这句：

> Dynamic runtime control improves the runtime-quality tradeoff on the retained Herlev line, but larger DATA003 instances show that the dominant scaling bottleneck is depot-side feasibility repair rather than pure routing search. Consequently, runtime policy should be conditioned on operational regime indicators, especially depot-feasibility signals, rather than treated as a single global time-budget choice.
