using Dates

function order_risk_flags(order::Order, planning_date::Date, config::ControllerConfig)
    days_to_deadline = max(Dates.value(order.service_date_to - planning_date), 0)
    window_width = order.time_window_end_min - order.time_window_start_min
    late_window = order.time_window_start_min >= config.late_window_threshold_min
    heavy_order = order.volume >= config.heavy_volume_threshold || order.weight >= config.heavy_weight_threshold
    trip2_sensitive = late_window || window_width <= 180
    hard_protected = days_to_deadline <= 1 || window_width <= 120
    risky_flex = late_window || heavy_order || trip2_sensitive
    return (
        late_window=late_window,
        heavy_order=heavy_order,
        trip2_sensitive=trip2_sensitive,
        hard_protected=hard_protected,
        risky_flex=risky_flex,
        days_to_deadline=days_to_deadline,
        window_width=window_width,
    )
end

function score_order(order::Order, planning_date::Date, day_state::DayState, config::ControllerConfig)
    flags = order_risk_flags(order, planning_date, config)
    waiting_days = max(Dates.value(planning_date - order.requested_date), 0)
    window_days = max(Dates.value(order.service_date_to - order.service_date_from), 0)

    urgency_score = config.urgency_weight / max(flags.days_to_deadline + 1, 1)
    age_score = config.age_weight * waiting_days
    risk_score = config.risk_weight / max(window_days + 1, 1)
    commitment_score = order.id in day_state.committed_order_ids ? config.commitment_weight : 0.0

    depot_risk_penalty = 0.0
    flags.late_window && (depot_risk_penalty += 0.6 * config.risk_clip_penalty)
    flags.heavy_order && (depot_risk_penalty += 0.8 * config.risk_clip_penalty)
    flags.trip2_sensitive && (depot_risk_penalty += 0.5 * config.risk_clip_penalty)

    total_score = urgency_score + age_score + risk_score + commitment_score - depot_risk_penalty

    tags = String[]
    flags.days_to_deadline <= 1 && push!(tags, "near_deadline")
    waiting_days >= 2 && push!(tags, "aged")
    window_days == 0 && push!(tags, "tight_window")
    flags.late_window && push!(tags, "late_window")
    flags.heavy_order && push!(tags, "heavy_order")
    flags.trip2_sensitive && push!(tags, "trip2_sensitive")
    flags.hard_protected && push!(tags, "hard_protected")
    flags.risky_flex && push!(tags, "risky_flex")

    return OrderScore(
        order_id=order.id,
        total_score=total_score,
        urgency_score=urgency_score,
        age_score=age_score,
        risk_score=risk_score,
        commitment_score=commitment_score,
        tags=tags,
    )
end

function split_protected_orders(ranked_orders::Vector{Order}, scores::Dict{String,OrderScore}, config::ControllerConfig)
    protected_pool = [o for o in ranked_orders if ("near_deadline" in scores[o.id].tags) || ("hard_protected" in scores[o.id].tags)]
    if isempty(protected_pool)
        protected_count = isempty(ranked_orders) ? 0 : max(1, floor(Int, length(ranked_orders) * config.protected_reserve_ratio))
        protected_pool = ranked_orders[1:min(protected_count, length(ranked_orders))]
    end

    protected_pool = sort(protected_pool; by=o -> scores[o.id].total_score, rev=true)
    hard_target = isempty(protected_pool) ? 0 : max(1, floor(Int, length(protected_pool) * config.hard_protected_ratio))
    hard_protected = [o.id for o in protected_pool if "hard_protected" in scores[o.id].tags]
    if length(hard_protected) < hard_target
        remaining = [o.id for o in protected_pool if !(o.id in Set(hard_protected))]
        append!(hard_protected, remaining[1:min(hard_target - length(hard_protected), length(remaining))])
    end
    protected_ids = [o.id for o in protected_pool]
    return unique(hard_protected), unique(protected_ids)
end

