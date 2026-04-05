# Figure Build Recipes

## Scope

当前只保留 `EXP00` / `EXP01` 图表配方。

## Figure A: `EXP00` vs `EXP01`

需要目录：

- `22.03controller_line/data/results/EXP_EXP00/`
- `22.03controller_line/data/results/EXP_EXP01/`

建议指标：

- `service_rate`
- `failed_orders`
- `cost_raw`
- `penalized_cost`

建议说明：

- `EXP00` 作为正常运营参考
- `EXP01` 作为单波压力参考

## Figure B: `EXP01` 按 seed 的稳定性

需要目录：

- `22.03controller_line/data/results/EXP_EXP01/`

建议指标：

- `service_rate`
- `failed_orders`
- `plan_churn`
