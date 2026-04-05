using Dates

function compute_route_schedule(order_ids::Vector{String}, orders_by_id::Dict{String,Order}, instance::Instance, vehicle::VehicleType, ready_min::Int, config::RoutingConfig)
    warehouse = instance.warehouse
    matrix_ref = instance.matrix_ref
    isempty(order_ids) && return (true, ready_min, ready_min, RouteStop[], 0.0, 0.0, 0.0, 0.0, 0.0, "empty_route")

    total_colli = 0.0
    total_volume = 0.0
    total_weight = 0.0
    for order_id in order_ids
        order = orders_by_id[order_id]
        order.node_id < 0 && return (false, 0, 0, RouteStop[], 0.0, 0.0, 0.0, 0.0, 0.0, "missing_matrix_node")
        total_colli += order.colli
        total_volume += order.volume
        total_weight += order.weight
    end
    total_colli > vehicle.capacity_colli && return (false, 0, 0, RouteStop[], 0.0, 0.0, total_colli, total_volume, total_weight, "capacity_colli")
    total_volume > vehicle.capacity_volume && return (false, 0, 0, RouteStop[], 0.0, 0.0, total_colli, total_volume, total_weight, "capacity_volume")
    total_weight > vehicle.capacity_weight && return (false, 0, 0, RouteStop[], 0.0, 0.0, total_colli, total_volume, total_weight, "capacity_weight")
    length(order_ids) > config.max_orders_per_route && return (false, 0, 0, RouteStop[], 0.0, 0.0, total_colli, total_volume, total_weight, "max_orders_per_route")

    first_order = orders_by_id[first(order_ids)]
    depot_to_first_min = matrix_duration_min(matrix_ref, warehouse.node_id, first_order.node_id)
    earliest_departure = max(ready_min, warehouse.opening_min)
    latest_departure = warehouse.closing_min
    departure_min = max(earliest_departure, floor(Int, first_order.time_window_start_min - depot_to_first_min))
    departure_min > latest_departure && return (false, 0, 0, RouteStop[], 0.0, 0.0, total_colli, total_volume, total_weight, "depot_departure_window")

    current_time = departure_min
    current_node = warehouse.node_id
    total_distance_km = 0.0
    stops = RouteStop[]

    for order_id in order_ids
        order = orders_by_id[order_id]
        leg_min = matrix_duration_min(matrix_ref, current_node, order.node_id)
        leg_km = matrix_distance_km(matrix_ref, current_node, order.node_id)
        arrival_min = ceil(Int, current_time + leg_min)
        service_start_min = max(arrival_min, order.time_window_start_min)
        service_start_min > order.time_window_end_min && return (false, 0, 0, RouteStop[], 0.0, 0.0, total_colli, total_volume, total_weight, "time_window")

        departure_after_service = ceil(Int, service_start_min + order.service_time_min + config.depot_service_buffer_min)
        push!(stops, RouteStop(
            order_id=order_id,
            arrival_min=arrival_min,
            service_start_min=service_start_min,
            departure_min=departure_after_service,
        ))
        total_distance_km += leg_km
        current_time = departure_after_service
        current_node = order.node_id
    end

    return_min = ceil(Int, current_time + matrix_duration_min(matrix_ref, current_node, warehouse.node_id))
    total_distance_km += matrix_distance_km(matrix_ref, current_node, warehouse.node_id)
    total_duration_min = return_min - departure_min

    total_duration_min > vehicle.max_duration_min && return (false, 0, 0, RouteStop[], total_distance_km, total_duration_min, total_colli, total_volume, total_weight, "route_duration")
    total_distance_km > vehicle.max_distance_km && return (false, 0, 0, RouteStop[], total_distance_km, total_duration_min, total_colli, total_volume, total_weight, "route_distance")

    return (true, departure_min, return_min, stops, total_distance_km, total_duration_min, total_colli, total_volume, total_weight, "ok")
end

function route_penalty(route::Route, vehicle::VehicleType, config::RoutingConfig)
    trip_penalty = route.trip_index == 2 ? config.trip2_penalty : 0.0
    capacity_slack = (route.total_colli / max(vehicle.capacity_colli, 1.0)) + (route.total_volume / max(vehicle.capacity_volume, 1.0))
    return route.total_distance_km + trip_penalty + config.depot_proxy_penalty * capacity_slack
end

function order_vehicle_bias(order::Order, vehicle::VehicleType, config::RoutingConfig)
    heavy = order.volume >= config.truck_seed_volume_threshold || order.weight >= config.truck_seed_weight_threshold
    if vehicle.type_name == "Truck"
        return heavy ? -config.truck_bonus_heavy : 0.75
    else
        return heavy ? 1.5 : -config.lift_bonus_light
    end
end

function route_vehicle_bias(route::Route, vehicle::VehicleType, orders_by_id::Dict{String,Order}, config::RoutingConfig)
    isempty(route.order_ids) && return 0.0
    heavy_count = 0
    for order_id in route.order_ids
        order = orders_by_id[order_id]
        if order.volume >= config.truck_seed_volume_threshold || order.weight >= config.truck_seed_weight_threshold
            heavy_count += 1
        end
    end
    if vehicle.type_name == "Truck"
        return heavy_count >= max(1, ceil(Int, length(route.order_ids) / 3)) ? -config.truck_bonus_heavy / 2 : 0.75
    else
        return heavy_count == 0 ? -config.lift_bonus_light / 2 : 0.75 * heavy_count
    end
end

function insertion_priority(order::Order, score::OrderScore)
    tw_width = order.time_window_end_min - order.time_window_start_min
    return (
        -("near_deadline" in score.tags ? 1 : 0),
        -("tight_window" in score.tags ? 1 : 0),
        -score.total_score,
        tw_width,
        -order.volume,
    )
