using Pkg
Pkg.activate(joinpath(@__DIR__, ".."))
Pkg.instantiate()

using FreshSolver

function main(args)
    thesis_root = normpath(joinpath(@__DIR__, "..", "..", "..", "..", ".."))
    benchmark = length(args) >= 1 ? args[1] : joinpath(thesis_root, "data", "processed", "benchmarks", "multiday_benchmark_herlev.json")
    matrix_dir = length(args) >= 2 ? args[2] : joinpath(thesis_root, "data", "processed", "matrices", "vrp_matrix_latest")
    output_path = length(args) >= 3 ? args[3] : joinpath(thesis_root, "results", "raw_runs", "herlev_single_day_baseline_julia.json")

    payload = run_single_day(benchmark, matrix_dir, output_path)
    println("Wrote result to: " * output_path)
    println("Assigned orders: " * string(payload.summary.assigned_orders))
    println("Deferred orders: " * string(payload.summary.deferred_orders))
    println("Depot penalty: " * string(payload.summary.depot_penalty))
end

main(ARGS)
