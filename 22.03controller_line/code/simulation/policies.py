import math
from datetime import datetime


def _uses_oracle_targets(config) -> bool:
    mode = str((config or {}).get("information_mode", "strict_online")).lower()
    return mode in {"forecast_informed", "oracle", "full_oracle", "legacy_oracle"}

# =========================================================
# Base
# =========================================================
class BasePolicy:
    """
    Unified policy interface + debug/trace.

    Rolling passes:
      - prev_planned_ids: yesterday "carryover pool" (planned but NOT delivered)
      - prev_selected_ids: yesterday planned set (for plan-churn metrics / optional freeze)
      - future_capacity_pressure: min capacity ratio in lookahead window
      - pressure_k_star: offset (0=today) of worst ratio day in lookahead window
    """

    def __init__(self, config=None):
        self.base_config = (config or {}).copy()
        self.config = self.base_config.copy()
        self.last_debug_info = {
            "quota_flex": -1,
            "total_flex_demand": 0,
            "selected_flex_demand": 0,
            "is_quota_binding": False,
            "kept_count": 0,
            "frozen_count": 0,
            "is_under_pressure": False,
            "hard_overflow": 0,
            "mode_status": "normal",
            "future_pressure": 1.0,
            "pressure_k_star": 999,
            # deadline guardrail
            "mandatory_count": 0,
        }
        self.last_trace = {}

    def select_orders(
        self,
        current_date,
        visible_orders,
        analyzer,
        prev_planned_ids,
        daily_capacity_colli=None,
        prev_selected_ids=None,
        **kwargs,
    ):
        # Defensive fallback: if BasePolicy is ever instantiated due to wiring issues,
        # dispatch to the intended concrete policy based on config["mode"].
        mode = (self.config or {}).get("mode", "proactive_quota")
        if mode == "greedy":
            return GreedyPolicy(self.config).select_orders(
                current_date=current_date,
                visible_orders=visible_orders,
                analyzer=analyzer,
                prev_planned_ids=prev_planned_ids,
                daily_capacity_colli=daily_capacity_colli,
                prev_selected_ids=prev_selected_ids,
                **kwargs,
            )
        if mode == "stability":
            return StabilityPolicy(self.config).select_orders(
                current_date=current_date,
                visible_orders=visible_orders,
                analyzer=analyzer,
                prev_planned_ids=prev_planned_ids,
                daily_capacity_colli=daily_capacity_colli,
                prev_selected_ids=prev_selected_ids,
                **kwargs,
            )
        # default: proactive
        return ProactivePolicy(self.config).select_orders(
            current_date=current_date,
            visible_orders=visible_orders,
            analyzer=analyzer,
            prev_planned_ids=prev_planned_ids,
            daily_capacity_colli=daily_capacity_colli,
            prev_selected_ids=prev_selected_ids,
            **kwargs,
        )

    @staticmethod
    def _days_until(date_str, current_date):
        if not date_str:
            return 999999
        return (datetime.strptime(date_str, "%Y-%m-%d") - current_date).days

    @staticmethod
    def _safe_deadline(order):
        fds = order.get("feasible_dates") or []
        return fds[-1] if fds else None

    @staticmethod
    def _xy_from_location(loc):
        if loc is None:
            return 0.0, 0.0
        if isinstance(loc, dict):
            if "x" in loc and "y" in loc:
                return float(loc.get("x", 0.0)), float(loc.get("y", 0.0))
            if "lon" in loc and "lat" in loc:
                return float(loc.get("lon", 0.0)), float(loc.get("lat", 0.0))
            if "lng" in loc and "lat" in loc:
                return float(loc.get("lng", 0.0)), float(loc.get("lat", 0.0))
        if isinstance(loc, (list, tuple)) and len(loc) >= 2:
            return float(loc[0]), float(loc[1])
        return 0.0, 0.0

    def _service_criticality_score(self, order, current_date, carry_prev_ids, buffer_order_ids, carryover_age_map, depot):
        oid = str(order.get("id"))
        deadline = self._safe_deadline(order)
        days_left = self._days_until(deadline, current_date)
        demand = float(order.get("demand", {}).get("colli", 0.0))
        carry_age = float((carryover_age_map or {}).get(oid, 0))
        carry_flag = 1.0 if oid in (carry_prev_ids or set()) else 0.0
        buffer_flag = 1.0 if oid in (buffer_order_ids or set()) else 0.0
        ox, oy = self._xy_from_location(order.get("location"))
        dx, dy = self._xy_from_location(depot.get("location") if isinstance(depot, dict) else None)
        route_burden = math.hypot(ox - dx, oy - dy)
        return (
            8.0 / (days_left + 1.0)
            + 1.5 * carry_flag
            + 0.7 * carry_age
            + 1.2 * buffer_flag
            - 0.08 * demand
            - 0.03 * route_burden
        )

    def _execution_shadow_cost(self, order, current_date, depot, daily_capacity_colli):
        deadline = self._safe_deadline(order)
        days_left = self._days_until(deadline, current_date)
        demand = float(order.get("demand", {}).get("colli", 0.0))
        service_time = float(order.get("service_time", 0.0))
        delivery_window_days = int(order.get("delivery_window_days", 0) or 0)
        ox, oy = self._xy_from_location(order.get("location"))
        dx, dy = self._xy_from_location(depot.get("location") if isinstance(depot, dict) else None)
        route_burden = math.hypot(ox - dx, oy - dy)
        demand_ratio = demand / max(1.0, float(daily_capacity_colli or 1.0))
        service_ratio = service_time / 20.0
        single_window_flag = 1.0 if delivery_window_days <= 1 else 0.0
        near_deadline_flag = 1.0 if days_left <= 1 else 0.0
        return (
            0.45 * demand_ratio
            + 0.30 * service_ratio
            + 0.20 * route_burden
            + 0.35 * single_window_flag
            + 0.20 * near_deadline_flag
        )

    def _execution_priority_score(self, order, current_date, depot, daily_capacity_colli):
        deadline = self._safe_deadline(order)
        days_left = self._days_until(deadline, current_date)
        delivery_window_days = int(order.get("delivery_window_days", 0) or 0)
        demand = float(order.get("demand", {}).get("colli", 0.0))
        service_time = float(order.get("service_time", 0.0))
        demand_ratio = demand / max(1.0, float(daily_capacity_colli or 1.0))
        shadow_cost = self._execution_shadow_cost(order, current_date, depot, daily_capacity_colli)
        urgency_bonus = 5.0 / (days_left + 1.0)
        single_window_bonus = 1.5 if delivery_window_days <= 1 else 0.0
        ease_bonus = 1.0 / (1.0 + service_time / 20.0 + demand_ratio)
        return urgency_bonus + single_window_bonus + ease_bonus - shadow_cost

    def _read_pressure(self, **kwargs):
        """
        Normalize pressure keys to:
          - future_pressure: min capacity ratio ahead
          - k_star: offset of worst day
        """
        future_pressure = kwargs.get(
            "future_capacity_pressure",
            kwargs.get("future_pressure", kwargs.get("min_ratio", 1.0)),
        )
        k_star = kwargs.get("pressure_k_star", kwargs.get("k_star", 999))
        try:
            future_pressure = float(future_pressure)
        except Exception:
            future_pressure = 1.0
        try:
            k_star = int(k_star)
        except Exception:
            k_star = 999
        return future_pressure, k_star

    def _wrap_result(self, orders, hard_orders, current_date, analyzer):
        """Assign dynamic penalties (meters) for OR-Tools disjunctions."""
        result = []
        hard_ids = set(o["id"] for o in hard_orders)

        hard_penalty_m = int(self.config.get("hard_penalty_m", 5_000_000))
        flex_base_m = float(self.config.get("flex_penalty_base_m", 200_000))
        flex_beta = float(self.config.get("flex_penalty_beta", 0.2))
        flex_min_m = int(self.config.get("flex_penalty_min_m", 50_000))
        flex_max_m = int(self.config.get("flex_penalty_max_m", 2_000_000))
        execution_guard_level = max(0.0, float(self.config.get("execution_guard_level", 0.0) or 0.0))
        execution_penalty_spread = max(0.0, float(self.config.get("execution_penalty_spread", 0.0) or 0.0))
        depot = self.config.get("depot_context")
        daily_capacity_colli = float(self.config.get("daily_capacity_context", 1.0) or 1.0)
        reserved_hard_ids = set(self.config.get("reserved_hard_ids", []) or [])
        reserved_hard_penalty_multiplier = max(1.0, float(self.config.get("solver_reserved_hard_penalty_multiplier", 1.0) or 1.0))
        hard_priority_norm = {}
        if execution_guard_level > 0.0 and execution_penalty_spread > 0.0 and hard_orders:
            raw_scores = []
            for o in hard_orders:
                raw_scores.append((o.get("id"), self._execution_priority_score(o, current_date, depot, daily_capacity_colli)))
            vals = [score for _, score in raw_scores]
            min_score = min(vals)
            max_score = max(vals)
            scale = max(max_score - min_score, 1e-9)
            for oid, score in raw_scores:
                hard_priority_norm[oid] = (score - min_score) / scale

        for o in orders:
            o_copy = o.copy()
            oid = o_copy.get("id")
            if oid in hard_ids:
                if oid in reserved_hard_ids:
                    multiplier = min(8.0, reserved_hard_penalty_multiplier)
                    o_copy["dynamic_penalty"] = int(round(hard_penalty_m * multiplier))
                elif oid in hard_priority_norm:
                    centered = float(hard_priority_norm[oid]) - 0.5
                    multiplier = 1.0 + execution_guard_level * execution_penalty_spread * centered
                    multiplier = max(0.80, min(1.20, multiplier))
                    o_copy["dynamic_penalty"] = int(round(hard_penalty_m * multiplier))
                else:
                    o_copy["dynamic_penalty"] = hard_penalty_m
            else:
                delta = 0
                if getattr(analyzer, "uses_oracle_targets", True):
                    t_str = analyzer.get_target_day(oid)
                    if t_str:
                        # delta > 0 means late vs target -> higher penalty
                        delta = (current_date - datetime.strptime(t_str, "%Y-%m-%d")).days
                else:
                    deadline = self._safe_deadline(o_copy)
                    days_left = self._days_until(deadline, current_date)
                    urgency_window = int(self.config.get("online_penalty_urgency_days", 2))
                    delta = max(0, urgency_window - max(0, days_left))
                penalty = int(flex_base_m * math.exp(flex_beta * delta))
                penalty = max(flex_min_m, min(flex_max_m, penalty))
                o_copy["dynamic_penalty"] = penalty
            result.append(o_copy)
        return result

    def on_day_end(self, day_stats: dict):
        """Optional hook. Kept for compatibility (no-op by default)."""
        return