end

function route_pick_window_stats(route::Route, orders_by_id::Dict{String,Order}, instance::Instance)
    bucket_minutes = 15
    total_pick_min = sum(orders_by_id[id].picking_task_time_min for id in route.order_ids)
    pick_start = max(instance.warehouse.picking_open_min, floor(Int, route.departure_min - total_pick_min))
    pick_end = route.departure_min
    pick_bucket_count = max(1, ceil(Int, max(pick_end - pick_start, 1) / bucket_minutes))
    return (pick_start=pick_start, pick_end=pick_end, pick_bucket_count=pick_bucket_count)
end

function route_resource_usage_proxy(order::Order, candidate::Route, orders_by_id::Dict{String,Order}, instance::Instance, config::RoutingConfig)
    bucket_minutes = 15
    departure_bucket = (candidate.departure_min ÷ bucket_minutes) * bucket_minutes
    late_departure = candidate.departure_min >= config.late_bucket_start_min

    pick_stats = route_pick_window_stats(candidate, orders_by_id, instance)
    picking_bucket_load = (candidate.total_colli + 0.5 * candidate.total_volume) / max(pick_stats.pick_bucket_count, 1)

    staging_duration_buckets = max(1, ceil(Int, max(candidate.departure_min - pick_stats.pick_start, 1) / bucket_minutes))
    staging_bucket_load = candidate.total_volume * min(2.0, staging_duration_buckets / 2.0)

    gate_usage = 1.0 + (candidate.trip_index >= 2 ? 0.5 : 0.0) + (late_departure ? 0.25 : 0.0)
    picking_buckets = collect((pick_stats.pick_start ÷ bucket_minutes) * bucket_minutes:bucket_minutes:((max(pick_stats.pick_start, pick_stats.pick_end - 1)) ÷ bucket_minutes) * bucket_minutes)
    staging_buckets = collect((pick_stats.pick_end ÷ bucket_minutes) * bucket_minutes:bucket_minutes:((max(pick_stats.pick_end, candidate.departure_min - 1)) ÷ bucket_minutes) * bucket_minutes)
    return (
        departure_bucket=departure_bucket,
        gate_usage=gate_usage,
        picking_bucket_load=picking_bucket_load,
        staging_bucket_load=staging_bucket_load,
        picking_buckets=picking_buckets,
        staging_buckets=staging_buckets,
    )
end

function dynamic_bucket_shadow_cost(usage, dynamic_lambda_gate::Dict{Int,Float64}, dynamic_lambda_picking::Dict{Int,Float64}, dynamic_lambda_staging::Dict{Int,Float64}, config::RoutingConfig)
    gate_cost = get(dynamic_lambda_gate, usage.departure_bucket, 0.0) * usage.gate_usage
    picking_cost = sum(get(dynamic_lambda_picking, bucket, 0.0) for bucket in usage.picking_buckets) * usage.picking_bucket_load
    staging_cost = sum(get(dynamic_lambda_staging, bucket, 0.0) for bucket in usage.staging_buckets) * usage.staging_bucket_load
    return config.shadow_price_weight * (gate_cost + picking_cost + staging_cost)
end

function insertion_bucket_bias(order::Order, candidate::Route, orders_by_id::Dict{String,Order}, score_map::Dict{String,OrderScore}, targeted_bias_ids::Set{String}, controller_bucket_signal::String, controller_bucket_pressure_score::Float64, pressure_mode::String, lambda_gate::Float64, lambda_picking::Float64, lambda_staging::Float64, lambda_scale::Float64, dynamic_lambda_gate::Dict{Int,Float64}, dynamic_lambda_picking::Dict{Int,Float64}, dynamic_lambda_staging::Dict{Int,Float64}, instance::Instance, config::RoutingConfig)
    config.bucket_aware_insertion_bias || return 0.0
    late_departure = candidate.departure_min >= config.late_bucket_start_min
    score = get(score_map, order.id, OrderScore(order_id=order.id, total_score=0.0, urgency_score=0.0, age_score=0.0, risk_score=0.0, commitment_score=0.0, tags=String[]))
    tags = Set(score.tags)
    is_protected = ("near_deadline" in tags) || ("hard_protected" in tags)
    is_risky = "risky_flex" in tags
    is_heavy = order.volume >= config.truck_seed_volume_threshold || order.weight >= config.truck_seed_weight_threshold

    bias = 0.0
    if config.targeted_insertion_bias
        target_active = isempty(targeted_bias_ids) ? is_risky : (order.id in targeted_bias_ids)
        if late_departure && candidate.trip_index >= 2 && target_active
            bias += config.trip2_late_bias_weight
        end
        heavy_weight = 0.5 * config.heavy_late_bias_weight
        staging_weight = 0.5 * config.staging_risk_bias_weight
        trip2_weight = config.trip2_late_bias_weight
        if config.pressure_mode_pattern_feedback
            if pressure_mode == "gate"
                trip2_weight *= 1.35
                heavy_weight *= 0.75
                staging_weight *= 0.75
            elseif pressure_mode == "staging"
                staging_weight *= 1.5
                heavy_weight *= 1.1
            elseif pressure_mode == "picking"
                heavy_weight *= 1.4
                staging_weight *= 0.8
            end
        end
        if late_departure && candidate.trip_index >= 2 && target_active
            bias += trip2_weight
        end
        if late_departure && target_active && is_heavy
            bias += heavy_weight
        end
        if late_departure && target_active && candidate.total_volume >= 1.8
            bias += staging_weight * min(1.2, candidate.total_volume / 2.2)
        end
        if config.controller_bucket_feedback_bias && target_active
            if config.controller_bucket_feedback_fine_grained
                bias += config.controller_bucket_feedback_weight * controller_bucket_pressure_score
            else
                if controller_bucket_signal == "severe"
                    bias += config.controller_bucket_feedback_weight
                elseif controller_bucket_signal == "elevated"
                    bias += 0.5 * config.controller_bucket_feedback_weight
                end
            end
        end
        if is_protected
            bias -= config.protect_near_deadline_bias_relief
        end
    else
        if candidate.trip_index >= 2 && late_departure
            bias += config.trip2_late_bias_weight
        end
        if late_departure && is_heavy
            bias += config.heavy_late_bias_weight
        end
        if late_departure && candidate.total_volume >= 1.6
            bias += config.staging_risk_bias_weight * min(1.5, candidate.total_volume / 2.0)
        end
    end
    if config.shadow_price_feedback
        usage = route_resource_usage_proxy(order, candidate, orders_by_id, instance, config)
        scale = config.normalized_shadow_price ? lambda_scale : 1.0
        if config.regime_aware_normalization
            if pressure_mode == "staging"
                scale *= 0.85
            elseif pressure_mode == "picking"
                scale *= 0.90
            elseif pressure_mode == "gate"
                scale *= 0.95
            end
        end
        shadow_cost = config.shadow_price_weight * scale * (
            lambda_gate * usage.gate_usage +
            lambda_picking * usage.picking_bucket_load +
            lambda_staging * usage.staging_bucket_load
        )
        if config.service_shield_feedback
            shield = 0.0
            if config.structured_service_shield
                if is_protected
                    shield += 1.2 * config.service_shield_relief_weight
                elseif score.total_score >= 3.5
                    shield += 0.8 * config.service_shield_relief_weight
                elseif score.total_score >= 2.5
                    shield += 0.5 * config.service_shield_relief_weight
                end
                if !("risky_flex" in tags)
                    shield += 0.3 * config.service_shield_relief_weight
                end
            else
                if is_protected
                    shield += config.service_shield_relief_weight
                elseif score.total_score >= 2.5
                    shield += 0.5 * config.service_shield_relief_weight
                end
            end
            shadow_cost = max(0.0, shadow_cost - shield)
        end
        bias += shadow_cost
        if config.dynamic_shadow_price_v8
            bias += scale * dynamic_bucket_shadow_cost(usage, dynamic_lambda_gate, dynamic_lambda_picking, dynamic_lambda_staging, config)
        end
    end
    return bias
