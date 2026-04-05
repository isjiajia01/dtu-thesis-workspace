# repair

负责 depot-aware diagnostics 与后优化修复。

第一版代码实现顺序：
1. `diagnostics.py`：gate bucket 画像
2. `policy.py`：departure smoothing baseline
3. 后续补：
   - picking / staging profile
   - overload-focused reassignment
   - route split / rollback / refill
   - selective risky-flex removal
