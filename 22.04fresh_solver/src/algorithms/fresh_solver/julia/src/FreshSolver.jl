module FreshSolver

using Dates
using JSON3

include("types.jl")
include("io.jl")
include("controller.jl")
include("routing.jl")
include("repair.jl")
include("evaluation.jl")
include("runner.jl")

export SolverConfig,
       load_instance,
       build_initial_day_state,
       make_controller_decision,
       build_routes_for_day,
       evaluate_depot_profile,
       repair_solution,
       summarize_run,
       run_single_day,
       run_multiday

end