function clip_flex_orders(ranked_orders::Vector{Order}, protected_ids::Vector{String}, scores::Dict{String,OrderScore}, config::ControllerConfig, day_state::DayState)
    protected_set = Set(protected_ids)
    flex_orders = [o for o in ranked_orders if !(o.id in protected_set)]

    feedback_factor = 1.0
    risky_feedback_factor = 1.0
    last_penalty = Float64(get(day_state.metadata, "last_depot_penalty", 0.0))
    last_overloads = Int(get(day_state.metadata, "last_overload_bucket_count", 0))
    if last_penalty >= config.severe_depot_penalty_feedback_threshold || last_overloads >= config.severe_overload_feedback_threshold
        feedback_factor = max(0.40, 1.0 - config.severe_feedback_clip_step)
        risky_feedback_factor = max(0.10, 1.0 - config.severe_feedback_risky_clip_step)
    elseif last_penalty >= config.depot_penalty_feedback_threshold || last_overloads >= config.overload_feedback_threshold
        feedback_factor = max(0.50, 1.0 - config.feedback_clip_step)
        risky_feedback_factor = max(0.20, 1.0 - config.feedback_risky_clip_step)
    end

    flex_cap = floor(Int, length(ranked_orders) * config.flex_admission_cap_ratio * feedback_factor) - length(protected_ids)
    flex_cap = max(0, flex_cap)
    risky_cap = max(1, floor(Int, max(flex_cap, 1) * config.risky_flex_cap_ratio * risky_feedback_factor))

    admitted = String[]
    deferred = String[]
    risky_count = 0

    for order in flex_orders
        is_risky = "risky_flex" in scores[order.id].tags
        if length(admitted) >= flex_cap
            push!(deferred, order.id)
        elseif is_risky && risky_count >= risky_cap
            push!(deferred, order.id)
        else
            push!(admitted, order.id)
            is_risky && (risky_count += 1)
        end
    end

    return admitted, deferred, feedback_factor, risky_feedback_factor
end

function bucket_shadow_price(utilization::Float64, α::Float64, β::Float64, τ::Float64, γ::Float64, η::Float64)
    smooth_term = α * max(0.0, utilization - τ)^γ
    peak_term = β * max(0.0, utilization - 1.0)^η
    return smooth_term + peak_term
end

function build_dynamic_shadow_maps(day_state::DayState)
    gate_usage = get(day_state.metadata, "last_gate_bucket_usage", Dict{Int,Float64}())
    picking_usage = get(day_state.metadata, "last_picking_bucket_usage", Dict{Int,Float64}())
    staging_usage = get(day_state.metadata, "last_staging_bucket_usage", Dict{Int,Float64}())
    return gate_usage, picking_usage, staging_usage
end

