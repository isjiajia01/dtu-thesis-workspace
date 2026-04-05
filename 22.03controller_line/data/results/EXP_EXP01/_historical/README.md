# Historical EXP01 Endpoints

这个目录是实际 historical endpoint 存储层。

它的职责是说明：哪些 endpoint 虽然仍保留在 `EXP_EXP01/` 下，但默认应视为 historical / exploratory / non-default evidence。

## 为什么不直接搬目录

当前分析脚本直接读取 `EXP_EXP01/` 下的 sibling endpoint 目录。

如果直接把历史 endpoint 迁走，或者复制出带 `summary_final.json` 的镜像目录，会有两个风险：

- 破坏现有脚本和人工习惯路径
- 被聚合脚本重复扫描，导致结果重复计数

因此当前采用的是：

- retained endpoint 放入 `../_retained/`
- historical endpoint 放入 `../_historical/`
- 聚合脚本按递归 endpoint 发现逻辑读取，不依赖旧的 root-level sibling 布局

## 默认视为 historical 的内容

除 `../_retained/README.md` 列出的 endpoint 之外，本目录下其余大多数 endpoint 都应先视为 historical。

典型类型包括：

- 早期 / 已放弃方法线：
  - `scenario1_robust_v3_*`
  - `scenario1_robust_v6a*`
  - `scenario1_robust_v6b*`
  - `scenario1_robust_v6c*`
  - `scenario1_robust_v6d*`
  - `scenario1_robust_v6e*`
  - `scenario1_robust_v6h*`
- 历史 OOD sweep：
  - `scenario1_ood_*_cap05`
  - `scenario1_ood_*_dyn60_*`
  - `scenario1_ood_*_dyn90_*`
  - 非 retained 的 `scenario1_ood_*_v6d_compute300`
- 历史 `DATA003` sweep：
  - 非 retained 的 east/west tuning lines
  - `v6g60`
  - `v6g90r`
  - 各类 `w16h` / `dyn*` 历史组合
- 调试或诊断目录：
  - `*_probe`
  - `*_smoke`

## 使用原则

这些 endpoint 可以用于：

- traceability
- 机制回查
- 反例说明
- 内部诊断

这些 endpoint 不应默认用于：

- 当前结果章节 headline ranking
- 当前 Herlev mainline 最终 controller 对比
- 当前 retained OOD / DATA003 canonical evidence

## 真正的边界定义

当前 thesis 的最终 retained boundary 仍以这些文件为准：

- `../README.md`
- `../../paper/THESIS_EXPERIMENT_WRITING_MAP.md`
- `../../paper/CLAIM_GUARDRAILS.md`
- `../../docs/decisions.md`
