# 关键抉择：OR vs AI 支线设计

## 1. 结论
当前 thesis 主线建议优先走 **OR / 仓库约束更深内生化**，而不是立刻把主线切到完整的 RL-ALNS。

原因不是 AI 不重要，而是从当前 `22.04` 的系统状态看，最核心的科学问题仍然是：
- 为什么高 service rate 会与非零 depot penalty 并存；
- 为什么后置 repair 仍然无法完全闭合 execution realism；
- 如何把 gate / picking / staging 风险更早地纳入 admission 与 route construction。

因此，当前最合理的结构是：
- **主线：OR / integrated depot-aware solving**
- **支线：AI / learning-based operator selection（后续增强或 supplementary）**

---

## 2. 为什么主线先选 OR

### 2.1 当前最痛的瓶颈不是“搜索不够聪明”，而是“约束还不够内生”
当前 `22.04` 已经有：
- controller
- daily routing backend
- depot-aware repair
- optimistic vs strict 对照
- Herlev / East / West 多实例结果

这些结果已经表明：
1. 系统有很强的清 backlog 能力；
2. 但 realism 收紧后，Herlev / West 会掉点；
3. 说明核心问题在于 depot-aware realism 如何更早进入求解链。

### 2.2 RL-ALNS 现在切入风险大
当前若直接切 RL 主线，需要补：
- 稳定算子池抽象
- 状态表示
- 动作空间
- reward 设计
- 训练/验证/泛化框架
- 方差与鲁棒性分析

而当前 thesis 更急需的是把问题建对，而不是先把搜索器训聪明。

---

## 3. 两条路线在 thesis 中的角色分工

### 3.1 OR 主线
建议写成：
- `controller + daily routing backend + depot-aware repair`
- 从后置 repair 逐步走向更强的 depot-aware admission / insertion / acceptance
- 用 optimistic vs strict 说明 realism 对结果的影响

### 3.2 AI 支线
建议写成：
- 在固定 OR 主体上做 learning-guided operator orchestration
- 目标是提升大实例上的 quality-time trade-off
- 作为后续方法扩展或 supplementary follow-up

---

## 4. OR 支线的近期实验路线图

## Phase A：soft-to-hard 内生化
目标：不改主架构，只把 depot 风险更早推入 controller / routing。

### A1. 更早 admission clipping
- 更早触发 depot feedback
- 更强 risky-flex clipping
- 更高 protected reservation

### A2. 更强 depot-aware route scoring
- 提高 trip2 / late-window / heavy-order 的早期代价
- 减少过度 route packing
- 让 route 构造阶段提前让路于仓库可执行性

### A3. 更严格的 refill / rollback 接受条件
- depot overload 高时减少 refill
- 若 repair 无法明显降风险，则更倾向 rollback flex

## Phase B：hard-like guard
目标：把部分 depot overload 从 soft penalty 推向 hard-like acceptance。

### B1. severe bucket guard
- 超过严重阈值的 bucket 不允许继续加压

### B2. overload-aware refill veto
- refill 若会推高 worst bucket，则拒绝

### B3. controller closure rule
- 若上一日 depot 过载严重，则第二日 admission 自动更保守

## Phase C：更结构化的协同表达
目标：开始把 depot-resource coupling 写成更系统化的方法贡献。

### C1. cumulative resource proxy
### C2. decomposition-friendly depot coupling term
### C3. route construction 中显式 bucket-smoothing bias

---

## 5. AI 支线的后续路线图（暂不主推）

### D1. 抽象当前 repair / refill / move 为算子库
### D2. 设计 state（depot load, route mix, carryover pressure）
### D3. 学习 operator selection policy
### D4. 与 hand-crafted rules / roulette baseline 对照

当前建议：先不把 D 线作为 thesis 主线，只在 OR 主线稳定后再启动。

---

## 6. 立刻可执行的三个实验

### Experiment OR-V1：depot-aware admission + routing tightening
- 类型：配置级实验
- 目的：验证更早 depot-aware 控制是否能在不过度损失 SR 的情况下改善 realism
- 输出：Herlev baseline vs OR-V1

### Experiment OR-V2：severe-overload guard
- 类型：机制级实验
- 目的：把 severe bucket 从 soft penalty 推向 hard-like veto
- 输出：strict baseline vs OR-V2

### Experiment OR-V3：refill veto under depot stress
- 类型：机制级实验
- 目的：减少 high-risk refill 对 worst bucket 的二次放大
- 输出：West strict vs OR-V3

---

## 7. 当前执行决策
当前先正式启动：
- **OR-V1**：作为 OR 支线第一步实验

选择理由：
- 改动小，风险低；
- 直接检验“更早内生化”是否有效；
- 能快速给 thesis 一个支线起点结果。

---

## 8. 一句话总结
当前 thesis 最该回答的是：
> 如何把仓库执行约束更真实地内生到滚动求解框架中。

因此，当前主线先押 **OR / depot-aware integration**；AI 支线保留，但放到主线稳定之后再展开。 
