# experiments

本目录存放实验设计与批次说明。

## 推荐子结构
- `herlev/`：Herlev 主基准实验
- `west/`：West 大规模 regime 诊断实验
- `east/`：East 对照实验
- `ablation/`：controller / routing / repair 消融
- `reports/`：阶段性汇总与对照表

## 推荐命名规则
- `A*`：controller 方向实验
- `S*`：routing / shaping / service trade-off 实验
- `P*`：结构性新路线或 phase redesign
- `R*`：repair-only 强化实验

## 最小实验记录模板
每个实验建议记录：
- 实验名
- 输入 benchmark
- config 路径
- baseline 对照
- assigned / deferred / failed
- depot penalty / overload buckets
- runtime
- 核心观察
