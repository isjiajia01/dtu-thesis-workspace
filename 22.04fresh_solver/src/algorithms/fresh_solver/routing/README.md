# routing

负责单日多趟富约束路径生成。

第一版代码实现顺序：
1. `constructive.py`：seed + insertion 骨架
2. 后续补：
   - route timeline recomputation
   - trip1 / trip2 relay feasibility
   - regret insertion
   - local improvement
   - protected displacement controls