end

function try_insert_order(route::Route, order_id::String, orders_by_id::Dict{String,Order}, score_map::Dict{String,OrderScore}, targeted_bias_ids::Set{String}, controller_bucket_signal::String, controller_bucket_pressure_score::Float64, pressure_mode::String, lambda_gate::Float64, lambda_picking::Float64, lambda_staging::Float64, lambda_scale::Float64, dynamic_lambda_gate::Dict{Int,Float64}, dynamic_lambda_picking::Dict{Int,Float64}, dynamic_lambda_staging::Dict{Int,Float64}, instance::Instance, vehicle::VehicleType, config::RoutingConfig)
    best_candidate = nothing
    best_penalty = Inf
    best_reason = "no_feasible_insertion"
    order = orders_by_id[order_id]

    for pos in 1:(length(route.order_ids) + 1)
        candidate_order_ids = copy(route.order_ids)
        insert!(candidate_order_ids, pos, order_id)
        ok, departure_min, return_min, stops, total_distance_km, total_duration_min, total_colli, total_volume, total_weight, reason = compute_route_schedule(
            candidate_order_ids,
            orders_by_id,
            instance,
            vehicle,
            route.ready_min,
            config,
        )
        if ok
            candidate = Route(
                route_id=route.route_id,
                depot_id=route.depot_id,
                vehicle_type_name=route.vehicle_type_name,
                vehicle_index=route.vehicle_index,
                trip_index=route.trip_index,
                ready_min=route.ready_min,
                departure_min=departure_min,
                return_min=return_min,
                order_ids=candidate_order_ids,
                stops=stops,
                total_distance_km=total_distance_km,
                total_duration_min=total_duration_min,
                total_colli=total_colli,
                total_volume=total_volume,
                total_weight=total_weight,
            )
            penalty = route_penalty(candidate, vehicle, config) + insertion_bucket_bias(order, candidate, orders_by_id, score_map, targeted_bias_ids, controller_bucket_signal, controller_bucket_pressure_score, pressure_mode, lambda_gate, lambda_picking, lambda_staging, lambda_scale, dynamic_lambda_gate, dynamic_lambda_picking, dynamic_lambda_staging, instance, config)
            if penalty < best_penalty
                best_penalty = penalty
                best_candidate = candidate
            end
        else
            best_reason = reason
        end
    end

    return best_candidate, best_reason, best_penalty
end

