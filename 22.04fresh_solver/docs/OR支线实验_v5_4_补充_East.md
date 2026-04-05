# OR 支线实验 v5.4：East 补充验证

## 1. 目的
在 West 上，V5.4 已经证明：
- normalized shadow-price + service shield 可以显著修复 V5.3 的高压坍塌。

本补充实验用于确认：
> 在相对宽松的 East 实例上，V5.4 是否会破坏原有表现。

---

## 2. East 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 3268 | 0 | 100.00% | 1865 | 30752.72 | 13 | 431.4 |
| OR-V5.3 | 3268 | 0 | 100.00% | 1963 | 30119.88 | 14 | 418.1 |
| OR-V5.4 | 3268 | 0 | 100.00% | 1963 | 30428.28 | 15 | 518.7 |

---

## 3. 解释
### 3.1 East 上 V5.4 没有破坏服务
- 服务仍为 `100%`
- 没有增加 expired

这说明 normalization + service shield 至少没有在宽松实例上把系统搞坏。

### 3.2 但 East 上也没有额外收益
相比 V5.3：
- depot penalty 略回升；
- overload bucket 略增；
- runtime 增加。

所以在 East 上，V5.4 只是“安全但没明显收益”，而不是进一步提升版本。

---

## 4. 当前综合判断
结合 Herlev / East / West：
- Herlev：V5.3 很强
- West：V5.4 显著修复 V5.3 坍塌
- East：V5.4 不破坏服务，但没有新增收益

这说明：
- normalization + service shield 是高压实例必要机制；
- 但在宽松实例上，它更多是一个防守型保护层，而不是收益来源。

## 5. 结论
V5.4 当前最合理的定位是：
> **面向高压实例的 shadow-price stabilization layer**

而不是一个在所有实例上都统一优于 V5.3 的版本。
