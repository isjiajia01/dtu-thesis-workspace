using Pkg
Pkg.activate(joinpath(@__DIR__, ".."))
Pkg.instantiate()

using FreshSolver

function build_or_v5_2_config()
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
            shadow_price_feedback=true,
            shadow_price_weight=1.6,
            controller_bucket_feedback_weight=1.2,
            late_bucket_start_min=810,
            trip2_late_bias_weight=4.5,
            heavy_late_bias_weight=1.5,
            staging_risk_bias_weight=1.0,
            protect_near_deadline_bias_relief=5.5,
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
    benchmark = length(args) >= 1 ? args[1] : joinpath(thesis_root, "data", "processed", "benchmarks", "multiday_benchmark_herlev.json")
    matrix_dir = length(args) >= 2 ? args[2] : joinpath(thesis_root, "data", "processed", "matrices", "vrp_matrix_latest")
    output_path = length(args) >= 3 ? args[3] : joinpath(thesis_root, "results", "raw_runs", "herlev_multiday_or_v5_2_julia.json")

    config = build_or_v5_2_config()
    payload = run_multiday(benchmark, matrix_dir, output_path; config=config)
    println("Wrote result to: " * output_path)
    println("Unique assigned orders: " * string(payload.unique_assigned_orders))
    println("Service rate: " * string(payload.service_rate))
    println("Final carryover orders: " * string(payload.final_carryover_orders))
end

main(ARGS)
