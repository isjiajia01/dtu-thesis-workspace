# results

本目录用于存放实验输出。

## 推荐内容
- `summary_tables/`：汇总表
- `raw_runs/`：单次运行原始 JSON
- `figures/`：绘图输入与图表
- `diagnostics/`：depot / routing / controller 诊断输出

## 建议输出字段
每次运行至少输出：
- instance name
- config name
- assigned / unassigned / deferred / expired
- route count
- distance / duration
- trip2 route count
- depot penalty
- overload bucket count
- runtime seconds
- failure reason breakdown
