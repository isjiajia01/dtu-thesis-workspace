# OR 支线实验 v5.4：normalized shadow-price + service shield

## 1. 目的
针对 OR-V5.3 在 West 上出现的“服务坍塌但 depot penalty 改善”的问题，V5.4 不是简单调低价格强度，而是加入两层保护：

1. **normalized shadow-price**：根据实例当前压力水平对 `lambda` 做缩放，避免在高压 regime 中价格被过度放大成近似 hard gate。
2. **service shield**：对 `protected / near-deadline` 以及高分订单，在 shadow-price 成本上给予减免，防止资源价格把服务目标完全压掉。

本轮先在最敏感的 West 上验证。

输出：
- `results/raw_runs/west_multiday_or_v5_4_julia.json`

---

## 2. West 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 4548 | 3 | 99.934% | 2477 | 22860.08 | 23 |
| OR-V5.3 | 4473 | 78 | 98.286% | 2696 | 19244.68 | 24 |
| OR-V5.4 | 4541 | 10 | 99.780% | 2625 | 20942.56 | 24 |

---

## 3. 解释
### 3.1 V5.4 明显修复了 V5.3 的 West 坍塌问题
相比 V5.3：
- `expired: 78 -> 10`
- `service_rate: 98.29% -> 99.78%`
- `assigned: 4473 -> 4541`

这说明：
- instance-aware normalization + service shield 确实挡住了 shadow-price 在高压实例上的过激失真；
- refined price internalization 路线并不是错，而是需要保护层。

### 3.2 但 V5.4 仍未达到 OR-V2 的水平
相比 OR-V2：
- `expired: 3 -> 10`
- `service_rate: 99.934% -> 99.780%`
- `deferred events: 2477 -> 2625`

不过：
- `max_depot_penalty: 22860.08 -> 20942.56` 有改善

这说明 V5.4 成功找回了大部分服务，同时保留了一部分 depot-structure 改善，但还未达到“既胜过 OR-V2 服务，又保住更好 depot 结构”的理想点。

---

## 4. 当前结论
V5.4 是一个重要正向结果：
- 它证明 West 上的问题不是 V5.3 路线本身错误，而是价格内生化缺乏归一化与服务保护；
- 加入 normalization + shield 后，West 从“明显坍塌”回到“接近可用”；
- 这表明 refined shadow-price 路线仍值得继续深挖。

## 5. 下一步建议
若继续沿 V5.4 往下推进，更有价值的方向是：
1. 在 East 上补跑 V5.4，确认不会破坏宽松实例表现；
2. 将 shield 从静态规则升级为与 deadline / protected class 更强绑定；
3. 让 normalization 与实例压力 regime 更细粒度对齐，而不是当前简单缩放。