function evaluate_order_choices(order_id::String, routes::Vector{Route}, orders_by_id::Dict{String,Order}, score_map::Dict{String,OrderScore}, targeted_bias_ids::Set{String}, controller_bucket_signal::String, controller_bucket_pressure_score::Float64, pressure_mode::String, lambda_gate::Float64, lambda_picking::Float64, lambda_staging::Float64, lambda_scale::Float64, dynamic_lambda_gate::Dict{Int,Float64}, dynamic_lambda_picking::Dict{Int,Float64}, dynamic_lambda_staging::Dict{Int,Float64}, instance::Instance, vehicle_types_by_name::Dict{String,VehicleType}, vehicle_ready::Dict{Tuple{String,Int},Int}, vehicle_trip_count::Dict{Tuple{String,Int},Int}, config::RoutingConfig; allow_new_route::Bool=true)
    choices = NamedTuple[]
    failure_reasons = String[]

    for route_idx in eachindex(routes)
        route = routes[route_idx]
        key = (route.vehicle_type_name, route.vehicle_index)
        route.trip_index != vehicle_trip_count[key] && continue
        vehicle = vehicle_types_by_name[route.vehicle_type_name]
        candidate, reason, penalty = try_insert_order(route, order_id, orders_by_id, score_map, targeted_bias_ids, controller_bucket_signal, controller_bucket_pressure_score, pressure_mode, lambda_gate, lambda_picking, lambda_staging, lambda_scale, dynamic_lambda_gate, dynamic_lambda_picking, dynamic_lambda_staging, instance, vehicle, config)
        if !isnothing(candidate)
            push!(choices, (kind=:append, target=route_idx, candidate=candidate, penalty=penalty))
        else
            push!(failure_reasons, reason)
        end
    end

    if allow_new_route
        for vehicle in instance.vehicle_types
            for vehicle_index in 1:vehicle.count
                key = (vehicle.type_name, vehicle_index)
                trip_index = vehicle_trip_count[key] + 1
                trip_index > vehicle.max_trips_per_day && continue
                ready_min = vehicle_ready[key]
                ok, departure_min, return_min, stops, total_distance_km, total_duration_min, total_colli, total_volume, total_weight, reason = compute_route_schedule(
                    [order_id],
                    orders_by_id,
                    instance,
                    vehicle,
                    ready_min,
                    config,
                )
                if ok
                    route_id = "$(Dates.format(instance.start_date, "yyyymmdd"))_$(vehicle.type_name)_v$(vehicle_index)_t$(trip_index)"
                    candidate = Route(
                        route_id=route_id,
                        depot_id=instance.depot_id,
                        vehicle_type_name=vehicle.type_name,
                        vehicle_index=vehicle_index,
                        trip_index=trip_index,
                        ready_min=ready_min,
                        departure_min=departure_min,
                        return_min=return_min,
                        order_ids=[order_id],
                        stops=stops,
                        total_distance_km=total_distance_km,
                        total_duration_min=total_duration_min,
                        total_colli=total_colli,
                        total_volume=total_volume,
                        total_weight=total_weight,
                    )
                    order = orders_by_id[order_id]
                    penalty = route_penalty(candidate, vehicle, config) + order_vehicle_bias(order, vehicle, config) + insertion_bucket_bias(order, candidate, orders_by_id, score_map, targeted_bias_ids, controller_bucket_signal, controller_bucket_pressure_score, pressure_mode, lambda_gate, lambda_picking, lambda_staging, lambda_scale, dynamic_lambda_gate, dynamic_lambda_picking, dynamic_lambda_staging, instance, config)
                    push!(choices, (kind=:new_route, target=key, candidate=candidate, penalty=penalty))
                else
                    push!(failure_reasons, reason)
                end
            end
        end
    end

    sort!(choices, by=c -> c.penalty)
    return choices, failure_reasons
end

function apply_choice!(choice, routes::Vector{Route}, vehicle_ready::Dict{Tuple{String,Int},Int}, vehicle_trip_count::Dict{Tuple{String,Int},Int}, instance::Instance)
    candidate = choice.candidate
    if choice.kind == :append
        routes[choice.target] = candidate
        key = (candidate.vehicle_type_name, candidate.vehicle_index)
        vehicle_ready[key] = candidate.return_min + instance.warehouse.unloading_time_min + instance.warehouse.loading_time_min
    else
        key = choice.target
        push!(routes, candidate)
        vehicle_trip_count[key] += 1
        vehicle_ready[key] = candidate.return_min + instance.warehouse.unloading_time_min + instance.warehouse.loading_time_min
    end
end

function choose_order_by_regret(candidate_order_ids::Vector{String}, routes::Vector{Route}, orders_by_id::Dict{String,Order}, scores::Dict{String,OrderScore}, targeted_bias_ids::Set{String}, controller_bucket_signal::String, controller_bucket_pressure_score::Float64, pressure_mode::String, lambda_gate::Float64, lambda_picking::Float64, lambda_staging::Float64, lambda_scale::Float64, dynamic_lambda_gate::Dict{Int,Float64}, dynamic_lambda_picking::Dict{Int,Float64}, dynamic_lambda_staging::Dict{Int,Float64}, instance::Instance, vehicle_types_by_name::Dict{String,VehicleType}, vehicle_ready::Dict{Tuple{String,Int},Int}, vehicle_trip_count::Dict{Tuple{String,Int},Int}, config::RoutingConfig; allow_new_route::Bool=true)
    best_order_id = nothing
    best_choice = nothing
    best_regret = -Inf
    best_first_penalty = Inf
    best_failure_reasons = String[]
    k = max(config.regret_k, 2)

    for order_id in candidate_order_ids
        choices, failure_reasons = evaluate_order_choices(order_id, routes, orders_by_id, scores, targeted_bias_ids, controller_bucket_signal, controller_bucket_pressure_score, pressure_mode, lambda_gate, lambda_picking, lambda_staging, lambda_scale, dynamic_lambda_gate, dynamic_lambda_picking, dynamic_lambda_staging, instance, vehicle_types_by_name, vehicle_ready, vehicle_trip_count, config; allow_new_route=allow_new_route)
        if isempty(choices)
            if isnothing(best_order_id)
                best_order_id = order_id
                best_failure_reasons = failure_reasons
            end
            continue
        end

        first_penalty = choices[1].penalty
        compare_penalty = length(choices) >= k ? choices[k].penalty : first_penalty + 1000.0
        regret = compare_penalty - first_penalty
        score = get(scores, order_id, OrderScore(order_id=order_id, total_score=0.0, urgency_score=0.0, age_score=0.0, risk_score=0.0, commitment_score=0.0, tags=String[]))
        regret += 0.01 * score.total_score

        if regret > best_regret || (regret == best_regret && first_penalty < best_first_penalty)
            best_regret = regret
            best_first_penalty = first_penalty
            best_order_id = order_id
            best_choice = choices[1]
            best_failure_reasons = failure_reasons
        end
    end

    return best_order_id, best_choice, best_failure_reasons
