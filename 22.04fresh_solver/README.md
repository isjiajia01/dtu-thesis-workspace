# 22.04fresh_solver

本文件夹用于承接当前 thesis 的问题背景、数据、算法架构与后续实验。

## 目录结构
- `docs/`：问题背景、算法架构、实验口径、诊断与写作素材
- `data/processed/benchmarks/`：benchmark JSON 数据集
- `data/processed/matrices/`：各 depot 对应的真实路网矩阵
- `configs/`：求解配置与实验配置
- `experiments/`：实验计划、批次说明、对照组设计
- `results/`：实验输出、汇总表、图表源数据
- `notes/`：阅读笔记、临时分析、写作碎片
- `src/algorithms/fresh_solver/`：当前主求解器实现骨架与说明

## 当前已放入内容
- `docs/问题背景.md`
- `docs/最优算法架构.md`
- `docs/03_算法框架_论文章节版.md`
- `data/processed/benchmarks/*`
- `data/processed/matrices/*`
- `src/algorithms/fresh_solver/julia/*`

## 当前主线建议
论文主线算法架构建议采用：

**Rolling-Horizon Controller + Daily Rich VRP Backend + Depot-Resource Repair**

即：
1. 跨日控制器：决定当天接哪些单、保护哪些单、延后哪些单
2. 单日路径后端：生成多趟、带时间窗和容量约束的日内路线
3. 仓库资源修复层：修复 gate / picking / staging / trip2 带来的仓配冲突

## 当前实现主线
- 算法主要实现语言切到 **Julia**
- Julia 主入口：`src/algorithms/fresh_solver/julia/`
- 当前已可运行：`julia --project=. scripts/run_day.jl`
- 已产出基线结果：`results/raw_runs/herlev_single_day_baseline_julia.json`
