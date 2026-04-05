# fresh_solver

当前 thesis 主求解器建议按三层结构组织：

1. `controller/`
   - 跨日 admission / protection / clipping
2. `routing/`
   - 单日多趟构造式路径求解后端
3. `repair/`
   - depot-aware overload diagnostics 与后处理修复

## 实现语言
- **主实现：Julia** → `julia/`
- Python 目录保留为早期骨架/接口参考

## 推荐内部模块
- `instance.*`：benchmark / matrix / warehouse / fleet 数据读取
- `state.*`：rolling-horizon day state, backlog, commitments
- `controller/*`：order scoring, reservation, admission policy
- `routing/*`：seed, insertion, trip-aware feasibility, local improve
- `repair/*`：gate / picking / staging diagnostics, smoothing, reassignment
- `evaluation/*`：service KPI, routing KPI, depot KPI, failure labels
- `experiments/*`：Herlev / East / West 的批量实验入口

## 当前主线口径
- 不把 giant MIP 作为主线
- 不把纯 RL 作为主线
- 不默认引入完整 3D packing
- 以 `controller + routing backend + depot repair` 为 thesis 主架构
- 当前 Julia baseline 入口：`julia/scripts/run_day.jl`