end

function try_relocate_move(routes::Vector{Route}, orders_by_id::Dict{String,Order}, instance::Instance, vehicle_types_by_name::Dict{String,VehicleType}, config::RoutingConfig)
    best_move = nothing
    best_delta = 0.0

    for from_idx in eachindex(routes)
        from_route = routes[from_idx]
        from_vehicle = vehicle_types_by_name[from_route.vehicle_type_name]
        base_from_penalty = route_penalty(from_route, from_vehicle, config)
        for pos in eachindex(from_route.order_ids)
            order_id = from_route.order_ids[pos]
            reduced_order_ids = copy(from_route.order_ids)
            deleteat!(reduced_order_ids, pos)
            ok_from, dep_from, ret_from, stops_from, dist_from, dur_from, colli_from, vol_from, weight_from, _ = compute_route_schedule(
                reduced_order_ids,
                orders_by_id,
                instance,
                from_vehicle,
                from_route.ready_min,
                config,
            )
            ok_from || continue
            new_from = Route(
                route_id=from_route.route_id,
                depot_id=from_route.depot_id,
                vehicle_type_name=from_route.vehicle_type_name,
                vehicle_index=from_route.vehicle_index,
                trip_index=from_route.trip_index,
                ready_min=from_route.ready_min,
                departure_min=dep_from,
                return_min=ret_from,
                order_ids=reduced_order_ids,
                stops=stops_from,
                total_distance_km=dist_from,
                total_duration_min=dur_from,
                total_colli=colli_from,
                total_volume=vol_from,
                total_weight=weight_from,
            )
            new_from_penalty = route_penalty(new_from, from_vehicle, config)

            for to_idx in eachindex(routes)
                from_idx == to_idx && continue
                to_route = routes[to_idx]
                to_vehicle = vehicle_types_by_name[to_route.vehicle_type_name]
                candidate_to, _, candidate_to_penalty = try_insert_order(to_route, order_id, orders_by_id, Dict{String,OrderScore}(), Set{String}(), "normal", 0.0, "balanced", 0.0, 0.0, 0.0, 1.0, Dict{Int,Float64}(), Dict{Int,Float64}(), Dict{Int,Float64}(), instance, to_vehicle, config)
                isnothing(candidate_to) && continue
                delta = (new_from_penalty + candidate_to_penalty) - (base_from_penalty + route_penalty(to_route, to_vehicle, config))
                if delta < best_delta
                    best_delta = delta
                    best_move = (:relocate, from_idx, to_idx, new_from, candidate_to)
                end
            end
        end
    end

    return best_move, best_delta
end

function try_swap_move(routes::Vector{Route}, orders_by_id::Dict{String,Order}, instance::Instance, vehicle_types_by_name::Dict{String,VehicleType}, config::RoutingConfig)
    best_move = nothing
    best_delta = 0.0

    for idx_a in 1:length(routes)
        route_a = routes[idx_a]
        vehicle_a = vehicle_types_by_name[route_a.vehicle_type_name]
        base_a_penalty = route_penalty(route_a, vehicle_a, config)
        for idx_b in (idx_a + 1):length(routes)
            route_b = routes[idx_b]
            vehicle_b = vehicle_types_by_name[route_b.vehicle_type_name]
            base_b_penalty = route_penalty(route_b, vehicle_b, config)
            for pos_a in eachindex(route_a.order_ids)
                for pos_b in eachindex(route_b.order_ids)
                    candidate_a_ids = copy(route_a.order_ids)
                    candidate_b_ids = copy(route_b.order_ids)
                    candidate_a_ids[pos_a], candidate_b_ids[pos_b] = candidate_b_ids[pos_b], candidate_a_ids[pos_a]

                    ok_a, dep_a, ret_a, stops_a, dist_a, dur_a, colli_a, vol_a, weight_a, _ = compute_route_schedule(
                        candidate_a_ids, orders_by_id, instance, vehicle_a, route_a.ready_min, config,
                    )
                    ok_a || continue
                    ok_b, dep_b, ret_b, stops_b, dist_b, dur_b, colli_b, vol_b, weight_b, _ = compute_route_schedule(
                        candidate_b_ids, orders_by_id, instance, vehicle_b, route_b.ready_min, config,
                    )
                    ok_b || continue

                    new_a = Route(
                        route_id=route_a.route_id,
                        depot_id=route_a.depot_id,
                        vehicle_type_name=route_a.vehicle_type_name,
                        vehicle_index=route_a.vehicle_index,
                        trip_index=route_a.trip_index,
                        ready_min=route_a.ready_min,
                        departure_min=dep_a,
                        return_min=ret_a,
                        order_ids=candidate_a_ids,
                        stops=stops_a,
                        total_distance_km=dist_a,
                        total_duration_min=dur_a,
                        total_colli=colli_a,
                        total_volume=vol_a,
                        total_weight=weight_a,
                    )
                    new_b = Route(
                        route_id=route_b.route_id,
                        depot_id=route_b.depot_id,
                        vehicle_type_name=route_b.vehicle_type_name,
                        vehicle_index=route_b.vehicle_index,
                        trip_index=route_b.trip_index,
                        ready_min=route_b.ready_min,
                        departure_min=dep_b,
                        return_min=ret_b,
                        order_ids=candidate_b_ids,
                        stops=stops_b,
                        total_distance_km=dist_b,
                        total_duration_min=dur_b,
                        total_colli=colli_b,
                        total_volume=vol_b,
                        total_weight=weight_b,
                    )
                    delta = (route_penalty(new_a, vehicle_a, config) + route_penalty(new_b, vehicle_b, config)) - (base_a_penalty + base_b_penalty)
                    if delta < best_delta
                        best_delta = delta
                        best_move = (:swap, idx_a, idx_b, new_a, new_b)
                    end
                end
            end
        end
    end

    return best_move, best_delta
