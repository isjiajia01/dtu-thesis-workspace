using JSON3
using Dates

function visible_orders_for_day(instance::Instance, planning_date::Date, carryover_ids::Set{String}, completed_ids::Set{String})
    visible = Order[]
    for order in instance.orders
        order.id in completed_ids && continue
        order.id in carryover_ids || order.requested_date <= planning_date || continue
        planning_date in order.feasible_dates || continue
        push!(visible, order)
    end
    return visible
end

function run_single_day(benchmark_path::AbstractString, matrix_dir::AbstractString, output_path::AbstractString; config::SolverConfig=SolverConfig())
    instance = load_instance(benchmark_path, matrix_dir)
    planning_date = instance.start_date
    day_state = build_initial_day_state(planning_date, [order.id for order in instance.orders])

    t0 = time()
    initial_decision = make_controller_decision(planning_date, instance.orders, day_state, config.controller)
    initial_routing_solution = build_routes_for_day(planning_date, instance, initial_decision, config.routing)
    initial_repair_result = repair_solution(initial_routing_solution, instance, config.repair)

    day_state.metadata["last_depot_penalty"] = initial_repair_result.diagnostics.depot_penalty
    day_state.metadata["last_overload_bucket_count"] = initial_repair_result.diagnostics.overload_bucket_count

    decision = make_controller_decision(planning_date, instance.orders, day_state, config.controller)
    routing_solution = build_routes_for_day(planning_date, instance, decision, config.routing)
    repair_result = repair_solution(routing_solution, instance, config.repair)
    runtime_seconds = time() - t0
    summary = summarize_run(instance.name, runtime_seconds, repair_result, length(decision.deferred_order_ids))

    payload = (
        initial_pass=(
            decision=as_named_tuple(initial_decision),
            summary=(
                depot_penalty=initial_repair_result.diagnostics.depot_penalty,
                overload_bucket_count=initial_repair_result.diagnostics.overload_bucket_count,
                assigned_orders=sum(length(route.order_ids) for route in initial_repair_result.repaired_solution.routes),
                deferred_orders=length(initial_decision.deferred_order_ids),
            ),
        ),
        decision=as_named_tuple(decision),
        routing_solution=as_named_tuple(routing_solution),
        repair_result=as_named_tuple(repair_result),
        summary=as_named_tuple(summary),
    )

    mkpath(dirname(output_path))
    open(output_path, "w") do io
        JSON3.pretty(io, payload)
    end
    return payload
end

function dominant_pressure_mode(diagnostics::DepotDiagnostics)
    gate_sum = sum(bucket.gate_over for bucket in diagnostics.bucket_usage)
    picking_sum = sum(bucket.picking_colli_over + bucket.picking_volume_over for bucket in diagnostics.bucket_usage)
    staging_sum = sum(bucket.staging_over for bucket in diagnostics.bucket_usage)
    if gate_sum <= 0 && picking_sum <= 0 && staging_sum <= 0
        return "balanced"
    elseif gate_sum >= picking_sum && gate_sum >= staging_sum
        return "gate"
    elseif staging_sum >= picking_sum && staging_sum >= gate_sum
        return "staging"
    else
        return "picking"
    end
end

function diagnostics_bucket_maps(diagnostics::DepotDiagnostics, instance::Instance, config::RepairConfig)
    gate_map = Dict{Int,Float64}()
    picking_map = Dict{Int,Float64}()
    staging_map = Dict{Int,Float64}()
    bucket_fraction = config.bucket_minutes / 60.0
    gate_cap = max(instance.warehouse.gates, 1)
    picking_colli_cap = max(instance.warehouse.picking_capacity_colli_per_hour * bucket_fraction, 1e-6)
    picking_volume_cap = max(instance.warehouse.picking_capacity_volume_per_hour * bucket_fraction, 1e-6)
    staging_cap = max(instance.warehouse.max_staging_volume, 1e-6)
    for bucket in diagnostics.bucket_usage
        gate_map[bucket.bucket_start_min] = bucket.departures / gate_cap
        picking_map[bucket.bucket_start_min] = max(bucket.picking_colli / picking_colli_cap, bucket.picking_volume / picking_volume_cap)
        staging_map[bucket.bucket_start_min] = bucket.staging_volume / staging_cap
    end
    return gate_map, picking_map, staging_map
end

