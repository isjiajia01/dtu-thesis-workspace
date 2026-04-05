using Pkg
Pkg.activate(joinpath(@__DIR__, ".."))
Pkg.instantiate()

using FreshSolver

function build_or_v8_2_config()
    return FreshSolver.SolverConfig(
        controller=FreshSolver.ControllerConfig(
            protected_reserve_ratio=0.22,
            hard_protected_ratio=0.48,
            flex_admission_cap_ratio=0.86,
            risky_flex_cap_ratio=0.20,
            risk_clip_penalty=3.6,
            depot_penalty_feedback_threshold=1500.0,
            overload_feedback_threshold=4,
            severe_depot_penalty_feedback_threshold=2400.0,
            severe_overload_feedback_threshold=7,
            feedback_clip_step=0.14,
            feedback_risky_clip_step=0.16,
            severe_feedback_clip_step=0.22,
            severe_feedback_risky_clip_step=0.26,
            dynamic_shadow_price_controller=true,
            controller_shadow_price_weight=0.20,
            controller_shadow_price_flex_only=true,
        ),
        routing=FreshSolver.RoutingConfig(
            max_orders_per_route=7,
            depot_proxy_penalty=3.1,
            trip2_penalty=14.0,
            depot_service_buffer_min=9.0,
            protected_seed_count=10,
            regret_k=2,
            local_improvement_budget=120,
            split_tail_budget=10,
            refill_budget=24,
            split_service_gain_weight=1.35,
            split_depot_gain_weight=0.007,
            split_protected_gain_weight=2.8,
            split_extra_cost_weight=0.040,
            refill_service_gain_weight=1.15,
            refill_depot_gain_weight=0.005,
            refill_protected_gain_weight=3.0,
            refill_safe_bonus_weight=1.6,
            refill_choice_penalty_weight=0.045,
            severe_bucket_veto=true,
            severe_bucket_penalty_threshold=700.0,
            refill_worst_bucket_veto=true,
            refill_worst_bucket_growth_tolerance=35.0,
            bucket_aware_insertion_bias=true,
            targeted_insertion_bias=true,
            controller_bucket_feedback_bias=true,
            controller_bucket_feedback_fine_grained=true,
            pressure_mode_pattern_feedback=true,
            controller_bucket_feedback_weight=1.0,
            late_bucket_start_min=810,
            trip2_late_bias_weight=3.8,
            heavy_late_bias_weight=1.1,
            staging_risk_bias_weight=0.6,
            protect_near_deadline_bias_relief=6.0,
            shadow_price_feedback=true,
            shadow_price_weight=0.10,
            normalized_shadow_price=true,
            regime_aware_normalization=true,
            dynamic_shadow_price_v8=true,
            shadow_price_activation_utilization=0.84,
            shadow_price_convex_gamma=1.7,
            shadow_price_peak_eta=2.2,
            alpha_gate=0.5,
            alpha_picking=1.35,
            alpha_staging=0.25,
            beta_gate=0.7,
            beta_picking=1.1,
            beta_staging=0.25,
            service_shield_feedback=true,
            structured_service_shield=true,
            service_shield_relief_weight=2.1,
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

function main(args)
    thesis_root = normpath(joinpath(@__DIR__, "..", "..", "..", "..", ".."))
    benchmark = length(args) >= 1 ? args[1] : joinpath(thesis_root, "data", "processed", "benchmarks", "multiday_benchmark_west.json")
    matrix_dir = length(args) >= 2 ? args[2] : joinpath(thesis_root, "data", "processed", "matrices", "vrp_matrix_west")
    output_path = length(args) >= 3 ? args[3] : joinpath(thesis_root, "results", "raw_runs", "west_multiday_or_v8_2_julia.json")

    config = build_or_v8_2_config()
    payload = run_multiday(benchmark, matrix_dir, output_path; config=config)
    println("Wrote result to: " * output_path)
    println("Unique assigned orders: " * string(payload.unique_assigned_orders))
    println("Service rate: " * string(payload.service_rate))
    println("Final carryover orders: " * string(payload.final_carryover_orders))
end

main(ARGS)
