using Pkg
Pkg.activate(joinpath(@__DIR__, ".."))
Pkg.instantiate()

using FreshSolver

function main(args)
    thesis_root = normpath(joinpath(@__DIR__, "..", "..", "..", "..", ".."))
    benchmark = length(args) >= 1 ? args[1] : joinpath(thesis_root, "data", "processed", "benchmarks", "multiday_benchmark_herlev.json")
    matrix_dir = length(args) >= 2 ? args[2] : joinpath(thesis_root, "data", "processed", "matrices", "vrp_matrix_latest")
    output_path = length(args) >= 3 ? args[3] : joinpath(thesis_root, "results", "raw_runs", "herlev_multiday_baseline_julia.json")

    payload = run_multiday(benchmark, matrix_dir, output_path)
    println("Wrote result to: " * output_path)
    println("Unique assigned orders: " * string(payload.unique_assigned_orders))
    println("Service rate: " * string(payload.service_rate))
    println("Final carryover orders: " * string(payload.final_carryover_orders))
end

main(ARGS)