end

function improve_routes!(routes::Vector{Route}, orders_by_id::Dict{String,Order}, instance::Instance, vehicle_types_by_name::Dict{String,VehicleType}, config::RoutingConfig)
    iterations = 0
    while iterations < config.local_improvement_budget
        iterations += 1
        relocate_move, relocate_delta = try_relocate_move(routes, orders_by_id, instance, vehicle_types_by_name, config)
        swap_move, swap_delta = try_swap_move(routes, orders_by_id, instance, vehicle_types_by_name, config)

        best_move = nothing
        best_delta = 0.0
        if !isnothing(relocate_move) && relocate_delta < best_delta
            best_move = relocate_move
            best_delta = relocate_delta
        end
        if !isnothing(swap_move) && swap_delta < best_delta
            best_move = swap_move
            best_delta = swap_delta
        end
        isnothing(best_move) && break

        if best_move[1] == :relocate
            _, from_idx, to_idx, new_from, new_to = best_move
            routes[from_idx] = new_from
            routes[to_idx] = new_to
            if isempty(routes[from_idx].order_ids)
                deleteat!(routes, from_idx)
            end
        else
            _, idx_a, idx_b, new_a, new_b = best_move
            routes[idx_a] = new_a
            routes[idx_b] = new_b
        end
    end
end

function rebuild_vehicle_state(routes::Vector{Route}, instance::Instance)
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

function route_utilization_score(route::Route, vehicle::VehicleType)
    return max(route.total_volume / max(vehicle.capacity_volume, 1.0), route.total_weight / max(vehicle.capacity_weight, 1.0))
end

function routing_bucket_stats(routes::Vector{Route}, orders_by_id::Dict{String,Order}, instance::Instance)
    warehouse = instance.warehouse
    bucket_minutes = 15
    usage = Dict{Int,NamedTuple}()
    for route in routes
        bucket = (route.departure_min ÷ bucket_minutes) * bucket_minutes
        current = get(usage, bucket, (departures=0, picking_colli=0.0, picking_volume=0.0, staging_volume=0.0))
        total_pick_min = sum(orders_by_id[id].picking_task_time_min for id in route.order_ids)
        pick_start = max(warehouse.picking_open_min, floor(Int, route.departure_min - total_pick_min))
        pick_bucket = (pick_start ÷ bucket_minutes) * bucket_minutes
        current = (departures=current.departures + 1, picking_colli=current.picking_colli, picking_volume=current.picking_volume, staging_volume=current.staging_volume)
        usage[bucket] = current
        while pick_bucket <= route.departure_min
            cur = get(usage, pick_bucket, (departures=0, picking_colli=0.0, picking_volume=0.0, staging_volume=0.0))
            usage[pick_bucket] = (
                departures=cur.departures,
                picking_colli=cur.picking_colli + route.total_colli,
                picking_volume=cur.picking_volume + route.total_volume,
                staging_volume=cur.staging_volume + (pick_bucket >= ((route.departure_min ÷ bucket_minutes) * bucket_minutes) ? route.total_volume : 0.0),
            )
            pick_bucket += bucket_minutes
        end
    end

    penalty = 0.0
    worst_bucket_penalty = 0.0
    overload_bucket_count = 0
    for (_, u) in usage
        bucket_penalty = 0.0
        bucket_penalty += max(0, u.departures - warehouse.gates) * 100.0
        bucket_penalty += max(0.0, u.picking_colli - warehouse.picking_capacity_colli_per_hour * 0.25) * 4.0
        bucket_penalty += max(0.0, u.picking_volume - warehouse.picking_capacity_volume_per_hour * 0.25) * 8.0
        bucket_penalty += max(0.0, u.staging_volume - warehouse.max_staging_volume) * 6.0
        penalty += bucket_penalty
        if bucket_penalty > 0
            overload_bucket_count += 1
            worst_bucket_penalty = max(worst_bucket_penalty, bucket_penalty)
        end
    end
    return (penalty=penalty, worst_bucket_penalty=worst_bucket_penalty, overload_bucket_count=overload_bucket_count)
end

function routing_bucket_proxy(routes::Vector{Route}, orders_by_id::Dict{String,Order}, instance::Instance)
    return routing_bucket_stats(routes, orders_by_id, instance).penalty
end

function split_candidate_positions(route::Route, orders_by_id::Dict{String,Order})
    positions = Int[]
    n = length(route.order_ids)
    n >= 1 && push!(positions, n)
    n >= 2 && push!(positions, n - 1)
    heavy_pos = argmax([orders_by_id[id].volume + 0.003 * orders_by_id[id].weight for id in route.order_ids])
    heavy_pos ∉ positions && push!(positions, heavy_pos)
    return unique(positions)
end

function refill_priority(order_id::String, score_map::Dict{String,OrderScore})
    score = score_map[order_id]
    protected = (("near_deadline" in score.tags) || ("hard_protected" in score.tags)) ? 1 : 0
    risky = ("risky_flex" in score.tags) ? 1 : 0
    return (-protected, risky, -score.total_score)
end