# =========================================================
# Greedy
# =========================================================
class GreedyPolicy(BasePolicy):
    """Greedy: feasible-today by earliest deadline until physical capacity."""

    def select_orders(self, current_date, visible_orders, analyzer, prev_planned_ids, daily_capacity_colli=None, prev_selected_ids=None, **kwargs):
        today_str = current_date.strftime("%Y-%m-%d")
        phys_cap = float(daily_capacity_colli) if daily_capacity_colli is not None else float("inf")

        candidates = [o for o in visible_orders if today_str in (o.get("feasible_dates") or [])]
        candidates.sort(key=lambda x: (self._safe_deadline(x) or "9999-12-31", x.get("id")))

        selected, load = [], 0.0
        for o in candidates:
            c = float(o["demand"]["colli"])
            if load + c <= phys_cap:
                o_copy = o.copy()
                o_copy["dynamic_penalty"] = int(self.config.get("greedy_penalty_m", 10_000_000))
                selected.append(o_copy)
                load += c

        self.last_debug_info.update({
            "mode_status": "greedy",
            "quota_flex": float("inf"),
            "total_flex_demand": 0.0,
            "selected_flex_demand": 0.0,
            "is_quota_binding": False,
            "kept_count": 0,
            "frozen_count": 0,
            "is_under_pressure": False,
            "hard_overflow": 0.0,
            "mandatory_count": 0,
        })
        self.last_trace = {"mode": "greedy", "selected_load": load, "phys_cap": phys_cap, "selected_ids": [o["id"] for o in selected]}
        return selected


