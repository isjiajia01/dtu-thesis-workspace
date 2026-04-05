# Architecture

## 层次结构

- 入口与编排：`scripts/`（实验运行、HPC 作业生成、预检查）
- 核心算法：`code/`（controller, routing backend, experiments）
- 兼容包名：`src/`（通过 `src/__init__.py` 将 `src.*` 映射到 `code/`）
- 论文与公式：`paper/`
- 数据：`data/raw`（只读）, `data/processed`（可复现产物）
- 结果：`data/results`

## 术语约定

- 不再把当前 `22.03` 的日内求解器写成 `ALNS`。
- 当前日内求解核心应写为 `routing solver` 或 `daily routing backend`。
- 如果需要指出实现细节，安全写法是 `OR-Tools GLS solver`，因为当前实现是 `RoutingModel + guided local search`。
- 整体方法结构应写为 `controller + routing backend`：
  - `controller` 负责滚动重算、admission / commitment / reservation / runtime-policy 等上层决策。
  - `routing backend` 负责在给定订单尝试集合上生成日内车辆路径与服务顺序。
- 只有在讨论历史兼容类名时，才提 `ALNS_Solver`；那是保留的代码别名，不是推荐的论文措辞。

## 数据流

1. 原始数据进入 `data/raw`。
2. 处理后产物进入 `data/processed`。
3. `EXP00` / `EXP01` 读取 `data/processed` 并输出到 `data/results`。

4. `controller` 在滚动时域上决定当天尝试订单集合与算时策略。
5. `daily routing backend` 在固定计算预算内求解日内 VRP/VRPTW 并返回执行计划。

## 计算矩阵

- 路网矩阵采用 OSRM 生成并存于 `data/processed/vrp_matrix_latest/`。
- 所有保留实验均使用该矩阵。
