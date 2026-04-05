using Pkg
Pkg.activate(joinpath(@__DIR__, "..", "..", "src", "algorithms", "fresh_solver", "julia"))
Pkg.instantiate()

using Dates, JSON3, FreshSolver

function build_or_v8_1_config()
    return FreshSolver.SolverConfig(
        controller=FreshSolver.ControllerConfig(
            protected_reserve_ratio=0.22,
            hard_protected_ratio=0.48,
            flex_admission_cap_ratio=0.84,
            risky_flex_cap_ratio=0.18,
            risk_clip_penalty=3.8,
            depot_penalty_feedback_threshold=1500.0,
            overload_feedback_threshold=4,
            severe_depot_penalty_feedback_threshold=2400.0,
            severe_overload_feedback_threshold=7,
            feedback_clip_step=0.16,
            feedback_risky_clip_step=0.18,
            severe_feedback_clip_step=0.26,
            severe_feedback_risky_clip_step=0.30,
            dynamic_shadow_price_controller=true,
            controller_shadow_price_weight=0.28,
            controller_shadow_price_flex_only=true,
        ),
        routing=FreshSolver.RoutingConfig(
            max_orders_per_route=7,
            depot_proxy_penalty=3.2,
            trip2_penalty=15.0,
            depot_service_buffer_min=9.0,
            protected_seed_count=10,
            regret_k=2,
            local_improvement_budget=120,
            split_tail_budget=10,
            refill_budget=20,
            split_service_gain_weight=1.2,
            split_depot_gain_weight=0.008,
            split_protected_gain_weight=2.8,
            split_extra_cost_weight=0.045,
            refill_service_gain_weight=1.05,
            refill_depot_gain_weight=0.006,
            refill_protected_gain_weight=3.1,
            refill_safe_bonus_weight=1.5,
            refill_choice_penalty_weight=0.05,
            severe_bucket_veto=true,
            severe_bucket_penalty_threshold=700.0,
            refill_worst_bucket_veto=true,
            refill_worst_bucket_growth_tolerance=25.0,
            bucket_aware_insertion_bias=true,
            targeted_insertion_bias=true,
            controller_bucket_feedback_bias=true,
            controller_bucket_feedback_fine_grained=true,
            pressure_mode_pattern_feedback=true,
            controller_bucket_feedback_weight=1.2,
            late_bucket_start_min=810,
            trip2_late_bias_weight=4.0,
            heavy_late_bias_weight=1.3,
            staging_risk_bias_weight=0.8,
            protect_near_deadline_bias_relief=5.8,
            shadow_price_feedback=true,
            shadow_price_weight=0.12,
            normalized_shadow_price=true,
            regime_aware_normalization=true,
            dynamic_shadow_price_v8=true,
            shadow_price_activation_utilization=0.82,
            shadow_price_convex_gamma=1.8,
            shadow_price_peak_eta=2.4,
            alpha_gate=0.6,
            alpha_picking=1.5,
            alpha_staging=0.35,
            beta_gate=0.8,
            beta_picking=1.4,
            beta_staging=0.4,
            service_shield_feedback=true,
            structured_service_shield=true,
            service_shield_relief_weight=1.8,
        ),
        repair=FreshSolver.RepairConfig(
            gate_penalty_weight=150.0,
            picking_colli_penalty_weight=8.0,
            picking_volume_penalty_weight=12.0,
            staging_penalty_weight=10.0,
            reassignment_budget=8,
            rollback_budget=10,
        ),
    )
end

hhmm(mins) = lpad(string(mins ÷ 60), 2, '0') * ":" * lpad(string(mins % 60), 2, '0')

function dominant_pressure_mode(diagnostics)
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

function write_csv(path, rows)
    open(path, "w") do io
        println(io, join(["date","bucket_start_min","bucket_hhmm","departures","picking_colli","picking_volume","staging_volume","gate_over","picking_colli_over","picking_volume_over","total_picking_over","staging_over","bucket_penalty","pressure_mode"], ","))
        for r in rows
            println(io, join([r["date"], string(r["bucket_start_min"]), r["bucket_hhmm"], string(r["departures"]), string(r["picking_colli"]), string(r["picking_volume"]), string(r["staging_volume"]), string(r["gate_over"]), string(r["picking_colli_over"]), string(r["picking_volume_over"]), string(r["total_picking_over"]), string(r["staging_over"]), string(r["bucket_penalty"]), r["pressure_mode"]], ","))
        end
    end
end

