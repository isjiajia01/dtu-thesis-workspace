using Dates

Base.@kwdef struct Order
    id::String
    original_id::String
    depot_id::String
    requested_date::Date
    service_date_from::Date
    service_date_to::Date
    feasible_dates::Vector{Date}
    time_window_start_min::Int
    time_window_end_min::Int
    colli::Float64
    volume::Float64
    weight::Float64
    service_time_min::Float64
    picking_task_time_min::Float64
    lat::Float64
    lon::Float64
    node_id::Int
end

Base.@kwdef struct Warehouse
    depot_id::String
    lat::Float64
    lon::Float64
    node_id::Int
    opening_min::Int
    closing_min::Int
    picking_open_min::Int
    picking_close_min::Int
    gates::Int
    loading_time_min::Int
    unloading_time_min::Int
    max_staging_volume::Float64
    picking_capacity_colli_per_hour::Float64
    picking_capacity_volume_per_hour::Float64
end

Base.@kwdef struct VehicleType
    type_name::String
    depot_id::String
    count::Int
    capacity_colli::Float64
    capacity_volume::Float64
    capacity_weight::Float64
    max_duration_min::Float64
    max_distance_km::Float64
    max_trips_per_day::Int = 2
end

Base.@kwdef struct MatrixRef
    matrix_dir::String
    n_nodes::Int
    durations_sec::Vector{Int32}
    distances_m::Vector{Int32}
end

Base.@kwdef struct Instance
    name::String
    start_date::Date
    end_date::Date
    depot_id::String
    orders::Vector{Order}
    warehouse::Warehouse
    vehicle_types::Vector{VehicleType}
    matrix_ref::MatrixRef
end

Base.@kwdef struct ControllerConfig
    urgency_weight::Float64 = 5.0
    age_weight::Float64 = 1.0
    risk_weight::Float64 = 2.0
    commitment_weight::Float64 = 2.0
    protected_reserve_ratio::Float64 = 0.20
    hard_protected_ratio::Float64 = 0.40
    flex_admission_cap_ratio::Float64 = 0.90
    risky_flex_cap_ratio::Float64 = 0.25
    late_window_threshold_min::Int = 840
    heavy_volume_threshold::Float64 = 1.4
    heavy_weight_threshold::Float64 = 260.0
    risk_clip_penalty::Float64 = 3.0
    depot_penalty_feedback_threshold::Float64 = 3000.0
    overload_feedback_threshold::Int = 8
    severe_depot_penalty_feedback_threshold::Float64 = 4500.0
    severe_overload_feedback_threshold::Int = 12
    feedback_clip_step::Float64 = 0.10
    feedback_risky_clip_step::Float64 = 0.10
    severe_feedback_clip_step::Float64 = 0.20
    severe_feedback_risky_clip_step::Float64 = 0.20
    dynamic_shadow_price_controller::Bool = false
    controller_shadow_price_weight::Float64 = 0.35
    controller_shadow_price_flex_only::Bool = true
end

Base.@kwdef struct RoutingConfig
    max_orders_per_route::Int = 8
    depot_proxy_penalty::Float64 = 2.0
    trip2_penalty::Float64 = 10.0
    depot_service_buffer_min::Float64 = 5.0
    protected_seed_count::Int = 12
    regret_k::Int = 2
    local_improvement_budget::Int = 200
    split_tail_budget::Int = 20
    refill_budget::Int = 50
    split_service_gain_weight::Float64 = 1.5
    split_depot_gain_weight::Float64 = 0.004
    split_protected_gain_weight::Float64 = 2.5
    split_extra_cost_weight::Float64 = 0.03
    refill_service_gain_weight::Float64 = 1.25
    refill_depot_gain_weight::Float64 = 0.003
    refill_protected_gain_weight::Float64 = 3.0
    refill_safe_bonus_weight::Float64 = 1.0
    refill_choice_penalty_weight::Float64 = 0.03
    severe_bucket_veto::Bool = false
    severe_bucket_penalty_threshold::Float64 = 600.0
    refill_worst_bucket_veto::Bool = false
    refill_worst_bucket_growth_tolerance::Float64 = 0.0
    bucket_aware_insertion_bias::Bool = false
    targeted_insertion_bias::Bool = false
    late_bucket_start_min::Int = 840
    trip2_late_bias_weight::Float64 = 6.0
    heavy_late_bias_weight::Float64 = 4.0
    staging_risk_bias_weight::Float64 = 3.0
    protect_near_deadline_bias_relief::Float64 = 4.0
    controller_bucket_feedback_bias::Bool = false
    controller_bucket_feedback_weight::Float64 = 2.5
    controller_bucket_feedback_fine_grained::Bool = false
    controller_feedback_target_trip2_late_only::Bool = false
    pressure_mode_pattern_feedback::Bool = false
    shadow_price_feedback::Bool = false
    shadow_price_weight::Float64 = 1.0
    normalized_shadow_price::Bool = false
    regime_aware_normalization::Bool = false
    dynamic_shadow_price_v8::Bool = false
    shadow_price_activation_utilization::Float64 = 0.80
    shadow_price_convex_gamma::Float64 = 2.0
    shadow_price_peak_eta::Float64 = 3.0
    alpha_gate::Float64 = 0.8
    alpha_picking::Float64 = 1.4
    alpha_staging::Float64 = 0.6
    beta_gate::Float64 = 1.2
    beta_picking::Float64 = 2.2
    beta_staging::Float64 = 0.8
    service_shield_feedback::Bool = false
    structured_service_shield::Bool = false
    service_shield_relief_weight::Float64 = 1.5
    truck_seed_volume_threshold::Float64 = 1.4
    truck_seed_weight_threshold::Float64 = 260.0
    truck_bonus_heavy::Float64 = 4.0
    lift_bonus_light::Float64 = 1.5
