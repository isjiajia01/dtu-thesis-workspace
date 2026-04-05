# OR 支线大实例对照：East / West 上的 OR-V2 vs OR-V5

## 1. 目的
在 Herlev 上，OR-V2 与 OR-V5 已经形成较清晰分工：
- OR-V2：更好的服务型 OR 点
- OR-V5：更好的结构型 OR 点

本对照的目的，是测试这种关系在更大实例（East / West）上是否仍成立。

对应结果：
- `east_multiday_or_v2_julia.json`
- `east_multiday_or_v5_julia.json`
- `west_multiday_or_v2_julia.json`
- `west_multiday_or_v5_julia.json`

---

## 2. East 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 3268 | 0 | 100.00% | 1865 | 30752.72 | 13 | 431.4 |
| OR-V5 | 3268 | 0 | 100.00% | 1963 | 29894.08 | 14 | 488.7 |

### East 解释
- 二者在服务层面完全相同：都达到 `100%` SR；
- OR-V5 的 max depot penalty 略低，但 max overload bucket 反而略高；
- 差异整体较小，说明 East 在当前模型下属于容量较宽松、对 OR 分支结构变化不太敏感的 regime。

---

## 3. West 结果

| Variant | Assigned | Expired | SR | Deferred events | Max depot penalty | Max overloads | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OR-V2 | 4548 | 3 | 99.934% | 2477 | 22860.08 | 23 | 626.6 |
| OR-V5 | 4547 | 4 | 99.912% | 2623 | 24102.64 | 24 | 689.6 |

### West 解释
- OR-V2 在 West 上同时优于 OR-V5：
  - 服务更高；
  - expired 更少；
  - deferred 更少；
  - max depot penalty / overload 也更低；
- 这说明在更大、更敏感的 West 实例上，Herlev 中 OR-V5 的“结构更干净”优势没有迁移成功，反而输给了 OR-V2。

---

## 4. 综合结论
### 4.1 Herlev 的 OR-V5 结构优势并未稳定迁移到大实例
- East：差异很小，未显示出 OR-V5 的明显结构性优势；
- West：OR-V5 反而整体不如 OR-V2。

### 4.2 当前 OR 支线的跨实例最稳版本仍是 OR-V2
基于 Herlev / East / West：
- OR-V2 目前仍是更稳、更可迁移的 OR 分支版本；
- OR-V5 体现了 controller-to-routing feedback 的研究价值，但当前只在 Herlev 上展示了结构改善，在更大实例上尚未证明泛化优势。

### 4.3 研究含义
这说明：
- controller-to-routing feedback 这个想法本身值得保留；
- 但当前实现方式可能过于 Herlev-specific；
- 若继续探索 V5 路线，更合理的是重新设计 feedback signal 的内容或作用时机，而不是把当前版本直接视为大实例更优方案。

---

## 5. 当前阶段判断
### 当前服务型 / 稳定型首选
- **OR-V2**

### 当前机制探索型保留
- **OR-V5**

也就是说：
- `OR-V2` 可作为当前 OR 支线的主保留版本；
- `OR-V5` 可作为“协同 feedback 机制有潜力但尚未跨实例稳定”的探索版本。
