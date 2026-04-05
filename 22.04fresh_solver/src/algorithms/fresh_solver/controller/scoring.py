from __future__ import annotations

from datetime import date

from ..core.config import ControllerConfig
from ..core.models import DayState, Order, OrderScore


def score_order(order: Order, planning_date: date, day_state: DayState, config: ControllerConfig) -> OrderScore:
    days_to_deadline = max((order.service_date_to - planning_date).days, 0)
    waiting_days = max((planning_date - order.requested_date).days, 0)
    window_days = max((order.service_date_to - order.service_date_from).days, 0)

    urgency_score = config.urgency_weight / max(days_to_deadline + 1, 1)
    age_score = config.age_weight * waiting_days
    risk_score = config.risk_weight / max(window_days + 1, 1)
    commitment_score = config.commitment_weight if order.order_id in day_state.committed_order_ids else 0.0
    depot_adjustment = 0.0

    total_score = urgency_score + age_score + risk_score + commitment_score - depot_adjustment
    tags = []
    if days_to_deadline <= 1:
        tags.append("near_deadline")
    if waiting_days >= 2:
        tags.append("aged")
    if window_days == 0:
        tags.append("tight_window")

    return OrderScore(
        order_id=order.order_id,
        total_score=total_score,
        urgency_score=urgency_score,
        age_score=age_score,
        risk_score=risk_score,
        commitment_score=commitment_score,
        depot_adjustment=depot_adjustment,
        tags=tags,
    )
