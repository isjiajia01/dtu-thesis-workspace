using Dates
using JSON3

parse_date(s) = Date(String(s))

function load_nodes_map(matrix_dir::AbstractString)
    nodes_path = joinpath(matrix_dir, "nodes.csv")
    lines = readlines(nodes_path)
    order_to_node = Dict{String,Int}()
    depot_node_id = 0
    for line in lines[2:end]
        isempty(line) && continue
        cols = split(line, ',')
        node_id = parse(Int, cols[1])
        kind = cols[2]
        order_id = cols[3]
        if kind == "depot"
            depot_node_id = node_id
        elseif kind == "order"
            order_to_node[order_id] = node_id
        end
    end
    return depot_node_id, order_to_node
end

function load_matrix_ref(matrix_dir::AbstractString)
    index_raw = JSON3.read(read(joinpath(matrix_dir, "index.json"), String))
    n_nodes = Int(index_raw.n_nodes)
    durations_sec = read(joinpath(matrix_dir, String(index_raw.durations_bin)))
    distances_m = read(joinpath(matrix_dir, String(index_raw.distances_bin)))
    duration_vec = reinterpret(Int32, durations_sec)
    distance_vec = reinterpret(Int32, distances_m)
    return MatrixRef(
        matrix_dir=String(matrix_dir),
        n_nodes=n_nodes,
        durations_sec=copy(duration_vec),
        distances_m=copy(distance_vec),
    )
end

function load_instance(benchmark_path::AbstractString, matrix_dir::AbstractString)
    raw = JSON3.read(read(benchmark_path, String))
    metadata = raw.metadata
    depot = raw.depot
    vehicles_raw = raw.vehicles
    orders_raw = raw.orders

    matrix_ref = load_matrix_ref(matrix_dir)
    depot_node_id, order_to_node = load_nodes_map(matrix_dir)

    depot_id = String(metadata.depot_name)
    warehouse = Warehouse(
        depot_id=depot_id,
        lat=Float64(depot.location[1]),
        lon=Float64(depot.location[2]),
        node_id=depot_node_id,
        opening_min=Int(depot.opening_time),
        closing_min=Int(depot.closing_time),
        picking_open_min=Int(depot.picking_open_min),
        picking_close_min=Int(depot.picking_close_min),
        gates=Int(depot.gates),
        loading_time_min=Int(depot.loading_time_minutes),
        unloading_time_min=Int(depot.unloading_time_minutes),
        max_staging_volume=Float64(depot.picking_capacity.max_staging_volume),
        picking_capacity_colli_per_hour=Float64(depot.picking_capacity.colli_per_hour),
        picking_capacity_volume_per_hour=Float64(depot.picking_capacity.volume_per_hour),
    )

    vehicle_types = VehicleType[
        VehicleType(
            type_name=String(v.type_name),
            depot_id=String(v.depot),
            count=Int(v.count),
            capacity_colli=Float64(v.capacity.colli),
            capacity_volume=Float64(v.capacity.volume),
            capacity_weight=Float64(v.capacity.weight),
            max_duration_min=60.0 * Float64(v.max_duration_hours),
            max_distance_km=Float64(v.max_distance_km),
        )
        for v in vehicles_raw
    ]

    orders = Order[]
    for o in orders_raw
        feasible_dates = Date[parse_date(d) for d in o.feasible_dates]
        order_id = string(o.id)
        push!(orders, Order(
            id=order_id,
            original_id=string(o.original_id),
            depot_id=depot_id,
            requested_date=parse_date(o.release_date),
            service_date_from=first(feasible_dates),
            service_date_to=last(feasible_dates),
            feasible_dates=feasible_dates,
            time_window_start_min=Int(o.time_window[1]),
            time_window_end_min=Int(o.time_window[2]),
            colli=Float64(o.demand.colli),
            volume=Float64(o.demand.volume),
            weight=Float64(o.demand.weight),
            service_time_min=Float64(o.service_time),
            picking_task_time_min=haskey(o, :picking_task_time) ? Float64(o.picking_task_time) : 0.0,
            lat=Float64(o.location[1]),
            lon=Float64(o.location[2]),
            node_id=get(order_to_node, order_id, -1),
        ))
    end

    return Instance(
        name=splitext(basename(benchmark_path))[1],
        start_date=parse_date(metadata.horizon_start),
        end_date=parse_date(metadata.horizon_end),
        depot_id=depot_id,
        orders=orders,
        warehouse=warehouse,
        vehicle_types=vehicle_types,
        matrix_ref=matrix_ref,
    )
end
