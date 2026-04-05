# OR 支线实验 v5.2：quasi-shadow-price feedback

## 1. 目的
在 OR-V5 的基础上，把当前协同机制从：
- `risk label -> insertion bias`

升级为：
- `resource pressure -> shadow-price-like cost internalization`

核心思想是：
- controller 不再只输出 `bucket_risk_signal / pressure_mode`
- 而是根据上一日 depot diagnostics 形成一组启发式资源价格：
  - `lambda_gate`
  - `lambda_picking`
  - `lambda_staging`
- routing 在 insertion / new-route 选择时，把这些价格乘到对应资源增量上，形成类似“影子价格成本”的附加项。

输出：
- `results/raw_runs/herlev_multiday_or_v5_2_julia.json`

---

## 2. 实现方式
### Controller 侧
根据：
- `bucket_pressure_score`
- `pressure_mode`

生成：
- `lambda_gate`
- `lambda_picking`
- `lambda_staging`

若某一类资源为上一日主导压力模式，则相应 `lambda` 更高；若模式平衡，则三者均分。

### Routing 侧
在 insertion scoring 中新增 shadow-price-like 成本：
- gate price × trip2 / late departure proxy
- picking price × picking-task / colli proxy
- staging price × route-volume / late staging proxy

于是当前 insertion cost 可以理解为：
- route distance / route penalty
- + targeted bias
- + shadow-price-like resource cost

---

## 3. Herlev 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 1038 | 6 | 99.43% | 528 | 4983.48 | 6 |
| OR-V5 | 1035 | 9 | 99.14% | 550 | 4399.96 | 4 |
| OR-V5.2 | 1038 | 6 | 99.43% | 580 | 4485.08 | 7 |

---

## 4. 解释
### 4.1 OR-V5.2 把服务恢复到了 OR-V2 水平
相比 OR-V5：
- `service_rate: 99.14% -> 99.43%`
- `expired: 9 -> 6`

说明 quasi-shadow-price feedback 至少没有像 V5 那样继续压低服务。

### 4.2 但它没有保住 V5 的结构收益
相比 OR-V5：
- `max_depot_penalty: 4399.96 -> 4485.08`（略变差）
- `max_overloads: 4 -> 7`（更差）

相比 OR-V2：
- 服务与 expired 基本打平；
- depot penalty 略优于 OR-V2；
- overload bucket 更差。

### 4.3 研究含义
OR-V5.2 说明：
- 从标签反馈升级到“影子价格式成本内生化”，确实改变了行为；
- 它把 V5 的结构型协同推回到更接近 V2 的服务表现；
- 但当前价格代理还比较粗，尚未形成“既保住 V5 结构收益，又恢复 V2 服务优势”的理想平衡。

---

## 5. 当前结论
OR-V5.2 是当前 V5 系列里第一个真正具有“准对偶/影子价格”味道的版本，说明：
- 继续深挖 V5，正确方向不是再堆标签，而是把资源压力转成 cost internalization；
- 但当前 price proxy 还偏粗，下一步应继续精炼资源使用代理与价格映射，而不是回到单纯 label/bias 逻辑。