function make_controller_decision(planning_date::Date, orders::Vector{Order}, day_state::DayState, config::ControllerConfig)
    scores = Dict{String,OrderScore}()
    for order in orders
        scores[order.id] = score_order(order, planning_date, day_state, config)
    end
    ranked = sort(orders; by=o -> scores[o.id].total_score, rev=true)

    hard_protected, protected_ids = split_protected_orders(ranked, scores, config)
    admitted_flex, deferred_ids, feedback_factor, risky_feedback_factor = clip_flex_orders(ranked, protected_ids, scores, config, day_state)

    protected_set = Set(protected_ids)
    admitted_set = Set(admitted_flex)
    deferred_ids = unique(vcat(
        deferred_ids,
        [o.id for o in ranked if !(o.id in protected_set) && !(o.id in admitted_set)],
    ))

    last_penalty = Float64(get(day_state.metadata, "last_depot_penalty", 0.0))
    last_overloads = Int(get(day_state.metadata, "last_overload_bucket_count", 0))
    last_pressure_mode = String(get(day_state.metadata, "last_pressure_mode", "balanced"))
    bucket_risk_signal = if last_penalty >= config.severe_depot_penalty_feedback_threshold || last_overloads >= config.severe_overload_feedback_threshold
        "severe"
    elseif last_penalty >= config.depot_penalty_feedback_threshold || last_overloads >= config.overload_feedback_threshold
        "elevated"
    else
        "normal"
    end
    bucket_pressure_score = min(2.0,
        0.5 * (last_penalty / max(config.depot_penalty_feedback_threshold, 1.0)) +
        0.5 * (last_overloads / max(config.overload_feedback_threshold, 1))
    )
    lambda_gate = 0.0
    lambda_picking = 0.0
    lambda_staging = 0.0
    if last_pressure_mode == "gate"
        lambda_gate = bucket_pressure_score
    elseif last_pressure_mode == "picking"
        lambda_picking = bucket_pressure_score
    elseif last_pressure_mode == "staging"
        lambda_staging = bucket_pressure_score
    else
        λ = 0.5 * bucket_pressure_score
        lambda_gate = λ
        lambda_picking = λ
        lambda_staging = λ
    end
    lambda_scale = min(1.0, max(0.35,
        0.65 * (config.depot_penalty_feedback_threshold / max(last_penalty, config.depot_penalty_feedback_threshold)) +
        0.35 * (config.overload_feedback_threshold / max(last_overloads, config.overload_feedback_threshold, 1))
    ))
    if last_pressure_mode == "gate"
        lambda_scale *= 0.92
    elseif last_pressure_mode == "staging"
        lambda_scale *= 0.85
    elseif last_pressure_mode == "picking"
        lambda_scale *= 0.88
    end
    lambda_scale = min(1.0, max(0.30, lambda_scale))

    gate_bucket_usage, picking_bucket_usage, staging_bucket_usage = build_dynamic_shadow_maps(day_state)
    dynamic_lambda_gate = Dict{Int,Float64}()
    dynamic_lambda_picking = Dict{Int,Float64}()
    dynamic_lambda_staging = Dict{Int,Float64}()
    τ = Float64(get(day_state.metadata, "shadow_price_activation_utilization", 0.80))
    γ = Float64(get(day_state.metadata, "shadow_price_convex_gamma", 2.0))
    η = Float64(get(day_state.metadata, "shadow_price_peak_eta", 3.0))
    α_gate = Float64(get(day_state.metadata, "alpha_gate", 0.8))
    α_picking = Float64(get(day_state.metadata, "alpha_picking", 1.4))
    α_staging = Float64(get(day_state.metadata, "alpha_staging", 0.6))
    β_gate = Float64(get(day_state.metadata, "beta_gate", 1.2))
    β_picking = Float64(get(day_state.metadata, "beta_picking", 2.2))
    β_staging = Float64(get(day_state.metadata, "beta_staging", 0.8))

    if config.dynamic_shadow_price_controller
        for (bucket, util) in gate_bucket_usage
            dynamic_lambda_gate[bucket] = bucket_shadow_price(util, α_gate, β_gate, τ, γ, η)
        end
        for (bucket, util) in picking_bucket_usage
            dynamic_lambda_picking[bucket] = bucket_shadow_price(util, α_picking, β_picking, τ, γ, η)
        end
        for (bucket, util) in staging_bucket_usage
            dynamic_lambda_staging[bucket] = bucket_shadow_price(util, α_staging, β_staging, τ, γ, η)
        end
    end

    if config.dynamic_shadow_price_controller && config.controller_shadow_price_weight > 0
        adjusted_admitted = String[]
        adjusted_deferred = copy(deferred_ids)
        for order in ranked
            order.id in Set(protected_ids) && continue
            order.id in Set(admitted_flex) || continue
            tags = Set(scores[order.id].tags)
            if config.controller_shadow_price_flex_only && !("risky_flex" in tags)
                push!(adjusted_admitted, order.id)
                continue
            end
            expected_bucket = max(0, order.time_window_start_min - 180)
            expected_bucket = (expected_bucket ÷ 15) * 15
            pressure_penalty = get(dynamic_lambda_gate, expected_bucket, 0.0) + get(dynamic_lambda_picking, expected_bucket, 0.0) + 0.5 * get(dynamic_lambda_staging, expected_bucket, 0.0)
            if pressure_penalty > config.controller_shadow_price_weight * max(1.0, scores[order.id].total_score)
                push!(adjusted_deferred, order.id)
            else
                push!(adjusted_admitted, order.id)
            end
        end
        admitted_flex = adjusted_admitted
        deferred_ids = unique(adjusted_deferred)
    end

    return ControllerDecision(
        planning_date=planning_date,
        protected_order_ids=protected_ids,
        admitted_flex_order_ids=admitted_flex,
        deferred_order_ids=deferred_ids,
        order_scores=scores,
        metadata=Dict(
            "hard_protected_count" => length(hard_protected),
            "protected_count" => length(protected_ids),
            "admitted_flex_count" => length(admitted_flex),
            "deferred_count" => length(deferred_ids),
            "feedback_factor" => feedback_factor,
            "risky_feedback_factor" => risky_feedback_factor,
            "last_depot_penalty" => last_penalty,
            "last_overload_bucket_count" => last_overloads,
            "bucket_risk_signal" => bucket_risk_signal,
            "bucket_pressure_score" => bucket_pressure_score,
            "pressure_mode" => last_pressure_mode,
            "lambda_gate" => lambda_gate,
            "lambda_picking" => lambda_picking,
            "lambda_staging" => lambda_staging,
            "lambda_scale" => lambda_scale,
            "dynamic_lambda_gate" => dynamic_lambda_gate,
            "dynamic_lambda_picking" => dynamic_lambda_picking,
            "dynamic_lambda_staging" => dynamic_lambda_staging,
        ),
    )
end