function split_tail_and_refill!(routes::Vector{Route}, unassigned::Vector{UnassignedOrder}, orders_by_id::Dict{String,Order}, score_map::Dict{String,OrderScore}, instance::Instance, vehicle_types_by_name::Dict{String,VehicleType}, config::RoutingConfig)
    splits_done = 0
    protected_set = Set(id for (id, s) in score_map if (("near_deadline" in s.tags) || ("hard_protected" in s.tags)))
    while splits_done < config.split_tail_budget
        vehicle_ready, vehicle_trip_count = rebuild_vehicle_state(routes, instance)
        base_bucket_stats = routing_bucket_stats(routes, orders_by_id, instance)
        base_depot_proxy = base_bucket_stats.penalty
        ranked_routes = sort(collect(eachindex(routes)), by=i -> route_utilization_score(routes[i], vehicle_types_by_name[routes[i].vehicle_type_name]), rev=true)
        best_accept = nothing
        best_gain = 0.0

        for route_idx in ranked_routes
            route = routes[route_idx]
            length(route.order_ids) < 3 && continue
            vehicle = vehicle_types_by_name[route.vehicle_type_name]
            for pos in split_candidate_positions(route, orders_by_id)
                split_order_id = route.order_ids[pos]
                reduced_ids = copy(route.order_ids)
                deleteat!(reduced_ids, pos)
                ok, dep, ret, stops, dist, dur, colli, vol, weight, _ = compute_route_schedule(reduced_ids, orders_by_id, instance, vehicle, route.ready_min, config)
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

                temp_routes = copy(routes)
                temp_routes[route_idx] = reduced_route
                temp_ready, temp_trip = rebuild_vehicle_state(temp_routes, instance)
                choices, _ = evaluate_order_choices(split_order_id, temp_routes, orders_by_id, score_map, Set{String}(), "normal", 0.0, "balanced", 0.0, 0.0, 0.0, 1.0, Dict{Int,Float64}(), Dict{Int,Float64}(), Dict{Int,Float64}(), instance, vehicle_types_by_name, temp_ready, temp_trip, config; allow_new_route=true)
                isempty(choices) && continue
                choice = choices[1]
                trial_routes = copy(temp_routes)
                if choice.kind == :append
                    trial_routes[choice.target] = choice.candidate
                else
                    push!(trial_routes, choice.candidate)
                end
                trial_bucket_stats = routing_bucket_stats(trial_routes, orders_by_id, instance)
                trial_depot_proxy = trial_bucket_stats.penalty
                config.severe_bucket_veto && trial_bucket_stats.worst_bucket_penalty > max(config.severe_bucket_penalty_threshold, base_bucket_stats.worst_bucket_penalty) && continue
                depot_gain = base_depot_proxy - trial_depot_proxy
                protected_gain = split_order_id in protected_set ? config.split_protected_gain_weight : 0.0
                service_gain = config.split_service_gain_weight
                extra_cost = max(0.0, choice.penalty - route_penalty(route, vehicle, config)) * config.split_extra_cost_weight
                gain = service_gain + config.split_depot_gain_weight * depot_gain + protected_gain - extra_cost
                if gain > best_gain
                    best_gain = gain
                    best_accept = (route_idx=route_idx, reduced_route=reduced_route, choice=choice, split_order_id=split_order_id)
                end
            end
        end

        isnothing(best_accept) && break
        routes[best_accept.route_idx] = best_accept.reduced_route
        vehicle_ready, vehicle_trip_count = rebuild_vehicle_state(routes, instance)
        apply_choice!(best_accept.choice, routes, vehicle_ready, vehicle_trip_count, instance)
        filter!(u -> u.order_id != best_accept.split_order_id, unassigned)
        splits_done += 1
    end

    refill_attempts = 0
    pending_ids = sort([u.order_id for u in unassigned], by=id -> refill_priority(id, score_map))
    while !isempty(pending_ids) && refill_attempts < config.refill_budget
        refill_attempts += 1
        vehicle_ready, vehicle_trip_count = rebuild_vehicle_state(routes, instance)
        base_bucket_stats = routing_bucket_stats(routes, orders_by_id, instance)
        base_depot_proxy = base_bucket_stats.penalty
        order_id, choice, _ = choose_order_by_regret(pending_ids, routes, orders_by_id, score_map, Set{String}(), "normal", 0.0, "balanced", 0.0, 0.0, 0.0, 1.0, Dict{Int,Float64}(), Dict{Int,Float64}(), Dict{Int,Float64}(), instance, vehicle_types_by_name, vehicle_ready, vehicle_trip_count, config; allow_new_route=true)
        isnothing(order_id) && break
        filter!(x -> x != order_id, pending_ids)
        isnothing(choice) && continue

        trial_routes = copy(routes)
        if choice.kind == :append
            trial_routes[choice.target] = choice.candidate
        else
            push!(trial_routes, choice.candidate)
        end
        trial_bucket_stats = routing_bucket_stats(trial_routes, orders_by_id, instance)
        trial_depot_proxy = trial_bucket_stats.penalty
        config.severe_bucket_veto && trial_bucket_stats.worst_bucket_penalty > max(config.severe_bucket_penalty_threshold, base_bucket_stats.worst_bucket_penalty) && continue
        config.refill_worst_bucket_veto && trial_bucket_stats.worst_bucket_penalty > base_bucket_stats.worst_bucket_penalty + config.refill_worst_bucket_growth_tolerance && continue
        depot_gain = base_depot_proxy - trial_depot_proxy
        protected_gain = order_id in protected_set ? config.refill_protected_gain_weight : 0.0
        safe_bonus = ("risky_flex" in score_map[order_id].tags) ? 0.0 : config.refill_safe_bonus_weight
        gain = config.refill_service_gain_weight + protected_gain + safe_bonus + config.refill_depot_gain_weight * depot_gain - config.refill_choice_penalty_weight * choice.penalty
        gain <= 0 && continue

        apply_choice!(choice, routes, vehicle_ready, vehicle_trip_count, instance)
        filter!(u -> u.order_id != order_id, unassigned)
    end
