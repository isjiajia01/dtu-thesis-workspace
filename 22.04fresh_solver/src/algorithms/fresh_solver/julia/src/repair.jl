function build_empty_bucket_usage_map(start_min::Int, end_min::Int, bucket_minutes::Int)
    usage = Dict{Int,NamedTuple}()
    bucket_start = (start_min ÷ bucket_minutes) * bucket_minutes
    while bucket_start <= end_min
        usage[bucket_start] = (
            departures=0,
            picking_colli=0.0,
            picking_volume=0.0,
            staging_volume=0.0,
        )
        bucket_start += bucket_minutes
    end
    return usage
end

function add_bucket_load!(usage::Dict{Int,NamedTuple}, start_min::Int, end_min::Int, bucket_minutes::Int; departures=0, picking_colli=0.0, picking_volume=0.0, staging_volume=0.0)
    end_min < start_min && return
    bucket_start = (start_min ÷ bucket_minutes) * bucket_minutes
    while bucket_start <= end_min
        current = get(usage, bucket_start, (departures=0, picking_colli=0.0, picking_volume=0.0, staging_volume=0.0))
        usage[bucket_start] = (
            departures=current.departures + departures,
            picking_colli=current.picking_colli + picking_colli,
            picking_volume=current.picking_volume + picking_volume,
            staging_volume=current.staging_volume + staging_volume,
        )
        bucket_start += bucket_minutes
    end
end

function route_picking_window(route::Route, orders_by_id::Dict{String,Order}, warehouse::Warehouse)
    total_pick_min = sum(orders_by_id[id].picking_task_time_min for id in route.order_ids)
    pick_end = route.departure_min
    pick_start = max(warehouse.picking_open_min, floor(Int, pick_end - total_pick_min))
    return pick_start, pick_end
end

function evaluate_depot_profile(solution::RoutingSolution, instance::Instance, config::RepairConfig)
    warehouse = instance.warehouse
    orders_by_id = Dict(order.id => order for order in instance.orders)
    usage = build_empty_bucket_usage_map(warehouse.picking_open_min, warehouse.closing_min, config.bucket_minutes)

    for route in solution.routes
        departure_bucket = (route.departure_min ÷ config.bucket_minutes) * config.bucket_minutes
        add_bucket_load!(usage, departure_bucket, departure_bucket, config.bucket_minutes; departures=1)

        pick_start, pick_end = route_picking_window(route, orders_by_id, warehouse)
        route_pick_colli = sum(orders_by_id[id].colli for id in route.order_ids)
        route_pick_volume = sum(orders_by_id[id].volume for id in route.order_ids)
        add_bucket_load!(usage, pick_start, max(pick_start, pick_end - 1), config.bucket_minutes;
            picking_colli=route_pick_colli,
            picking_volume=route_pick_volume,
        )

        add_bucket_load!(usage, pick_end, max(pick_end, route.departure_min - 1), config.bucket_minutes;
            staging_volume=route.total_volume,
        )
    end

    bucket_usage = DepotBucketUsage[]
    depot_penalty = 0.0
    overload_bucket_count = 0
    worst_bucket_penalty = 0.0

    for bucket_start in sort(collect(keys(usage)))
        u = usage[bucket_start]
        gate_over = max(0, u.departures - warehouse.gates)
        picking_colli_cap = warehouse.picking_capacity_colli_per_hour * (config.bucket_minutes / 60.0)
        picking_volume_cap = warehouse.picking_capacity_volume_per_hour * (config.bucket_minutes / 60.0)
        picking_colli_over = max(0.0, u.picking_colli - picking_colli_cap)
        picking_volume_over = max(0.0, u.picking_volume - picking_volume_cap)
        staging_over = max(0.0, u.staging_volume - warehouse.max_staging_volume)

        bucket_penalty = gate_over * config.gate_penalty_weight +
                         picking_colli_over * config.picking_colli_penalty_weight +
                         picking_volume_over * config.picking_volume_penalty_weight +
                         staging_over * config.staging_penalty_weight

        if bucket_penalty > 0
            overload_bucket_count += 1
            depot_penalty += bucket_penalty
            worst_bucket_penalty = max(worst_bucket_penalty, bucket_penalty)
        end

        push!(bucket_usage, DepotBucketUsage(
            bucket_start_min=bucket_start,
            departures=u.departures,
            picking_colli=u.picking_colli,
            picking_volume=u.picking_volume,
            staging_volume=u.staging_volume,
            gate_over=gate_over,
            picking_colli_over=picking_colli_over,
            picking_volume_over=picking_volume_over,
            staging_over=staging_over,
            bucket_penalty=bucket_penalty,
        ))
    end

    return DepotDiagnostics(
        planning_date=solution.planning_date,
        depot_penalty=depot_penalty,
        overload_bucket_count=overload_bucket_count,
        worst_bucket_penalty=worst_bucket_penalty,
        bucket_usage=bucket_usage,
    )
