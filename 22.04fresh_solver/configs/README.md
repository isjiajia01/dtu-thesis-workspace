# configs

本目录用于存放求解配置。

## 推荐拆分
- `controller/`：admission / protection / clipping 参数
- `routing/`：seed / insertion / local search 参数
- `repair/`：diagnostics / move budget / penalty 参数
- `experiments/`：完整实验组合配置

## 推荐配置层级
1. `base.yaml`：全局默认参数
2. `instance/*.yaml`：按 benchmark 的实例特定参数
3. `experiment/*.yaml`：实验覆盖项

## 当前建议的关键参数
### controller
- urgency weights
- age weights
- protected reserve ratio
- flex admission cap
- stability penalty

### routing
- insertion strategy
- seed policy
- trip2 penalty
- local search budget

### repair
- gate bucket size
- overload penalty weights
- rollback budget
- refill budget
- reassignment neighborhood size
