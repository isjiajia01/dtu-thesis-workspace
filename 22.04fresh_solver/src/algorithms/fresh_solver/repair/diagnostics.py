from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from ..core.config import RepairConfig
from ..core.models import DepotBucketUsage, DepotDiagnostics, RoutingSolution


def evaluate_depot_profile(solution: RoutingSolution, config: RepairConfig) -> DepotDiagnostics:
    bucket_usage: Dict[str, List[DepotBucketUsage]] = defaultdict(list)
    overload_bucket_count = 0
    depot_penalty = 0.0
    worst_bucket_penalty = 0.0

    for route in solution.routes:
        if route.departure_time is None:
            continue
        bucket_start = route.departure_time.replace(
            minute=(route.departure_time.minute // config.bucket_minutes) * config.bucket_minutes,
            second=0,
            microsecond=0,
        )
        usage = DepotBucketUsage(bucket_start=bucket_start, departures=1)
        bucket_usage[route.depot_id].append(usage)

    for depot_id, usages in bucket_usage.items():
        counts: Dict[datetime, int] = defaultdict(int)
        for usage in usages:
            counts[usage.bucket_start] += usage.departures
        rebuilt: List[DepotBucketUsage] = []
        for bucket_start, departures in sorted(counts.items()):
            penalty = max(0, departures - 1)
            if penalty > 0:
                overload_bucket_count += 1
                depot_penalty += penalty * config.gate_penalty_weight
                worst_bucket_penalty = max(worst_bucket_penalty, penalty * config.gate_penalty_weight)
            rebuilt.append(DepotBucketUsage(bucket_start=bucket_start, departures=departures))
        bucket_usage[depot_id] = rebuilt

    return DepotDiagnostics(
        planning_date=solution.planning_date,
        depot_penalty=depot_penalty,
        overload_bucket_count=overload_bucket_count,
        worst_bucket_penalty=worst_bucket_penalty,
        bucket_usage=dict(bucket_usage),
    )