end

function shift_route(route::Route, delta_min::Int)
    return Route(
        route_id=route.route_id,
        depot_id=route.depot_id,
        vehicle_type_name=route.vehicle_type_name,
        vehicle_index=route.vehicle_index,
        trip_index=route.trip_index,
        ready_min=route.ready_min,
        departure_min=route.departure_min + delta_min,
        return_min=route.return_min + delta_min,
        order_ids=copy(route.order_ids),
        stops=[RouteStop(
            order_id=s.order_id,
            arrival_min=s.arrival_min + delta_min,
            service_start_min=s.service_start_min + delta_min,
            departure_min=s.departure_min + delta_min,
        ) for s in route.stops],
        total_distance_km=route.total_distance_km,
        total_duration_min=route.total_duration_min,
        total_colli=route.total_colli,
        total_volume=route.total_volume,
        total_weight=route.total_weight,
    )
end

function rebuild_vehicle_state_local(routes::Vector{Route}, instance::Instance)
    vehicle_ready = Dict{Tuple{String,Int},Int}()
    vehicle_trip_count = Dict{Tuple{String,Int},Int}()
    for vt in instance.vehicle_types
        for vehicle_index in 1:vt.count
            key = (vt.type_name, vehicle_index)
            vehicle_ready[key] = instance.warehouse.opening_min
            vehicle_trip_count[key] = 0
        end
    end
    for route in sort(routes, by=r -> (r.vehicle_type_name, r.vehicle_index, r.trip_index))
        key = (route.vehicle_type_name, route.vehicle_index)
        vehicle_trip_count[key] = max(vehicle_trip_count[key], route.trip_index)
        vehicle_ready[key] = max(vehicle_ready[key], route.return_min + instance.warehouse.unloading_time_min + instance.warehouse.loading_time_min)
    end
    return vehicle_ready, vehicle_trip_count
end

function candidate_route_indices_for_bucket(routes::Vector{Route}, bucket_start_min::Int, bucket_minutes::Int)
    return [idx for idx in eachindex(routes) if ((routes[idx].departure_min ÷ bucket_minutes) * bucket_minutes) == bucket_start_min]
end

function deferrable_order(order::Order, planning_date)
    return order.service_date_to > planning_date
end

function route_contribution_score(route::Route, orders_by_id::Dict{String,Order})
    return route.total_volume + 0.01 * route.total_weight + sum(orders_by_id[id].picking_task_time_min for id in route.order_ids)
end

function try_fragment_reassign(order_ids::Vector{String}, target_route::Route, orders_by_id::Dict{String,Order}, instance::Instance, vehicle_types_by_name::Dict{String,VehicleType})
    vehicle = vehicle_types_by_name[target_route.vehicle_type_name]
    candidate = target_route
    for order_id in order_ids
        next_candidate, _, _ = try_insert_order(candidate, order_id, orders_by_id, Dict{String,OrderScore}(), Set{String}(), "normal", 0.0, "balanced", 0.0, 0.0, 0.0, 1.0, Dict{Int,Float64}(), Dict{Int,Float64}(), Dict{Int,Float64}(), instance, vehicle, RoutingConfig())
        isnothing(next_candidate) && return nothing
        candidate = next_candidate
    end
    return candidate
