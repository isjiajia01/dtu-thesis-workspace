from __future__ import annotations

from typing import Iterable, List

from ..core.config import ControllerConfig
from ..core.models import ControllerDecision, DayState, Order
from .scoring import score_order


def make_controller_decision(
    planning_date,
    orders: Iterable[Order],
    day_state: DayState,
    config: ControllerConfig,
) -> ControllerDecision:
    orders = list(orders)
    scores = {order.order_id: score_order(order, planning_date, day_state, config) for order in orders}
    ranked = sorted(orders, key=lambda order: scores[order.order_id].total_score, reverse=True)

    protected_count = max(1, int(len(ranked) * config.protected_reserve_ratio)) if ranked else 0
    admitted_cap = int(len(ranked) * config.flex_admission_cap_ratio)
    admitted_cap = max(admitted_cap, protected_count)

    protected = [order.order_id for order in ranked[:protected_count]]
    admitted = [order.order_id for order in ranked[protected_count:admitted_cap]]
    deferred = [order.order_id for order in ranked[admitted_cap:]]

    return ControllerDecision(
        planning_date=planning_date,
        protected_order_ids=protected,
        admitted_flex_order_ids=admitted,
        deferred_order_ids=deferred,
        order_scores=scores,
        metadata={
            "protected_count": len(protected),
            "admitted_flex_count": len(admitted),
            "deferred_count": len(deferred),
        },
    )
