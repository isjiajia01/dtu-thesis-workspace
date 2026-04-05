using Pkg
Pkg.activate(joinpath(@__DIR__, ".."))
Pkg.instantiate()

using FreshSolver

function build_large_instance_fast_config()
    return FreshSolver.SolverConfig(
        controller=FreshSolver.ControllerConfig(
            flex_admission_cap_ratio=0.80,
            risky_flex_cap_ratio=0.20,
            feedback_clip_step=0.15,
            feedback_risky_clip_step=0.15,
            severe_feedback_clip_step=0.25,
            severe_feedback_risky_clip_step=0.25,
        ),
        routing=FreshSolver.RoutingConfig(
            protected_seed_count=8,
            regret_k=2,
            local_improvement_budget=40,
            split_tail_budget=6,
            refill_budget=12,
            split_service_gain_weight=1.3,
            split_depot_gain_weight=0.004,
            split_protected_gain_weight=2.5,
            split_extra_cost_weight=0.03,
            refill_service_gain_weight=1.2,
            refill_depot_gain_weight=0.003,
            refill_protected_gain_weight=3.0,
            refill_safe_bonus_weight=1.0,
            refill_choice_penalty_weight=0.03,
        ),
        repair=FreshSolver.RepairConfig(
            reassignment_budget=4,
            rollback_budget=4,
        ),
    )
end

function main(args)
    thesis_root = normpath(joinpath(@__DIR__, "..", "..", "..", "..", ".."))
    benchmark = length(args) >= 1 ? args[1] : joinpath(thesis_root, "data", "processed", "benchmarks", "multiday_benchmark_east.json")
    matrix_dir = length(args) >= 2 ? args[2] : joinpath(thesis_root, "data", "processed", "matrices", "vrp_matrix_east")
    output_path = length(args) >= 3 ? args[3] : joinpath(thesis_root, "results", "raw_runs", "east_multiday_fast_julia.json")

    config = build_large_instance_fast_config()
    payload = run_multiday(benchmark, matrix_dir, output_path; config=config)
    println("Wrote result to: " * output_path)
    println("Unique assigned orders: " * string(payload.unique_assigned_orders))
    println("Service rate: " * string(payload.service_rate))
    println("Final carryover orders: " * string(payload.final_carryover_orders))
end

main(ARGS)
