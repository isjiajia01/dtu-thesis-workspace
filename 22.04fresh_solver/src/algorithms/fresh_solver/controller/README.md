# controller

负责跨日 admission / protection / clipping。

第一版代码实现顺序：
1. `scoring.py`：订单打分
2. `policy.py`：protected reservation + flex clipping
3. 后续再加入：
   - plan stability penalty
   - depot-risk-aware clipping
   - request-age promotion
   - explicit route budget hints