end

function try_overload_reassignment!(solution::RoutingSolution, instance::Instance, diagnostics::DepotDiagnostics, config::RepairConfig)
    orders_by_id = Dict(order.id => order for order in instance.orders)
    vehicle_types_by_name = Dict(v.type_name => v for v in instance.vehicle_types)
    attempts = 0

    overloaded = sort(filter(b -> b.bucket_penalty > 0, diagnostics.bucket_usage), by=b -> b.bucket_penalty, rev=true)
    for bucket in overloaded[1:min(end, 5)]
        route_indices = candidate_route_indices_for_bucket(solution.routes, bucket.bucket_start_min, config.bucket_minutes)
        sort!(route_indices, by=i -> route_contribution_score(solution.routes[i], orders_by_id), rev=true)
        for route_idx in route_indices
            attempts >= config.reassignment_budget && return solution, diagnostics, false
            route = solution.routes[route_idx]
            vehicle = vehicle_types_by_name[route.vehicle_type_name]
            candidate_positions = unique([length(route.order_ids), max(1, length(route.order_ids)-1), argmax([orders_by_id[id].volume + 0.003 * orders_by_id[id].weight for id in route.order_ids])])
            fragment_candidates = Vector{Vector{String}}()
            for pos in candidate_positions
                pos > length(route.order_ids) && continue
                push!(fragment_candidates, [route.order_ids[pos]])
                if pos < length(route.order_ids)
                    push!(fragment_candidates, route.order_ids[pos:min(end, pos+1)])
                end
            end
            for fragment in fragment_candidates
                reduced_ids = copy(route.order_ids)
                for frag_id in fragment
                    frag_pos = findfirst(==(frag_id), reduced_ids)
                    !isnothing(frag_pos) && deleteat!(reduced_ids, frag_pos)
                end
                ok, dep, ret, stops, dist, dur, colli, vol, weight, _ = compute_route_schedule(reduced_ids, orders_by_id, instance, vehicle, route.ready_min, RoutingConfig())
                ok || continue
                reduced_route = Route(
                    route_id=route.route_id,
                    depot_id=route.depot_id,
                    vehicle_type_name=route.vehicle_type_name,
                    vehicle_index=route.vehicle_index,
                    trip_index=route.trip_index,
                    ready_min=route.ready_min,
                    departure_min=dep,
                    return_min=ret,
                    order_ids=copy(reduced_ids),
                    stops=stops,
                    total_distance_km=dist,
                    total_duration_min=dur,
                    total_colli=colli,
                    total_volume=vol,
                    total_weight=weight,
                )
                temp_routes = copy(solution.routes)
                temp_routes[route_idx] = reduced_route
                for target_idx in eachindex(temp_routes)
                    target_idx == route_idx && continue
                    candidate_target = try_fragment_reassign(fragment, temp_routes[target_idx], orders_by_id, instance, vehicle_types_by_name)
                    attempts += 1
                    isnothing(candidate_target) && continue
                    trial_routes = copy(temp_routes)
                    trial_routes[target_idx] = candidate_target
                    trial_solution = RoutingSolution(planning_date=solution.planning_date, routes=trial_routes, unassigned=solution.unassigned)
                    trial_diag = evaluate_depot_profile(trial_solution, instance, config)
                    if trial_diag.depot_penalty < diagnostics.depot_penalty
                        return trial_solution, trial_diag, true
                    end
                end
            end
        end
    end
    return solution, diagnostics, false
end