# =========================================================
# Proactive Smooth (fixed for crunch story) + Deadline Guardrail
# =========================================================
class ProactivePolicy(BasePolicy):
    """
    ProactiveSmooth:
      - Normal days: smoothing around analyzer target (quota)
      - Pre-crunch: force high fill ratio to burn backlog BEFORE crunch hits
      - Crunch (imminent): crisis fill to avoid avalanche
      - Pseudo-hard: if an order's deadline falls inside the upcoming crunch window,
        treat as hard-ish to avoid deferring into crunch days.

    Deadline Guardrail (advisor branch A):
      - Any order with days_to_deadline <= deadline_guardrail_days (default 1)
        MUST be included in today's selected set if it's feasible today,
        even if this exceeds buffer_ratio / quota.
      - This targets policy_rejected_or_unserved and shifts pressure to VRP.
    """

    def __init__(self, config):
        super().__init__(config)

        # Memory initialization for feedback loop
        # Use None to indicate "no history yet" (not 0)
        self.last_day_drop_rate: float | None = None
        self.last_day_failures: int | None = None

    def on_day_end(self, day_stats):
        """
        Feedback loop: update memory variables at end of each day.

        Args:
            day_stats: dict with keys like 'vrp_dropped', 'failures', 'planned', etc.
        """
        try:
            planned = float(day_stats.get('planned', 0))
            dropped = float(day_stats.get('vrp_dropped', 0))
            failures = int(day_stats.get('failures', 0))

            # Update drop rate
            if planned > 0:
                self.last_day_drop_rate = dropped / planned
            else:
                self.last_day_drop_rate = 0.0

            # Update failures
            self.last_day_failures = failures

        except Exception as e:
            print(f"[ProactivePolicy] on_day_end failed: {e}")
            self.last_day_drop_rate = 0.0
            self.last_day_failures = 0

    def _is_precrunch(self, future_pressure, k_star):
        # Detect "we know crunch is coming but not yet today"
        eps = float(self.config.get("threshold_eps", 1e-9))
        precrunch_threshold = float(self.config.get("precrunch_threshold", self.config.get("crunch_threshold", 0.85)))
        precrunch_horizon = int(self.config.get("precrunch_horizon", int(self.config.get("pressure_lookahead", 7))))
        return (future_pressure <= precrunch_threshold + eps) and (k_star > 0) and (k_star <= precrunch_horizon)

    def _is_crisis(self, future_pressure, k_star):
        eps = float(self.config.get("threshold_eps", 1e-9))
        crisis_threshold = float(self.config.get("crisis_threshold", self.config.get("crunch_threshold", 0.72)))
        crisis_horizon = int(self.config.get("crisis_horizon", int(self.config.get("pressure_trigger_horizon", 2))))
        return (future_pressure <= crisis_threshold + eps) and (k_star <= crisis_horizon)

    def _pseudo_hard_cutoff(self, k_star):
        # Deadline within [today, today + k_star + buffer] becomes pseudo-hard
        buf = int(self.config.get("pseudo_hard_buffer_days", 2))
        return max(0, int(k_star) + buf)

    def _deadline_guardrail(self, current_date, today_str, visible_orders):
        """
        Return mandatory orders + ids to be forced into today's selection.
        Only includes orders feasible today.
        """
        enabled = bool(self.config.get("deadline_guardrail_enabled", True))
        if not enabled:
            return [], set()

        guard_days = int(self.config.get("deadline_guardrail_days", 1))
        mandatory = []
        mandatory_ids = set()
        for o in visible_orders:
            fds = o.get("feasible_dates") or []
            if today_str not in fds:
                continue
            dl = fds[-1] if fds else None
            if self._days_until(dl, current_date) <= guard_days:
                oid = o.get("id")
                if oid is not None and oid not in mandatory_ids:
                    mandatory.append(o)
                    mandatory_ids.add(oid)
        return mandatory, mandatory_ids

    def select_orders(self, current_date, visible_orders, analyzer, prev_planned_ids, daily_capacity_colli=None, prev_selected_ids=None, **kwargs):
        control_action = kwargs.pop("control_action", None)
        self.config = self.base_config.copy()
        if control_action is not None and hasattr(control_action, "to_policy_overrides"):
            self.config.update(control_action.to_policy_overrides())
        event_mode = str(self.config.get("event_mode", "none")).lower()
        committed_ids = set(getattr(control_action, "committed_order_ids", ()) or ())
        buffered_ids = set(getattr(control_action, "buffered_order_ids", ()) or ())
        deferred_ids = set(getattr(control_action, "deferred_order_ids", ()) or ())
        carryover_age_map = kwargs.get("carryover_age_map", {}) or {}
        buffer_order_ids = set(kwargs.get("buffer_order_ids", set()) or set())

        # DEBUG: Print for first 5 days
        if current_date.day <= 5:
            print(f"[Day {current_date.day}] ProactivePolicy.select_orders called, visible_orders={len(visible_orders)}")

        today_str = current_date.strftime("%Y-%m-%d")
        phys_cap = float(daily_capacity_colli) if daily_capacity_colli is not None else float("inf")
        effective_cap = min(
            phys_cap,
            float(getattr(control_action, "effective_capacity_colli", phys_cap) or phys_cap),
        )
        effective_stop_budget = int(getattr(control_action, "effective_stop_budget", 10**9) or 10**9)

        base_lookahead = int(self.config.get("lookahead_days", 3))
        buffer_ratio = float(self.config.get("buffer_ratio", 1.05))
        reserve_capacity_ratio = max(0.0, float(self.config.get("reserve_capacity_ratio", 0.0)))
        flex_commitment_ratio = max(0.0, min(1.0, float(self.config.get("flex_commitment_ratio", 1.0))))
        w = self.config.get("weights", {"urgency": 20.0, "profile": 2.0})

        oracle_planner_enabled = _uses_oracle_targets(self.config) and getattr(analyzer, "uses_oracle_targets", True)

        future_pressure, k_star = self._read_pressure(**kwargs)
        crunch_aware = bool(self.config.get("crunch_aware", True))
        if not crunch_aware or not oracle_planner_enabled:
            future_pressure, k_star = 1.0, 999
        eps = float(self.config.get("threshold_eps", 1e-9))
        cap_ratio_today = float(kwargs.get("capacity_ratio_today", kwargs.get("cap_ratio_today", 1.0)))
        prev_day_planned = kwargs.get("prev_day_planned", None)
        prev_day_vrp_dropped = kwargs.get("prev_day_vrp_dropped", None)
        depot = kwargs.get("depot", None)
        self.config["depot_context"] = depot
        self.config["daily_capacity_context"] = float(daily_capacity_colli) if daily_capacity_colli is not None else float("inf")
        execution_guard_level = max(0.0, float(self.config.get("execution_guard_level", 0.0) or 0.0))
        execution_penalty_spread = max(0.0, float(self.config.get("execution_penalty_spread", 0.0) or 0.0))
        execution_hard_sort_enabled = bool(self.config.get("execution_hard_sort_enabled", False))
        hard_stop_reservation_enabled = bool(self.config.get("hard_stop_reservation_enabled", False))
        hard_stop_reservation_ratio = max(0.0, float(self.config.get("hard_stop_reservation_ratio", 0.0) or 0.0))
        hard_capacity_reservation_ratio = max(0.0, float(self.config.get("hard_capacity_reservation_ratio", 0.0) or 0.0))

        # Active crunch (today is already constrained) should not fall back to SMOOTH.
        active_crunch_enabled = bool(self.config.get("active_crunch_enabled", True))
        precrunch_threshold = float(self.config.get("precrunch_threshold", self.config.get("crunch_threshold", 0.85)))
        is_active_crunch = active_crunch_enabled and (
            (cap_ratio_today < 1.0 - eps)
            or (oracle_planner_enabled and k_star == 0 and future_pressure <= precrunch_threshold + eps)
        )


        is_precrunch = self._is_precrunch(future_pressure, k_star) if oracle_planner_enabled else False
        is_crisis = self._is_crisis(future_pressure, k_star) if oracle_planner_enabled else False

        future_pressure_debug = float(future_pressure) if oracle_planner_enabled else float("nan")
        k_star_debug = int(k_star) if oracle_planner_enabled else -1

        self.last_debug_info.update({
            "future_pressure": future_pressure_debug,
            "pressure_k_star": k_star_debug,
            "is_under_pressure": bool((future_pressure < float(self.config.get("crunch_threshold", 0.85))) if oracle_planner_enabled else (cap_ratio_today < 1.0 - eps)),
        })

        # Guardrail mandatory set (computed once per day)
        mandatory_orders, mandatory_ids = self._deadline_guardrail(current_date, today_str, visible_orders)

        self.last_debug_info.update({
            'capacity_ratio_today': cap_ratio_today,
            'visible_orders_count': len(visible_orders),
        })

        # -------------------------
        # Crisis / Active-Crunch mode: rescue behavior
        #   - prioritize near-deadline orders
        #   - cap number of attempted stops when VRP is dropping too much
        #   - within the same deadline band, prefer more "routeable" optional orders
        # -------------------------
        if is_crisis or is_active_crunch:
            # Ablation toggles (default True):
            enable_stop_cap = bool(self.config.get("crisis_enable_stop_cap", True))
            enable_routeability = bool(self.config.get("crisis_enable_routeability", True))
            # Yesterday drop rate proxy (used for adaptive gating)
            prev_drop_rate = 0.0
            try:
                if (prev_day_planned is not None) and (prev_day_vrp_dropped is not None) and float(prev_day_planned) > 0:
                    prev_drop_rate = float(prev_day_vrp_dropped) / float(prev_day_planned)
            except Exception:
                prev_drop_rate = 0.0

            # Routeability gating (optional): turn ON routeability only when pressure is sufficiently high.
            # Modes:
            #  - "fixed"   : use crisis_enable_routeability as-is
            #  - "ratio"   : enable if cap_ratio_today <= crisis_routeability_ratio_threshold
            #  - "drop"    : enable if prev_drop_rate >= crisis_routeability_drop_threshold
            #  - "pressure": enable if (k_star <= crisis_routeability_kstar_threshold) OR (future_pressure <= crisis_routeability_pressure_threshold)
            thr = None
            tau = None
            k_thr = None
            p_thr = None
            route_mode = str(self.config.get("crisis_routeability_mode", "fixed")).lower()
            if route_mode == "ratio":
                thr = float(self.config.get("crisis_routeability_ratio_threshold", 0.65))
                enable_routeability = bool(enable_routeability and (cap_ratio_today <= thr + eps))
            elif route_mode == "drop":
                tau = float(self.config.get("crisis_routeability_drop_threshold", 0.12))
                enable_routeability = bool(enable_routeability and (prev_drop_rate >= tau - eps))
            elif route_mode == "pressure" and oracle_planner_enabled:
                # IMPORTANT: routeability value often appears in the *precrunch* window (cap_ratio_today may still be 1.0),
                # so we gate using the forward-looking pressure signal (future_pressure, k_star) instead of today's ratio.
                k_thr = int(self.config.get("crisis_routeability_kstar_threshold", 2))
                p_thr = float(self.config.get("crisis_routeability_pressure_threshold", 0.80))
                enable_routeability = bool(enable_routeability and ((k_star <= k_thr) or (future_pressure <= p_thr + eps)))
            elif route_mode == "pressure":
                thr = float(self.config.get("crisis_routeability_ratio_threshold", 0.65))
                enable_routeability = bool(enable_routeability and (cap_ratio_today <= thr + eps))
            else:
                # fixed/unknown: keep as-is (thr/tau/k_thr/p_thr stay None)
                pass

            candidates = [o for o in visible_orders if today_str in (o.get("feasible_dates") or [])]
            for o in candidates:
                o["_days_left_tmp"] = self._days_until(self._safe_deadline(o), current_date)

            # --- adaptive max stops (optional) ---

            if enable_stop_cap:

                            crisis_max_stops = int(self.config.get("crisis_max_stops", 10**9))

                            drop_trigger = float(self.config.get("crisis_drop_rate_trigger", 0.10))

                            drop_gain = float(self.config.get("crisis_drop_rate_gain", 1.0))

                            min_factor = float(self.config.get("crisis_min_stop_factor", 0.60))

                            cap_ratio_stop_scale = float(self.config.get("crisis_ratio_stop_scale", 0.85))


                            try:

                                if prev_day_planned is not None and prev_day_vrp_dropped is not None and int(prev_day_planned) > 0:

                                    dr = float(prev_day_vrp_dropped) / float(max(1, int(prev_day_planned)))

                                    if dr >= drop_trigger:

                                        factor = max(min_factor, 1.0 - drop_gain * (dr - drop_trigger))

                                        crisis_max_stops = int(max(1, math.floor(int(prev_day_planned) * factor)))

                                    else:

                                        crisis_max_stops = int(max(1, math.ceil(int(prev_day_planned) * 1.05)))

                            except Exception:

                                pass


                            if cap_ratio_today < 1.0 - eps:

                                crisis_max_stops = int(max(1, math.floor(crisis_max_stops * cap_ratio_stop_scale)))


                            crisis_max_stops = int(max(crisis_max_stops, len(mandatory_orders)))
                            crisis_max_stops = int(min(crisis_max_stops, effective_stop_budget))

            else:

                # Stop-cap disabled: do not constrain attempted stops beyond mandatory.

                crisis_max_stops = int(self.config.get("crisis_max_stops", 10**9))

                # (Optional) keep ratio scaling when stop-cap is disabled

                if bool(self.config.get("crisis_scale_with_ratio_when_stopcap_off", False)) and cap_ratio_today < 1.0 - eps:

                    cap_ratio_stop_scale = float(self.config.get("crisis_ratio_stop_scale", 0.85))

                    crisis_max_stops = int(max(1, math.floor(crisis_max_stops * cap_ratio_stop_scale)))
                crisis_max_stops = int(min(crisis_max_stops, effective_stop_budget))

            # --- partition: hard first (near deadline) ---
            hard_days = int(self.config.get("crisis_hard_days", 2))

            # Extra deadline protection (hard-first window) under tight conditions.
            # Rationale: when the system is in active crunch (k_star==0) or today's ratio is tight, we must protect
            # near-deadline orders from being displaced by routeability heuristics.
            if bool(self.config.get("crisis_hard_days_boost_on_tight", True)):
                tight_ratio = float(self.config.get("crisis_hard_days_tight_ratio", 0.70))
                boost_to = int(self.config.get("crisis_hard_days_boost_to", 3))
                if (cap_ratio_today <= tight_ratio + eps) or (k_star == 0):
                    hard_days = max(hard_days, boost_to)

            # Optional: also boost based on observed drop rate yesterday
            if bool(self.config.get("crisis_hard_days_boost_on_drop", False)):
                drop_thr = float(self.config.get("crisis_hard_days_boost_drop_threshold", 0.15))
                boost_to = int(self.config.get("crisis_hard_days_boost_to", 3))
                if prev_drop_rate >= drop_thr - eps:
                    hard_days = max(hard_days, boost_to)
            hard = [o for o in candidates if int(o.get("_days_left_tmp", 9999)) <= hard_days]
            if execution_hard_sort_enabled and execution_guard_level > 0.0:
                hard.sort(
                    key=lambda x: (
                        x.get("_days_left_tmp", 9999),
                        -self._execution_priority_score(x, current_date, depot, effective_cap),
                        self._safe_deadline(x) or "9999-12-31",
                        x.get("id"),
                    )
                )
            else:
                hard.sort(key=lambda x: (x.get("_days_left_tmp", 9999), self._safe_deadline(x) or "9999-12-31", x.get("id")))

            hard_ids = set(o["id"] for o in hard)
            optional = [o for o in candidates if o["id"] not in hard_ids]

            # --- routeability proxy for optional ---
            if enable_routeability:
                            def _xy_from_location(loc):
                                """Robustly parse location that may be dict {'x','y'} or list/tuple [x,y]."""
                                if loc is None:
                                    return 0.0, 0.0
                                # dict-like
                                if isinstance(loc, dict):
                                    if 'x' in loc and 'y' in loc:
                                        return float(loc.get('x', 0.0)), float(loc.get('y', 0.0))
                                    if 'lon' in loc and 'lat' in loc:
                                        return float(loc.get('lon', 0.0)), float(loc.get('lat', 0.0))
                                    if 'lng' in loc and 'lat' in loc:
                                        return float(loc.get('lng', 0.0)), float(loc.get('lat', 0.0))
                                # list/tuple [x,y]
                                if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                                    return float(loc[0]), float(loc[1])
                                return 0.0, 0.0

                            def _xy_from_entity(ent):
                                """Entity may be an order or depot; supports top-level x/y or nested location."""
                                if ent is None:
                                    return 0.0, 0.0
                                if isinstance(ent, dict):
                                    if 'x' in ent and 'y' in ent:
                                        try:
                                            return float(ent.get('x', 0.0)), float(ent.get('y', 0.0))
                                        except Exception:
                                            pass
                                    return _xy_from_location(ent.get('location', None))
                                return 0.0, 0.0

                            def _routeability_score(order, coords_cache):
                                # higher is better
                                if depot is None:
                                    return 0.0
                                ox, oy = _xy_from_entity(order)
                                dx, dy = _xy_from_entity(depot)
                                dist_depot = math.hypot(ox - dx, oy - dy)

                                k = int(self.config.get("crisis_route_knn_k", 5))
                                pts = coords_cache
                                if len(pts) <= 1:
                                    avg_knn = 0.0
                                else:
                                    dists = []
                                    for (px, py) in pts:
                                        dists.append(math.hypot(ox - px, oy - py))
                                    dists.sort()
                                    knn = dists[1:1 + max(1, min(k, len(dists) - 1))]
                                    avg_knn = sum(knn) / float(len(knn)) if knn else 0.0

                                service_time = float(order.get("service_time", 0.0))
                                demand = float(order.get("demand", {}).get("colli", 0.0))
                                demand_ratio = demand / max(1.0, effective_cap)
                                return -dist_depot - avg_knn - 0.03 * service_time - 0.20 * demand_ratio

                            coords_cache = []
                            for o in optional:
                                loc = o.get("location", None)
                                coords_cache.append(_xy_from_location(loc))

                            # Keep deadline discipline: primarily sort by days_left, then by routeability (better first)
                            ranked_optional = []
                            for o in optional:
                                s = _routeability_score(o, coords_cache)
                                ranked_optional.append((int(o.get("_days_left_tmp", 9999)), -s, o))  # -s so smaller is better
                                ranked_optional.sort(key=lambda t: (t[0], t[1], t[2].get("id")))
            else:
                ranked_optional = []
                for o in optional:
                    ranked_optional.append((int(o.get('_days_left_tmp', 9999)), self._safe_deadline(o) or '9999-12-31', o.get('id'), o))
                ranked_optional.sort(key=lambda t: (t[0], t[1], t[2]))


            selected, load = [], 0.0

            reserved_ids = set()
            reserved_stop_quota = 0
            reserved_capacity_quota = 0.0
            if hard_stop_reservation_enabled and execution_guard_level > 0.0 and hard:
                critical_hard = [
                    o for o in hard
                    if int(o.get("_days_left_tmp", 9999)) <= 1 and int(o.get("delivery_window_days", 0) or 0) <= 1
                ]
                if critical_hard:
                    critical_hard.sort(
                        key=lambda x: (
                            -self._execution_shadow_cost(x, current_date, depot, effective_cap),
                            -(float(x.get("service_time", 0.0) or 0.0)),
                            -(float(x.get("demand", {}).get("colli", 0.0) or 0.0)),
                            x.get("id"),
                        )
                    )
                    reserved_stop_quota = min(
                        len(critical_hard),
                        max(1, int(round(float(crisis_max_stops) * max(0.08, hard_stop_reservation_ratio)))),
                    )
                    reserved_capacity_quota = max(
                        0.0,
                        float(effective_cap) * max(0.06, hard_capacity_reservation_ratio),
                    )
                    reserved_load = 0.0
                    for o in critical_hard:
                        if len(reserved_ids) >= reserved_stop_quota:
                            break
                        c = float(o["demand"]["colli"])
                        if load + c > effective_cap:
                            continue
                        if reserved_load >= reserved_capacity_quota and len(reserved_ids) >= max(1, reserved_stop_quota // 2):
                            break
                        selected.append(o)
                        reserved_ids.add(o["id"])
                        load += c
                        reserved_load += c

            hard = [o for o in hard if o.get("id") not in reserved_ids]

            for o in hard:
                if len(selected) >= crisis_max_stops:
                    break
                c = float(o["demand"]["colli"])
                if load + c <= effective_cap:
                    selected.append(o)
                    load += c

            for item in ranked_optional:
                o = item[-1]
                if len(selected) >= crisis_max_stops:
                    break
                c = float(o["demand"]["colli"])
                if load + c <= effective_cap:
                    selected.append(o)
                    load += c

            # Deadline guardrail: force-add mandatory (VRP may drop if infeasible)
            selected_ids = set(o["id"] for o in selected)
            for o in mandatory_orders:
                if o["id"] not in selected_ids:
                    selected.append(o)
                    selected_ids.add(o["id"])

            # penalty: treat all selected as hard in rescue modes
            result = self._wrap_result(selected, selected, current_date, analyzer)

            mode_status = "CRISIS_FILL" if is_crisis else "ACTIVE_CRUNCH_FILL"
            self.last_debug_info.update({
                "mode_status": mode_status,
                "quota_flex": 0.0,
                "total_flex_demand": 0.0,
                "selected_flex_demand": 0.0,
                "is_quota_binding": False,
                "hard_overflow": 0.0,
                "kept_count": 0,
                "frozen_count": 0,
                "mandatory_count": int(len(mandatory_ids)),
                "control_action_name": getattr(control_action, "name", ""),
                "hard_stop_reservation_enabled": bool(hard_stop_reservation_enabled),
                "hard_stop_reservation_ratio": float(hard_stop_reservation_ratio),
                "hard_capacity_reservation_ratio": float(hard_capacity_reservation_ratio),
                "reserved_hard_count": int(len(reserved_ids)),
            })
            self.last_trace = {
                "mode": mode_status.lower(),
                "control_action_name": getattr(control_action, "name", ""),
                "selected_load": load,
                "phys_cap": phys_cap,
                "selected_ids": [o["id"] for o in selected],
                "mandatory_ids": sorted(list(mandatory_ids)),
                "crisis_max_stops": int(crisis_max_stops),
                "enable_stop_cap": bool(enable_stop_cap),
                "enable_routeability": bool(enable_routeability),
                "route_mode": route_mode,
                "prev_drop_rate": float(prev_drop_rate),
                "hard_days": int(hard_days),
                "route_thr": thr,
                "route_tau": tau,
                "route_kthr": k_thr,
                "route_pthr": p_thr,
                "cap_ratio_today": float(cap_ratio_today),
                "prev_day_planned": prev_day_planned,
                "prev_day_vrp_dropped": prev_day_vrp_dropped,
                "hard_stop_reservation_enabled": bool(hard_stop_reservation_enabled),
                "hard_stop_reservation_ratio": float(hard_stop_reservation_ratio),
                "hard_capacity_reservation_ratio": float(hard_capacity_reservation_ratio),
                "reserved_hard_ids": sorted(list(reserved_ids)),
                "reserved_hard_stop_quota": int(reserved_stop_quota),
                "reserved_hard_capacity_quota": float(reserved_capacity_quota),
            }
            self.config["reserved_hard_ids"] = sorted(list(reserved_ids))
            return result

        

        # -------------------------
        # Candidate filter: feasible today + within lookahead (target or deadline)
        # -------------------------
        carry_prev_ids = set(prev_planned_ids or [])
        visible_today_load = sum(
            float(o["demand"]["colli"])
            for o in visible_orders
            if today_str in (o.get("feasible_dates") or [])
        )
        selection_cap = max(0.0, effective_cap)
        commitment_phys_cap = max(0.0, selection_cap * (1.0 - reserve_capacity_ratio))
        candidates = []
        for o in visible_orders:
            fds = o.get("feasible_dates") or []
            if today_str not in fds:
                continue
            dl = fds[-1]
            days_until_deadline = self._days_until(dl, current_date)
            if oracle_planner_enabled:
                t_str = analyzer.get_target_day(o["id"])
                target_gap = self._days_until(t_str, current_date) if t_str else 0

                # On precrunch days: widen lookahead to pull forward backlog
                eff_lookahead = int(self.config.get("precrunch_lookahead", max(base_lookahead, int(self.config.get("pressure_lookahead", 7))))) if is_precrunch else base_lookahead

                if target_gap > eff_lookahead and days_until_deadline > eff_lookahead:
                    continue
            else:
                should_include = (
                    o.get("id") in committed_ids
                    or o.get("id") in buffered_ids
                    or o.get("id") in buffer_order_ids
                    or
                    visible_today_load <= commitment_phys_cap + 1e-9
                    or o.get("id") in carry_prev_ids
                    or days_until_deadline <= base_lookahead
                )
                if not should_include:
                    continue
            candidates.append(o)

        # -------------------------
        # Hard / pseudo-hard / flex split
        # -------------------------
        urgent_hard_days = int(self.config.get("urgent_hard_days", 1))
        pseudo_cut = self._pseudo_hard_cutoff(k_star) if is_precrunch else None

        s_hard, s_pseudo, s_flex = [], [], []
        for o in candidates:
            dl = self._safe_deadline(o)
            days_left = self._days_until(dl, current_date)
            oid = o.get("id")

            if oid in committed_ids or days_left <= urgent_hard_days:
                s_hard.append(o)
            elif (pseudo_cut is not None) and (days_left <= pseudo_cut):
                # deadline falls inside "entering crunch" window -> treat as hard-ish
                s_pseudo.append(o)
            elif oid in deferred_ids and event_mode in {"commit_hold", "commit_shock_triage"}:
                continue
            else:
                s_flex.append(o)

        # pseudo-hard are treated as hard for selection/penalty
        hard_bucket = s_hard + s_pseudo

        # -------------------------
        # Protect hard feasibility (truncate if hard exceeds cap)
        # -------------------------
        hard_bucket.sort(key=lambda x: (self._safe_deadline(x) or "9999-12-31", x.get("id")))
        kept_hard, hard_load = [], 0.0
        for o in hard_bucket:
            c = float(o["demand"]["colli"])
            if hard_load + c <= selection_cap:
                kept_hard.append(o)
                hard_load += c
        hard_overflow = max(0.0, sum(float(o["demand"]["colli"]) for o in hard_bucket) - hard_load)

        # -------------------------
        # Quota (core smoothing knob)
        # -------------------------
        if oracle_planner_enabled:
            target_load = float(analyzer.get_day_target_load(today_str))
            quota_base = target_load * buffer_ratio

            # Precrunch: force min fill ratio (burn backlog)
            if is_precrunch:
                min_fill = float(self.config.get("precrunch_min_fill_ratio", 1.00))
                quota_base = max(quota_base, min_fill * selection_cap)
        else:
            target_load = min(commitment_phys_cap, sum(float(o["demand"]["colli"]) for o in candidates))
            quota_base = max(hard_load, target_load)

        commitment_cap = max(hard_load, commitment_phys_cap)
        quota = min(quota_base, commitment_cap)
        quota_flex = max(0.0, min(quota - hard_load, max(0.0, (commitment_cap - hard_load) * flex_commitment_ratio)))

        # -------------------------
        # Flex scoring (urgency + target delta)
        # -------------------------
        flex_items = []
        stop_pressure = max(
            0.0,
            (float(len(candidates)) - float(effective_stop_budget)) / max(1.0, float(effective_stop_budget)),
        )
        for o in s_flex:
            dl = self._safe_deadline(o)
            days_left = self._days_until(dl, current_date)
            if oracle_planner_enabled:
                t_str = analyzer.get_target_day(o["id"])
                delta = (current_date - datetime.strptime(t_str, "%Y-%m-%d")).days if t_str else 0

                # clamp delta to avoid huge swings
                delta = max(-base_lookahead, min(base_lookahead, delta))
                score = (float(w.get("urgency", 20.0)) / (days_left + 1)) + (float(w.get("profile", 2.0)) * delta)
            else:
                carryover_bonus = float(self.config.get("carryover_bonus", w.get("carryover", self.config.get("online_carryover_bonus", 3.0))))
                carryover_flag = 1.0 if o.get("id") in carry_prev_ids else 0.0
                buffer_flag = 1.0 if (o.get("id") in buffered_ids or o.get("id") in buffer_order_ids) else 0.0
                carry_age = float(carryover_age_map.get(str(o.get("id")), 0))
                criticality = self._service_criticality_score(
                    o,
                    current_date,
                    carry_prev_ids,
                    buffer_order_ids,
                    carryover_age_map,
                    depot,
                )
                score = (
                    (float(w.get("urgency", 20.0)) / (days_left + 1))
                    + (carryover_bonus * carryover_flag)
                    + (2.0 * buffer_flag)
                    + (0.5 * carry_age)
                    + (0.75 * criticality)
                )
            if execution_guard_level > 0.0:
                execution_cost = self._execution_shadow_cost(o, current_date, depot, effective_cap)
                score -= execution_guard_level * (0.75 + stop_pressure) * execution_cost
            flex_items.append({"score": score, "colli": float(o["demand"]["colli"]), "order": o})

        flex_items.sort(key=lambda x: x["score"], reverse=True)

        selected_flex, flex_load = [], 0.0
        for it in flex_items:
            if flex_load + it["colli"] <= quota_flex:
                selected_flex.append(it["order"])
                flex_load += it["colli"]

        final = kept_hard + selected_flex

        # -------------------------
        # Deadline Guardrail: FORCE include mandatory orders (<= 1 day to deadline)
        # even if this exceeds quota/buffer_ratio/phys_cap (VRP may drop).
        # -------------------------
        final_ids = set(o["id"] for o in final)
        forced_added = 0
        for o in mandatory_orders:
            oid = o["id"]
            if oid not in final_ids:
                final.append(o)
                final_ids.add(oid)
                forced_added += 1

        # mode tag
        mode_status = "PRECRUNCH_SMOOTH" if is_precrunch else "SMOOTH"

        self.last_debug_info.update({
            "mode_status": mode_status,
            "quota_flex": round(quota_flex, 2),
            "commitment_cap": round(commitment_cap, 2),
            "effective_capacity_colli": round(selection_cap, 2),
            "reserve_capacity_ratio": float(reserve_capacity_ratio),
            "flex_commitment_ratio": float(flex_commitment_ratio),
            "total_flex_demand": round(sum(it["colli"] for it in flex_items), 2),
            "selected_flex_demand": round(flex_load, 2),
            "is_quota_binding": sum(it["colli"] for it in flex_items) > quota_flex + 1e-9,
            "hard_overflow": round(hard_overflow, 2),
            "kept_count": 0,
            "frozen_count": 0,
            "mandatory_count": int(len(mandatory_ids)),
            "control_action_name": getattr(control_action, "name", ""),
            "execution_guard_level": float(execution_guard_level),
            "execution_penalty_spread": float(execution_penalty_spread),
            "execution_hard_sort_enabled": bool(execution_hard_sort_enabled),
            "hard_stop_reservation_enabled": bool(hard_stop_reservation_enabled),
            "hard_stop_reservation_ratio": float(hard_stop_reservation_ratio),
            "hard_capacity_reservation_ratio": float(hard_capacity_reservation_ratio),
        })

        self.last_trace = {
            "mode": mode_status.lower(),
            "control_action_name": getattr(control_action, "name", ""),
            "event_mode": event_mode,
            "is_precrunch": bool(is_precrunch),
            "is_crisis": bool(is_crisis),
            "future_pressure": future_pressure_debug,
            "pressure_k_star": k_star_debug,
            "target_load": target_load,
            "quota": quota,
            "commitment_cap": commitment_cap,
            "effective_capacity_colli": selection_cap,
            "hard_load": hard_load,
            "pseudo_cut_days": pseudo_cut,
            "hard_ids": [o["id"] for o in kept_hard],
            "selected_ids": [o["id"] for o in final],
            "buffered_ids": sorted(list((buffered_ids | buffer_order_ids) - final_ids)),
            "deferred_ids": sorted(list(deferred_ids - final_ids)),
            "mandatory_ids": sorted(list(mandatory_ids)),
            "mandatory_forced_added": int(forced_added),
            "execution_guard_level": float(execution_guard_level),
            "execution_penalty_spread": float(execution_penalty_spread),
            "execution_hard_sort_enabled": bool(execution_hard_sort_enabled),
            "hard_stop_reservation_enabled": bool(hard_stop_reservation_enabled),
            "hard_stop_reservation_ratio": float(hard_stop_reservation_ratio),
            "hard_capacity_reservation_ratio": float(hard_capacity_reservation_ratio),
        }

        # Treat kept_hard + mandatory as hard penalties
        hard_for_penalty = kept_hard + [o for o in mandatory_orders if o["id"] in final_ids]
        return self._wrap_result(final, hard_for_penalty, current_date, analyzer)


# =========================================================
# Stability (kept for compatibility; currently minimal)
# =========================================================
class StabilityPolicy(ProactivePolicy):
    """
    Placeholder stability policy (inherits Proactive behavior).
    If you re-enable Weak/Strong later, we can re-add freeze/keep logic on top of the fixed precrunch + pseudo-hard core.
    """
    pass
