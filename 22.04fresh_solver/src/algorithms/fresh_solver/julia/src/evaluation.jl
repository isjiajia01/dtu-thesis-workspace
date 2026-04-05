function summarize_run(instance_name::String, runtime_seconds::Float64, repair_result::RepairResult, deferred_orders::Int)
    routes = repair_result.repaired_solution.routes
    return RunSummary(
        instance_name=instance_name,
        planning_date=repair_result.planning_date,
        assigned_orders=sum(length(route.order_ids) for route in routes),
        unassigned_orders=length(repair_result.repaired_solution.unassigned),
        deferred_orders=deferred_orders,
        route_count=length(routes),
        trip2_route_count=count(route -> route.trip_index == 2, routes),
        total_distance_km=sum(route.total_distance_km for route in routes),
        total_duration_min=sum(route.total_duration_min for route in routes),
        depot_penalty=repair_result.diagnostics.depot_penalty,
        overload_bucket_count=repair_result.diagnostics.overload_bucket_count,
        runtime_seconds=runtime_seconds,
    )
end

function as_named_tuple(score::OrderScore)
    return (
        order_id=score.order_id,
        total_score=score.total_score,
        urgency_score=score.urgency_score,
        age_score=score.age_score,
        risk_score=score.risk_score,
        commitment_score=score.commitment_score,
        tags=score.tags,
    )
end

function as_named_tuple(decision::ControllerDecision)
    return (
        planning_date=string(decision.planning_date),
        protected_order_ids=decision.protected_order_ids,
        admitted_flex_order_ids=decision.admitted_flex_order_ids,
        deferred_order_ids=decision.deferred_order_ids,
        order_scores=Dict(k => as_named_tuple(v) for (k, v) in decision.order_scores),
        metadata=decision.metadata,
    )
end

function as_named_tuple(route::Route)
    return (
        route_id=route.route_id,
        depot_id=route.depot_id,
        vehicle_type_name=route.vehicle_type_name,
        vehicle_index=route.vehicle_index,
        trip_index=route.trip_index,
        ready_min=route.ready_min,
        departure_min=route.departure_min,
        return_min=route.return_min,
        order_ids=route.order_ids,
        stops=[(
            order_id=s.order_id,
            arrival_min=s.arrival_min,
            service_start_min=s.service_start_min,
            departure_min=s.departure_min,
        ) for s in route.stops],
        total_distance_km=route.total_distance_km,
        total_duration_min=route.total_duration_min,
        total_colli=route.total_colli,
        total_volume=route.total_volume,
        total_weight=route.total_weight,
    )
end

function as_named_tuple(solution::RoutingSolution)
    return (
        planning_date=string(solution.planning_date),
        routes=[as_named_tuple(route) for route in solution.routes],
        unassigned=[(order_id=u.order_id, reason=u.reason) for u in solution.unassigned],
    )
end

function as_named_tuple(diag::DepotDiagnostics)
    return (
        planning_date=string(diag.planning_date),
        depot_penalty=diag.depot_penalty,
        overload_bucket_count=diag.overload_bucket_count,
        worst_bucket_penalty=diag.worst_bucket_penalty,
        bucket_usage=[(
            bucket_start_min=b.bucket_start_min,
            departures=b.departures,
            picking_colli=b.picking_colli,
            picking_volume=b.picking_volume,
            staging_volume=b.staging_volume,
            gate_over=b.gate_over,
            picking_colli_over=b.picking_colli_over,
            picking_volume_over=b.picking_volume_over,
            staging_over=b.staging_over,
            bucket_penalty=b.bucket_penalty,
        ) for b in diag.bucket_usage],
    )
end

function as_named_tuple(result::RepairResult)
    return (
        planning_date=string(result.planning_date),
        repaired_solution=as_named_tuple(result.repaired_solution),
        diagnostics=as_named_tuple(result.diagnostics),
    )
end

function as_named_tuple(summary::RunSummary)
    return (
        instance_name=summary.instance_name,
        planning_date=string(summary.planning_date),
        assigned_orders=summary.assigned_orders,
        unassigned_orders=summary.unassigned_orders,
        deferred_orders=summary.deferred_orders,
        route_count=summary.route_count,
        trip2_route_count=summary.trip2_route_count,
        total_distance_km=summary.total_distance_km,
        total_duration_min=summary.total_duration_min,
        depot_penalty=summary.depot_penalty,
        overload_bucket_count=summary.overload_bucket_count,
        runtime_seconds=summary.runtime_seconds,
    )
end