function try_overload_rollback!(solution::RoutingSolution, instance::Instance, diagnostics::DepotDiagnostics, config::RepairConfig)
    orders_by_id = Dict(order.id => order for order in instance.orders)
    vehicle_types_by_name = Dict(v.type_name => v for v in instance.vehicle_types)
    rollbacks = 0
    overloaded = sort(filter(b -> b.bucket_penalty > 0, diagnostics.bucket_usage), by=b -> b.bucket_penalty, rev=true)

    for bucket in overloaded[1:min(end, 5)]
        route_indices = candidate_route_indices_for_bucket(solution.routes, bucket.bucket_start_min, config.bucket_minutes)
        sort!(route_indices, by=i -> route_contribution_score(solution.routes[i], orders_by_id), rev=true)
        for route_idx in route_indices
            rollbacks >= config.rollback_budget && return solution, diagnostics, false
            route = solution.routes[route_idx]
            vehicle = vehicle_types_by_name[route.vehicle_type_name]
            candidate_ids = [id for id in reverse(route.order_ids) if deferrable_order(orders_by_id[id], solution.planning_date)]
            isempty(candidate_ids) && continue
            for order_id in candidate_ids
                pos = findfirst(==(order_id), route.order_ids)
                isnothing(pos) && continue
                reduced_ids = copy(route.order_ids)
                deleteat!(reduced_ids, pos)
                ok, dep, ret, stops, dist, dur, colli, vol, weight, _ = compute_route_schedule(reduced_ids, orders_by_id, instance, vehicle, route.ready_min, RoutingConfig())
                ok || continue
                reduced_route = Route(
                    route_id=route.route_id,
                    depot_id=route.depot_id,
                    vehicle_type_name=route.vehicle_type_name,
                    vehicle_index=route.vehicle_index,
                    trip_index=route.trip_index,
                    ready_min=route.ready_min,
                    departure_min=dep,
                    return_min=ret,
                    order_ids=copy(reduced_ids),
                    stops=stops,
                    total_distance_km=dist,
                    total_duration_min=dur,
                    total_colli=colli,
                    total_volume=vol,
                    total_weight=weight,
                )
                trial_routes = copy(solution.routes)
                trial_routes[route_idx] = reduced_route
                if isempty(reduced_route.order_ids)
                    deleteat!(trial_routes, route_idx)
                end
                trial_unassigned = copy(solution.unassigned)
                push!(trial_unassigned, UnassignedOrder(order_id=order_id, reason="repair_rollback"))
                trial_solution = RoutingSolution(planning_date=solution.planning_date, routes=trial_routes, unassigned=trial_unassigned)
                trial_diag = evaluate_depot_profile(trial_solution, instance, config)
                rollbacks += 1
                if trial_diag.depot_penalty < diagnostics.depot_penalty
                    return trial_solution, trial_diag, true
                end
            end
        end
    end
    return solution, diagnostics, false
end

function repair_solution(solution::RoutingSolution, instance::Instance, config::RepairConfig)
    diagnostics = evaluate_depot_profile(solution, instance, config)
    if diagnostics.overload_bucket_count > 0
        overloaded = sort(filter(b -> b.bucket_penalty > 0, diagnostics.bucket_usage), by=b -> b.bucket_penalty, rev=true)
        for bucket in overloaded[1:min(end, 5)]
            for idx in eachindex(solution.routes)
                route = solution.routes[idx]
                route_bucket = (route.departure_min ÷ config.bucket_minutes) * config.bucket_minutes
                route_bucket != bucket.bucket_start_min && continue
                for delta in (-config.bucket_minutes, config.bucket_minutes)
                    shifted = shift_route(route, delta)
                    shifted.departure_min < instance.warehouse.opening_min && continue
                    shifted.departure_min > instance.warehouse.closing_min && continue
                    trial_routes = copy(solution.routes)
                    trial_routes[idx] = shifted
                    trial_solution = RoutingSolution(planning_date=solution.planning_date, routes=trial_routes, unassigned=solution.unassigned)
                    trial_diag = evaluate_depot_profile(trial_solution, instance, config)
                    if trial_diag.depot_penalty < diagnostics.depot_penalty
                        solution = trial_solution
                        diagnostics = trial_diag
                        break
                    end
                end
            end
        end

        solution, diagnostics, changed = try_overload_reassignment!(solution, instance, diagnostics, config)
        if !changed
            solution, diagnostics, _ = try_overload_rollback!(solution, instance, diagnostics, config)
        end
    end
    return RepairResult(planning_date=solution.planning_date, repaired_solution=solution, diagnostics=diagnostics)
end
