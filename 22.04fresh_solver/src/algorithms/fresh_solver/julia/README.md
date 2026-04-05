# FreshSolver Julia backend

这个目录是 thesis 主算法的 Julia 实现入口。

## 当前状态
- 已有可运行的单日 baseline 骨架
- 架构按 `controller + routing backend + depot-aware repair` 组织
- 已可读取 benchmark JSON，运行 Herlev baseline，并输出结果 JSON
- controller 已升级到 `protected reservation + risk-aware clipping v1`
- controller 已接入 `rolling depot feedback v1`（先跑一轮诊断，再按 depot penalty / overload buckets 收紧 admission）
- 当前 routing 已升级到 **可行性优先 v8**：
  - deadline/age/risk 打分控制器
  - 基于真实 benchmark 容量的车辆选择
  - **真实矩阵读取**（`index.json` + `durations.int32.bin` + `distances.int32.bin` + `nodes.csv`）
  - **protected-first seeding + regret insertion v1**
  - **route-level local improvement v1**（优先 `relocate + swap`）
  - **vehicle-type-aware seeding / insertion bias v1**（轻量 truck-heavy / lift-light 偏置）
  - **split-tail / route-split / second-stage refill v3**（按 thesis 计划继续强化 acceptance 权重，联合考虑 service / depot / protected）
  - 允许插入到 route 内部位置，而非仅尾插
  - 客户时间窗检查
  - 容量 / 路线时长 / 距离检查
  - trip1 / trip2 车辆接力检查
  - unassigned reason 输出

## 目录
- `Project.toml`：Julia 项目依赖
- `src/FreshSolver.jl`：主模块
- `scripts/run_day.jl`：单日 baseline 运行脚本
- `scripts/run_multiday.jl`：multi-day rolling baseline 运行脚本
- `scripts/run_multiday_fast.jl`：面向 East / West 的 large-instance fast config 脚本
- `scripts/run_multiday_strict.jl`：用于可信度审计的 stricter realism config 脚本
- `scripts/run_multiday_or_v1.jl`：OR 支线第一步（更早 depot-aware 内生化）的实验脚本
- `scripts/run_multiday_or_v2.jl`：OR 支线第二步（severe bucket guard）的实验脚本
- `scripts/run_multiday_or_v3.jl`：OR 支线第三步（refill veto under depot stress）的实验脚本
- `scripts/run_multiday_or_v4.jl`：OR 支线第四步（bucket-aware insertion scoring）的实验脚本
- `scripts/run_multiday_or_v4_1.jl`：OR 支线第四步细化版（targeted insertion bias）的实验脚本
- `scripts/run_multiday_or_v5.jl`：OR 支线第五步（controller-to-routing bucket feedback）的实验脚本

## 运行方式
```bash
cd '/Users/zhangjiajia/Life-OS/20-29 Study/22.04fresh_solver/src/algorithms/fresh_solver/julia'
julia --project=. scripts/run_day.jl
```

## 当前结果文件
- `results/raw_runs/herlev_single_day_baseline_julia.json`
- `results/raw_runs/herlev_multiday_baseline_julia.json`

## 当前 repair 状态
- 已从 gate-only baseline 扩展到 `gate + picking + staging` diagnostics v1
- repair 现支持基于最坏 bucket 的小范围 departure shift
- repair 已升级到 `overload-focused reassignment / rollback v1`
- 当前 penalty 已能输出每个 bucket 的 departures / picking / staging / overload 分解

## 当前 rolling 状态
- strongest chain 已收口成 `multi-day rolling runner v1`
- 可直接运行 `scripts/run_multiday.jl` 对 Herlev horizon 做日序滚动
- 可运行 `scripts/run_multiday_fast.jl` 对 East / West 使用 fast config
- 可运行 `scripts/run_multiday_strict.jl` 对 Herlev / East / West 做 stricter realism 对照
- 可运行 `scripts/run_multiday_or_v1.jl` 启动 OR 支线第一步实验（更早 depot-aware admission + routing tightening）
- 可运行 `scripts/run_multiday_or_v2.jl` 启动 OR 支线第二步实验（severe bucket guard）
- 可运行 `scripts/run_multiday_or_v3.jl` 启动 OR 支线第三步实验（refill veto under depot stress）
- 可运行 `scripts/run_multiday_or_v4.jl` 启动 OR 支线第四步实验（bucket-aware insertion scoring）
- 可运行 `scripts/run_multiday_or_v4_1.jl` 启动 OR 支线第四步细化实验（targeted insertion bias）
- 可运行 `scripts/run_multiday_or_v5.jl` 启动 OR 支线第五步实验（controller-to-routing bucket feedback）
- 当前多日 runner 使用：visible orders + carryover + controller feedback + routing + repair 的串联流程

## 下一步最优先
1. 进一步优化 vehicle-type-aware bias，避免当前轻量偏置损伤总 assignment
2. 把 overload-focused reassignment 从当前 fragment v2 扩展到更强的 route/customer 局部重构
3. 把 controller 的 rolling feedback 从单次收紧升级为多档/自适应收紧策略
4. 在 East / West 上开始更系统的 multi-day rolling experiments