function main()
    thesis_root = normpath(joinpath(@__DIR__, "..", ".."))
    benchmark = joinpath(thesis_root, "data", "processed", "benchmarks", "multiday_benchmark_west.json")
    matrix_dir = joinpath(thesis_root, "data", "processed", "matrices", "vrp_matrix_west")
    out_csv = joinpath(thesis_root, "results", "diagnostics", "west_or_v8_1_picking_buckets.csv")
    out_json = joinpath(thesis_root, "results", "diagnostics", "west_or_v8_1_picking_summary.json")

    config = build_or_v8_1_config()
    instance = FreshSolver.load_instance(benchmark, matrix_dir)
    carryover_ids = Set{String}(); completed_ids = Set{String}(); expired_ids = Set{String}()
    previous_penalty = 0.0; previous_overloads = 0; previous_pressure_mode = "balanced"
    previous_gate_bucket_usage = Dict{Int,Float64}(); previous_picking_bucket_usage = Dict{Int,Float64}(); previous_staging_bucket_usage = Dict{Int,Float64}()
    rows = Vector{Dict{String,Any}}(); day_summary = Vector{Dict{String,Any}}()

    for planning_date in instance.start_date:Day(1):instance.end_date
        visible = FreshSolver.visible_orders_for_day(instance, planning_date, carryover_ids, completed_ids)
        for order in instance.orders
            order.id in completed_ids && continue
            order.id in expired_ids && continue
            planning_date > order.service_date_to && push!(expired_ids, order.id)
        end
        isempty(visible) && continue
        day_state = FreshSolver.build_initial_day_state(planning_date, [order.id for order in visible])
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

        decision = FreshSolver.make_controller_decision(planning_date, visible, day_state, config.controller)
        sub_instance = FreshSolver.Instance(name=instance.name, start_date=planning_date, end_date=planning_date, depot_id=instance.depot_id, orders=visible, warehouse=instance.warehouse, vehicle_types=instance.vehicle_types, matrix_ref=instance.matrix_ref)
        routing_solution = FreshSolver.build_routes_for_day(planning_date, sub_instance, decision, config.routing)
        repair_result = FreshSolver.repair_solution(routing_solution, sub_instance, config.repair)
        diagnostics = repair_result.diagnostics
        pressure_mode = dominant_pressure_mode(diagnostics)

        assigned_ids = Set{String}(vcat([route.order_ids for route in repair_result.repaired_solution.routes]...)); union!(completed_ids, assigned_ids)
        deferred_ids = Set(decision.deferred_order_ids); unassigned_ids = Set(u.order_id for u in repair_result.repaired_solution.unassigned)
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
        previous_penalty = diagnostics.depot_penalty; previous_overloads = diagnostics.overload_bucket_count; previous_pressure_mode = pressure_mode
        previous_gate_bucket_usage = Dict(bucket.bucket_start_min => bucket.departures / max(instance.warehouse.gates, 1) for bucket in diagnostics.bucket_usage)
        previous_picking_bucket_usage = Dict(bucket.bucket_start_min => max(bucket.picking_colli / max(instance.warehouse.picking_capacity_colli_per_hour * 0.25, 1e-6), bucket.picking_volume / max(instance.warehouse.picking_capacity_volume_per_hour * 0.25, 1e-6)) for bucket in diagnostics.bucket_usage)
        previous_staging_bucket_usage = Dict(bucket.bucket_start_min => bucket.staging_volume / max(instance.warehouse.max_staging_volume, 1e-6) for bucket in diagnostics.bucket_usage)

        morning = 0.0; midday = 0.0; late = 0.0; peak_bucket = ""; peak_val = -1.0; pick_sum = 0.0; gate_sum = 0.0; staging_sum = 0.0
        for bucket in diagnostics.bucket_usage
            total_pick = bucket.picking_colli_over + bucket.picking_volume_over
            bucket_str = hhmm(bucket.bucket_start_min)
            push!(rows, Dict("date"=>string(planning_date),"bucket_start_min"=>bucket.bucket_start_min,"bucket_hhmm"=>bucket_str,"departures"=>bucket.departures,"picking_colli"=>bucket.picking_colli,"picking_volume"=>bucket.picking_volume,"staging_volume"=>bucket.staging_volume,"gate_over"=>bucket.gate_over,"picking_colli_over"=>bucket.picking_colli_over,"picking_volume_over"=>bucket.picking_volume_over,"total_picking_over"=>total_pick,"staging_over"=>bucket.staging_over,"bucket_penalty"=>bucket.bucket_penalty,"pressure_mode"=>pressure_mode))
            pick_sum += total_pick; gate_sum += bucket.gate_over; staging_sum += bucket.staging_over
            if bucket.bucket_start_min < 720
                morning += total_pick
            elseif bucket.bucket_start_min < 900
                midday += total_pick
            else
                late += total_pick
            end
            if total_pick > peak_val
                peak_val = total_pick; peak_bucket = bucket_str
            end
        end
        push!(day_summary, Dict("date"=>string(planning_date),"pressure_mode"=>pressure_mode,"picking_over_sum"=>pick_sum,"gate_over_sum"=>gate_sum,"staging_over_sum"=>staging_sum,"overload_bucket_count"=>diagnostics.overload_bucket_count,"depot_penalty"=>diagnostics.depot_penalty,"peak_picking_bucket"=>peak_bucket,"peak_picking_over"=>peak_val,"morning_picking_over"=>morning,"midday_picking_over"=>midday,"late_picking_over"=>late))
    end

    mkpath(dirname(out_csv)); write_csv(out_csv, rows)
    open(out_json, "w") do io
        JSON3.pretty(io, Dict("summary_by_day"=>day_summary,"totals"=>Dict("days"=>length(day_summary),"total_picking_over"=>sum(d["picking_over_sum"] for d in day_summary),"total_gate_over"=>sum(d["gate_over_sum"] for d in day_summary),"total_staging_over"=>sum(d["staging_over_sum"] for d in day_summary),"morning_picking_over"=>sum(d["morning_picking_over"] for d in day_summary),"midday_picking_over"=>sum(d["midday_picking_over"] for d in day_summary),"late_picking_over"=>sum(d["late_picking_over"] for d in day_summary))))
    end
    println(out_csv); println(out_json)
end

main()