end

function build_routes_for_day(planning_date::Date, instance::Instance, decision::ControllerDecision, config::RoutingConfig)
    orders_by_id = Dict(order.id => order for order in instance.orders)
    vehicle_types_by_name = Dict(v.type_name => v for v in instance.vehicle_types)
    routes = Route[]
    unassigned = UnassignedOrder[]

    vehicle_ready = Dict{Tuple{String,Int},Int}()
    vehicle_trip_count = Dict{Tuple{String,Int},Int}()
    for vt in instance.vehicle_types
        for vehicle_index in 1:vt.count
            key = (vt.type_name, vehicle_index)
            vehicle_ready[key] = instance.warehouse.opening_min
            vehicle_trip_count[key] = 0
        end
    end

    score_map = decision.order_scores
    controller_bucket_signal = String(get(decision.metadata, "bucket_risk_signal", "normal"))
    controller_bucket_pressure_score = Float64(get(decision.metadata, "bucket_pressure_score", 0.0))
    pressure_mode = String(get(decision.metadata, "pressure_mode", "balanced"))
    lambda_gate = Float64(get(decision.metadata, "lambda_gate", 0.0))
    lambda_picking = Float64(get(decision.metadata, "lambda_picking", 0.0))
    lambda_staging = Float64(get(decision.metadata, "lambda_staging", 0.0))
    lambda_scale = Float64(get(decision.metadata, "lambda_scale", 1.0))
    dynamic_lambda_gate = Dict{Int,Float64}(get(decision.metadata, "dynamic_lambda_gate", Dict{Int,Float64}()))
    dynamic_lambda_picking = Dict{Int,Float64}(get(decision.metadata, "dynamic_lambda_picking", Dict{Int,Float64}()))
    dynamic_lambda_staging = Dict{Int,Float64}(get(decision.metadata, "dynamic_lambda_staging", Dict{Int,Float64}()))
    targeted_bias_ids = Set{String}()
    if controller_bucket_signal != "normal"
        for order_id in decision.admitted_flex_order_ids
            tags = Set(get(score_map, order_id, OrderScore(order_id=order_id, total_score=0.0, urgency_score=0.0, age_score=0.0, risk_score=0.0, commitment_score=0.0, tags=String[])).tags)
            if config.controller_feedback_target_trip2_late_only
                (("risky_flex" in tags) && (("trip2_sensitive" in tags) || ("late_window" in tags))) && push!(targeted_bias_ids, order_id)
            else
                ("risky_flex" in tags) && push!(targeted_bias_ids, order_id)
            end
        end
    end
    protected_ids = sort(copy(decision.protected_order_ids), by=id -> insertion_priority(orders_by_id[id], score_map[id]))
    flex_ids = sort(copy(decision.admitted_flex_order_ids), by=id -> insertion_priority(orders_by_id[id], score_map[id]))

    seed_count = min(config.protected_seed_count, length(protected_ids))
    remaining_protected = copy(protected_ids)

    for _ in 1:seed_count
        isempty(remaining_protected) && break
        order_id, choice, failure_reasons = choose_order_by_regret(remaining_protected, routes, orders_by_id, score_map, targeted_bias_ids, controller_bucket_signal, controller_bucket_pressure_score, pressure_mode, lambda_gate, lambda_picking, lambda_staging, lambda_scale, dynamic_lambda_gate, dynamic_lambda_picking, dynamic_lambda_staging, instance, vehicle_types_by_name, vehicle_ready, vehicle_trip_count, config; allow_new_route=true)
        isnothing(order_id) && break
        filter!(x -> x != order_id, remaining_protected)
        if isnothing(choice)
            reason = isempty(failure_reasons) ? "no_feasible_seed_route" : first(sort(collect(Set(failure_reasons))))
            push!(unassigned, UnassignedOrder(order_id=order_id, reason=reason))
            continue
        end
        apply_choice!(choice, routes, vehicle_ready, vehicle_trip_count, instance)
    end

    pending = vcat(remaining_protected, flex_ids)
    while !isempty(pending)
        order_id, choice, failure_reasons = choose_order_by_regret(pending, routes, orders_by_id, score_map, targeted_bias_ids, controller_bucket_signal, controller_bucket_pressure_score, pressure_mode, lambda_gate, lambda_picking, lambda_staging, lambda_scale, dynamic_lambda_gate, dynamic_lambda_picking, dynamic_lambda_staging, instance, vehicle_types_by_name, vehicle_ready, vehicle_trip_count, config; allow_new_route=true)
        isnothing(order_id) && break
        filter!(x -> x != order_id, pending)
        if isnothing(choice)
            is_protected = order_id in Set(decision.protected_order_ids)
            default_reason = is_protected ? "no_feasible_protected_insertion" : "no_feasible_route"
            reason = isempty(failure_reasons) ? default_reason : first(sort(collect(Set(failure_reasons))))
            push!(unassigned, UnassignedOrder(order_id=order_id, reason=reason))
            continue
        end
        apply_choice!(choice, routes, vehicle_ready, vehicle_trip_count, instance)
    end

    improve_routes!(routes, orders_by_id, instance, vehicle_types_by_name, config)
    split_tail_and_refill!(routes, unassigned, orders_by_id, score_map, instance, vehicle_types_by_name, config)

    sort!(routes, by=r -> (r.vehicle_type_name, r.vehicle_index, r.trip_index, r.departure_min))
    return RoutingSolution(planning_date=planning_date, routes=routes, unassigned=unassigned)
end