function run_multiday(benchmark_path::AbstractString, matrix_dir::AbstractString, output_path::AbstractString; config::SolverConfig=SolverConfig())
    instance = load_instance(benchmark_path, matrix_dir)
    carryover_ids = Set{String}()
    completed_ids = Set{String}()
    expired_ids = Set{String}()
    day_results = NamedTuple[]
    previous_penalty = 0.0
    previous_overloads = 0
    previous_pressure_mode = "balanced"
    previous_gate_bucket_usage = Dict{Int,Float64}()
    previous_picking_bucket_usage = Dict{Int,Float64}()
    previous_staging_bucket_usage = Dict{Int,Float64}()

    t0 = time()
    for planning_date in instance.start_date:Day(1):instance.end_date
        visible = visible_orders_for_day(instance, planning_date, carryover_ids, completed_ids)

        for order in instance.orders
            order.id in completed_ids && continue
            order.id in expired_ids && continue
            planning_date > order.service_date_to && push!(expired_ids, order.id)
        end

        isempty(visible) && continue
        day_state = build_initial_day_state(planning_date, [order.id for order in visible])
        day_state.metadata["last_depot_penalty"] = previous_penalty
        day_state.metadata["last_overload_bucket_count"] = previous_overloads
        day_state.metadata["last_pressure_mode"] = previous_pressure_mode
        day_state.metadata["last_gate_bucket_usage"] = previous_gate_bucket_usage
        day_state.metadata["last_picking_bucket_usage"] = previous_picking_bucket_usage
        day_state.metadata["last_staging_bucket_usage"] = previous_staging_bucket_usage
        day_state.metadata["shadow_price_activation_utilization"] = config.routing.shadow_price_activation_utilization
        day_state.metadata["shadow_price_convex_gamma"] = config.routing.shadow_price_convex_gamma
        day_state.metadata["shadow_price_peak_eta"] = config.routing.shadow_price_peak_eta
        day_state.metadata["alpha_gate"] = config.routing.alpha_gate
        day_state.metadata["alpha_picking"] = config.routing.alpha_picking
        day_state.metadata["alpha_staging"] = config.routing.alpha_staging
        day_state.metadata["beta_gate"] = config.routing.beta_gate
        day_state.metadata["beta_picking"] = config.routing.beta_picking
        day_state.metadata["beta_staging"] = config.routing.beta_staging

        decision = make_controller_decision(planning_date, visible, day_state, config.controller)
        sub_instance = Instance(
            name=instance.name,
            start_date=planning_date,
            end_date=planning_date,
            depot_id=instance.depot_id,
            orders=visible,
            warehouse=instance.warehouse,
            vehicle_types=instance.vehicle_types,
            matrix_ref=instance.matrix_ref,
        )
        routing_solution = build_routes_for_day(planning_date, sub_instance, decision, config.routing)
        repair_result = repair_solution(routing_solution, sub_instance, config.repair)

        assigned_ids = Set{String}(vcat([route.order_ids for route in repair_result.repaired_solution.routes]...))
        union!(completed_ids, assigned_ids)
        deferred_ids = Set(decision.deferred_order_ids)
        unassigned_ids = Set(u.order_id for u in repair_result.repaired_solution.unassigned)

        next_carryover = Set{String}()
        for order in visible
            order.id in completed_ids && continue
            order.id in expired_ids && continue
            if order.id in deferred_ids || order.id in unassigned_ids
                if order.service_date_to > planning_date
                    push!(next_carryover, order.id)
                else
                    push!(expired_ids, order.id)
                end
            end
        end
        carryover_ids = next_carryover
        previous_penalty = repair_result.diagnostics.depot_penalty
        previous_overloads = repair_result.diagnostics.overload_bucket_count
        previous_pressure_mode = dominant_pressure_mode(repair_result.diagnostics)
        previous_gate_bucket_usage, previous_picking_bucket_usage, previous_staging_bucket_usage = diagnostics_bucket_maps(repair_result.diagnostics, sub_instance, config.repair)

        push!(day_results, (
            date=string(planning_date),
            visible_orders=length(visible),
            assigned_orders=length(assigned_ids),
            cumulative_assigned_orders=length(completed_ids),
            deferred_orders=length(deferred_ids),
            carryover_orders=length(carryover_ids),
            expired_orders=length(expired_ids),
            depot_penalty=repair_result.diagnostics.depot_penalty,
            overload_bucket_count=repair_result.diagnostics.overload_bucket_count,
            pressure_mode=previous_pressure_mode,
            summary=as_named_tuple(summarize_run(instance.name, 0.0, repair_result, length(decision.deferred_order_ids))),
        ))
    end

    runtime_seconds = time() - t0
    total_orders = length(instance.orders)
    unique_assigned_orders = length(completed_ids)
    unique_expired_orders = length(expired_ids)
    service_rate = total_orders == 0 ? 0.0 : unique_assigned_orders / total_orders

    payload = (
        instance_name=instance.name,
        horizon_start=string(instance.start_date),
        horizon_end=string(instance.end_date),
        runtime_seconds=runtime_seconds,
        total_orders=total_orders,
        unique_assigned_orders=unique_assigned_orders,
        unique_expired_orders=unique_expired_orders,
        service_rate=service_rate,
        eligible_count=total_orders,
        delivered_within_window_count=unique_assigned_orders,
        deadline_failure_count=unique_expired_orders,
        service_rate_within_window=service_rate,
        total_deferred_events=sum(day.deferred_orders for day in day_results),
        final_carryover_orders=length(carryover_ids),
        metric_definitions=(
            eligible_count="Total unique orders in the benchmark horizon.",
            delivered_within_window_count="Unique orders assigned on or before their service_date_to within the rolling horizon.",
            deadline_failure_count="Unique orders that reached service_date_to without being assigned.",
            service_rate_within_window="delivered_within_window_count / eligible_count",
            note="22.03-compatible paper-facing summary fields. Deferred events and carryover remain 22.04 runner-specific process metrics.",
        ),
        day_results=day_results,
    )

    mkpath(dirname(output_path))
    open(output_path, "w") do io
        JSON3.pretty(io, payload)
    end
    return payload
end
