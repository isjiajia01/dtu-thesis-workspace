using Pkg
Pkg.activate(joinpath(@__DIR__, ".."))
Pkg.instantiate()

using FreshSolver

function build_stricter_realism_config()
    return FreshSolver.SolverConfig(
        controller=FreshSolver.ControllerConfig(
            protected_reserve_ratio=0.28,
            hard_protected_ratio=0.55,
            flex_admission_cap_ratio=0.72,
            risky_flex_cap_ratio=0.12,
            risk_clip_penalty=4.5,
            depot_penalty_feedback_threshold=1500.0,
            overload_feedback_threshold=4,
            severe_depot_penalty_feedback_threshold=2500.0,
            severe_overload_feedback_threshold=7,
            feedback_clip_step=0.20,
            feedback_risky_clip_step=0.20,
            severe_feedback_clip_step=0.35,
            severe_feedback_risky_clip_step=0.35,
        ),
        routing=FreshSolver.RoutingConfig(
            max_orders_per_route=6,
            depot_proxy_penalty=4.0,
            trip2_penalty=18.0,
            depot_service_buffer_min=12.0,
            protected_seed_count=10,
            regret_k=2,
            local_improvement_budget=80,
            split_tail_budget=8,
            refill_budget=16,
            split_service_gain_weight=1.1,
            split_depot_gain_weight=0.010,
            split_protected_gain_weight=2.8,
            split_extra_cost_weight=0.05,
            refill_service_gain_weight=1.0,
            refill_depot_gain_weight=0.008,
            refill_protected_gain_weight=3.2,
            refill_safe_bonus_weight=1.8,
            refill_choice_penalty_weight=0.06,
        ),
        repair=FreshSolver.RepairConfig(
            gate_penalty_weight=180.0,
            picking_colli_penalty_weight=10.0,
            picking_volume_penalty_weight=16.0,
            staging_penalty_weight=14.0,
            reassignment_budget=6,
            rollback_budget=10,
        ),
    )
end

function main(args)
    thesis_root = normpath(joinpath(@__DIR__, "..", "..", "..", "..", ".."))
    benchmark = length(args) >= 1 ? args[1] : joinpath(thesis_root, "data", "processed", "benchmarks", "multiday_benchmark_herlev.json")
    matrix_dir = length(args) >= 2 ? args[2] : joinpath(thesis_root, "data", "processed", "matrices", "vrp_matrix_latest")
    output_path = length(args) >= 3 ? args[3] : joinpath(thesis_root, "results", "raw_runs", "herlev_multiday_strict_julia.json")

    config = build_stricter_realism_config()
    payload = run_multiday(benchmark, matrix_dir, output_path; config=config)
    println("Wrote result to: " * output_path)
    println("Unique assigned orders: " * string(payload.unique_assigned_orders))
    println("Service rate: " * string(payload.service_rate))
    println("Final carryover orders: " * string(payload.final_carryover_orders))
end

main(ARGS)