end

Base.@kwdef struct RepairConfig
    bucket_minutes::Int = 15
    gate_penalty_weight::Float64 = 100.0
    picking_colli_penalty_weight::Float64 = 4.0
    picking_volume_penalty_weight::Float64 = 8.0
    staging_penalty_weight::Float64 = 6.0
    reassignment_budget::Int = 12
    rollback_budget::Int = 8
end

Base.@kwdef struct SolverConfig
    controller::ControllerConfig = ControllerConfig()
    routing::RoutingConfig = RoutingConfig()
    repair::RepairConfig = RepairConfig()
end

Base.@kwdef mutable struct DayState
    planning_date::Date
    open_order_ids::Vector{String}
    committed_order_ids::Vector{String} = String[]
    metadata::Dict{String,Any} = Dict{String,Any}()
end

Base.@kwdef struct OrderScore
    order_id::String
    total_score::Float64
    urgency_score::Float64
    age_score::Float64
    risk_score::Float64
    commitment_score::Float64
    tags::Vector{String}
end

Base.@kwdef struct ControllerDecision
    planning_date::Date
    protected_order_ids::Vector{String}
    admitted_flex_order_ids::Vector{String}
    deferred_order_ids::Vector{String}
    order_scores::Dict{String,OrderScore}
    metadata::Dict{String,Any} = Dict{String,Any}()
end

Base.@kwdef struct RouteStop
    order_id::String
    arrival_min::Int
    service_start_min::Int
    departure_min::Int
end

Base.@kwdef mutable struct Route
    route_id::String
    depot_id::String
    vehicle_type_name::String
    vehicle_index::Int
    trip_index::Int
    ready_min::Int
    departure_min::Int
    return_min::Int
    order_ids::Vector{String}
    stops::Vector{RouteStop}
    total_distance_km::Float64
    total_duration_min::Float64
    total_colli::Float64
    total_volume::Float64
    total_weight::Float64
end

Base.@kwdef struct UnassignedOrder
    order_id::String
    reason::String
end

Base.@kwdef struct RoutingSolution
    planning_date::Date
    routes::Vector{Route}
    unassigned::Vector{UnassignedOrder}
end

Base.@kwdef struct DepotBucketUsage
    bucket_start_min::Int
    departures::Int
    picking_colli::Float64
    picking_volume::Float64
    staging_volume::Float64
    gate_over::Int
    picking_colli_over::Float64
    picking_volume_over::Float64
    staging_over::Float64
    bucket_penalty::Float64
end

Base.@kwdef struct DepotDiagnostics
    planning_date::Date
    depot_penalty::Float64
    overload_bucket_count::Int
    worst_bucket_penalty::Float64
    bucket_usage::Vector{DepotBucketUsage}
end

Base.@kwdef struct RepairResult
    planning_date::Date
    repaired_solution::RoutingSolution
    diagnostics::DepotDiagnostics
end

Base.@kwdef struct RunSummary
    instance_name::String
    planning_date::Date
    assigned_orders::Int
    unassigned_orders::Int
    deferred_orders::Int
    route_count::Int
    trip2_route_count::Int
    total_distance_km::Float64
    total_duration_min::Float64
    depot_penalty::Float64
    overload_bucket_count::Int
    runtime_seconds::Float64
end

function build_initial_day_state(planning_date::Date, open_order_ids::Vector{String})
    DayState(planning_date=planning_date, open_order_ids=open_order_ids)
end

@inline function matrix_offset(matrix_ref::MatrixRef, from_node::Int, to_node::Int)
    return from_node * matrix_ref.n_nodes + to_node + 1
end

@inline function matrix_duration_min(matrix_ref::MatrixRef, from_node::Int, to_node::Int)
    return Float64(matrix_ref.durations_sec[matrix_offset(matrix_ref, from_node, to_node)]) / 60.0
end

@inline function matrix_distance_km(matrix_ref::MatrixRef, from_node::Int, to_node::Int)
    return Float64(matrix_ref.distances_m[matrix_offset(matrix_ref, from_node, to_node)]) / 1000.0
end
