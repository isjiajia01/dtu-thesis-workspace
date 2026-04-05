# OR 支线实验 v5.3：refined resource-usage proxies

## 1. 目的
在 OR-V5.2 的 quasi-shadow-price feedback 基础上，进一步回答关键问题：

> 不是“有没有价格”，而是“价格乘的资源增量 proxy 是否足够贴近真实 depot usage”。

因此，V5.3 不改总体框架，只重做三类资源 usage proxy：
1. gate proxy
2. picking proxy
3. staging proxy

输出：
- `results/raw_runs/herlev_multiday_or_v5_3_julia.json`

---

## 2. 代理改进内容
### 2.1 Gate proxy
从之前偏粗的 `trip2 / late departure` proxy，改为更贴近 departure bucket 占用：
- base gate usage = 1.0
- trip2 增量 +0.5
- late departure 增量 +0.25

### 2.2 Picking proxy
从简单 `picking-task / colli` 代理，改为：
- 根据候选 route 的 pick 窗口长度计算 `pick_bucket_count`
- 以 `(route total colli + 0.5 * total volume) / pick_bucket_count` 近似每 bucket picking load

### 2.3 Staging proxy
从简单 `late staging + route volume` 代理，改为：
- 根据 pick-start 到 departure 的持续时间估算 staging 持续占用桶数
- 用 `route volume × staging_duration_buckets` 近似 staging pressure

---

## 3. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V5 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |
| OR-V5.2 | 1038 | 6 | 99.43% | 580 | 4485.08 | 7 |
| OR-V5.3 | 1043 | 1 | 99.90% | 577 | 4424.36 | 5 |

---

## 4. 解释
### 4.1 V5.3 明显优于 V5.2
相比 V5.2：
- `service_rate: 99.43% -> 99.90%`
- `expired: 6 -> 1`
- `max_depot_penalty: 4485.08 -> 4424.36`
- `max_overloads: 7 -> 5`

这说明 refined proxies 的确更好地刻画了资源压力，使 shadow-price-like cost internalization 更有效。

### 4.2 V5.3 的位置
相比 V5：
- 服务显著更好（`99.14% -> 99.90%`）
- depot penalty 略差（`4399.96 -> 4424.36`）
- overload 略高（`4 -> 5`）

相比 baseline：
- 服务达到同水平（`1043 / 1044`）
- 但 depot 结构仍未达到 baseline 的低 penalty / overload。

### 4.3 学术意义
V5.3 是当前 OR 支线里一个非常关键的发现：
- 不是“标签反馈”在起作用；
- 不是单纯“价格项”在起作用；
- 而是 **更贴近 depot diagnostics 的资源使用代理**，让价格内生化终于开始显著改变 service / structure trade-off。

这说明继续深挖影子价格路线是有价值的，而关键不在于价格概念本身，而在于资源使用近似是否足够贴近实际执行约束。

---

## 5. 当前结论
OR-V5.3 说明：
- `quasi-shadow-price feedback` 是有效方向；
- refined resource-usage proxies 是当前真正带来增益的关键；
- 接下来应优先验证 V5.3 是否能在 East / West 上保持改进，而不是回到纯标签/纯强度调参路线。
