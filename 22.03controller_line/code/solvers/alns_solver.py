import csv
import gc
import sys
import os
import json
import math
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# --- [Path Setup] ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)
PROJECT_ROOT = Path(project_root)

# Scaling factor for handling Volume/Weight decimals (converts floats to int)
SCALING_FACTOR = 1000

DEFAULT_MATRIX_DIR = PROJECT_ROOT / "data" / "processed" / "vrp_matrix_latest"
FIRST_SOLUTION_STRATEGIES = {
    "path_cheapest_arc": routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    "parallel_cheapest_insertion": routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
}

LOCAL_SEARCH_METAHEURISTICS = {
    "guided_local_search": routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    "greedy_descent": routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT,
}

DEPOT_MATRIX_DIRS = {
    "herlev": DEFAULT_MATRIX_DIR,
    "aalborg": PROJECT_ROOT / "data" / "processed" / "vrp_matrix_aalborg",
    "odense": PROJECT_ROOT / "data" / "processed" / "vrp_matrix_odense",
    "aabyhoj": PROJECT_ROOT / "data" / "processed" / "vrp_matrix_aabyhoj",
    "east": PROJECT_ROOT / "data" / "processed" / "vrp_matrix_east",
    "west": PROJECT_ROOT / "data" / "processed" / "vrp_matrix_west",
}


def _normalize_depot_key(value):
    text = str(value or "").strip().lower()
    return (
        text.replace("å", "a")
        .replace("ø", "o")
        .replace("æ", "ae")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )


def _matrix_file_path(matrix_dir: Path, relative_or_name: str) -> Path:
    candidate = matrix_dir / relative_or_name
    if candidate.exists():
        return candidate
    return matrix_dir / Path(relative_or_name).name


def _disable_stdio() -> None:
    try:
        devnull = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        return
    try:
        sys.stdout = devnull
    except Exception:
        pass
    try:
        sys.stderr = devnull
    except Exception:
        pass


def _safe_print(*values, sep: str = " ", end: str = "\n") -> None:
    stream = getattr(sys, "stdout", None) or sys.__stdout__
    if stream is None:
        return
    message = sep.join(str(value) for value in values) + end
    try:
        stream.write(message)
        stream.flush()
    except (BrokenPipeError, OSError, ValueError):
        _disable_stdio()


@lru_cache(maxsize=16)
def _load_osrm_matrix_assets(matrix_dir_str: str):
    matrix_dir = Path(matrix_dir_str)
    index = json.loads((matrix_dir / "index.json").read_text())
    matrix_size = int(index["n_nodes"])

    nodes_path = _matrix_file_path(matrix_dir, index.get("nodes_csv", "nodes.csv"))
    distances_path = _matrix_file_path(matrix_dir, index["distances_bin"])
    durations_path = _matrix_file_path(matrix_dir, index["durations_bin"])

    order_to_node = {}
    depot_node_id = None
    with nodes_path.open(newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            node_id = int(row["node_id"])
            if node_id >= matrix_size:
                continue
            kind = (row.get("kind") or "").strip().lower()
            if kind == "depot" and depot_node_id is None:
                depot_node_id = node_id
            if kind != "order":
                continue
            order_id = (row.get("order_id") or "").strip()
            if order_id:
                order_to_node[order_id] = node_id

    if depot_node_id is None:
        raise ValueError(f"OSRM matrix {matrix_dir} has no depot node in nodes.csv")

    distances = np.memmap(distances_path, dtype=np.int32, mode="r", shape=(matrix_size, matrix_size))
    durations = np.memmap(durations_path, dtype=np.int32, mode="r", shape=(matrix_size, matrix_size))

    return {
        "matrix_dir": matrix_dir,
        "index": index,
        "matrix_size": matrix_size,
        "depot_node_id": int(depot_node_id),
        "order_to_node": order_to_node,
        "distances": distances,
        "durations": durations,
    }


class RoutingGlsSolver:
    """
    OR-Tools ``RoutingModel`` solver with guided local search.

    ``ALNS_Solver`` is kept below as a compatibility alias because older
    22.03 entrypoints imported that name before the implementation was
    clarified.
    """

    def __init__(self, daily_data, current_date_str, config=None):
        self.data = daily_data
        self.current_date = datetime.strptime(current_date_str, "%Y-%m-%d")

        # Get Depot Name for vehicle filtering (matches File 1 generation)
        self.depot_name = self.data["depot"].get("name", None)

        # Default VRP Config
        default_config = {
            "base_penalty": 2000,
            "urgent_penalty": 1e7,
            "beta": 5.0,
            "epsilon": 0.1,
        }
        self.config = dict(default_config)
        if config:
            self.config.update(config)

        self.matrix_dir = self._resolve_matrix_dir()
        self.matrix_assets = _load_osrm_matrix_assets(str(self.matrix_dir))
        self._load_depot_constraints()

        # --- Step 1: Data Preparation ---
        self._flatten_vehicles()
        # Number of physical vehicles (one tour per solve; multi-trip handled via sequential solves)
        self._map_orders_to_nodes()
        self._compute_distance_matrix()

        # --- Step 2: Model Initialization ---
        self._init_routing_model()

        # --- Step 3: Inject Constraints & Callbacks ---
        self._register_transit_callback()
        self._register_time_callback()

        # Core: Multi-dimensional Loading Constraints (Colli, Volume, Weight)
        self._add_capacity_constraints()

        # Core: Max Distance Constraints
        self._add_distance_constraints()

        # Core: Time Windows & Multi-Wave Scheduling (Waves)
        self._add_time_window_constraints()

        self._add_penalties()
        # ----- solver run knobs (env overrides first) -----
        # VRP_TIME_LIMIT_SECONDS: int seconds for OR-Tools search.
        # VRP_MAX_TRIPS_PER_VEHICLE: max distinct trips per physical vehicle per day (1 or 2 recommended).
        # VRP_RELOAD_TIME_MINUTES: reload time between trips (defaults to depot loading_time_minutes).
        self.time_limit_seconds = int(self._get_time_limit_seconds())
        self.warehouse_filter_max_attempts = int(self._get_warehouse_filter_max_attempts())
        self.warehouse_retry_time_limit_seconds = int(self._get_warehouse_retry_time_limit_seconds())
        self.warehouse_drop_batch_size = int(self._get_warehouse_drop_batch_size())
        self.warehouse_retry_use_initial_routes = bool(self._get_warehouse_retry_use_initial_routes())
        self.memory_lean_mode = bool(self._get_memory_lean_mode())
        self.max_trips_per_vehicle = int(self._get_max_trips_per_vehicle())
        self.reload_time_minutes = int(self._get_reload_time_minutes())
        self.trip_id = int(self.config.get('trip_id', 1))
        self._solve_once_records = []

    def _resolve_matrix_dir(self) -> Path:
        metadata = self.data.get("metadata", {}) if isinstance(self.data, dict) else {}
        candidates = []

        for source in (self.config, metadata):
            for key in ("matrix_dir", "vrp_matrix_dir"):
                value = source.get(key)
                if value:
                    path = Path(str(value))
                    if not path.is_absolute():
                        path = PROJECT_ROOT / path
                    candidates.append(path)

        depot_key = _normalize_depot_key(
            self.data.get("depot", {}).get("name") or metadata.get("depot_name")
        )
        inferred = DEPOT_MATRIX_DIRS.get(depot_key)
        if inferred is not None:
            candidates.append(inferred)

        checked = []
        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            checked.append(str(candidate))
            if (candidate / "index.json").exists():
                return candidate

        raise FileNotFoundError(
            "OSRM matrix directory is required but was not found. "
            f"Checked: {checked or ['<none>']}. "
            "Set config['matrix_dir'] or metadata['matrix_dir'] to a valid matrix directory."
        )

    def _load_depot_constraints(self):
        """Load depot-side operational constraints from dataset/config."""
        depot = self.data.get("depot", {}) if isinstance(self.data, dict) else {}
        picking_cfg = depot.get("picking_capacity", {}) if isinstance(depot.get("picking_capacity", {}), dict) else {}

        self.bucket_minutes = int(self.config.get("bucket_minutes", depot.get("bucket_minutes", 15)))
        self.gate_limit = max(1, int(depot.get("gates", self.config.get("gates", 1))))
        self.loading_time_minutes = int(depot.get("loading_time_minutes", self.config.get("loading_time_minutes", 0)))
        self.unloading_time_minutes = int(depot.get("unloading_time_minutes", self.config.get("unloading_time_minutes", 0)))
        self.return_to_depot = bool(depot.get("return_to_depot", self.config.get("return_to_depot", True)))
        self.picking_open_min = int(depot.get("picking_open_min", self.config.get("picking_open_min", 0)))
        self.picking_close_min = int(depot.get("picking_close_min", self.config.get("picking_close_min", 1439)))
        self.picking_capacity_colli_per_hour = float(
            picking_cfg.get("colli_per_hour", self.config.get("picking_capacity_colli_per_hour", 0.0))
        )
        self.picking_capacity_volume_per_hour = float(
            picking_cfg.get("volume_per_hour", self.config.get("picking_capacity_volume_per_hour", 0.0))
        )
        self.max_staging_volume = float(
            picking_cfg.get("max_staging_volume", self.config.get("max_staging_volume", 0.0))
        )


    def _get_time_limit_seconds(self) -> int:
        """Read VRP time limit from env/config (default: 20s)."""
        env = os.environ.get("VRP_TIME_LIMIT_SECONDS", None)
        if env is not None:
            try:
                return int(env)
            except Exception:
                pass
        try:
            return int(self.config.get("time_limit_seconds", 20))
        except Exception:
            return 20

    def _get_warehouse_filter_max_attempts(self) -> int:
        env = os.environ.get("VRP_WAREHOUSE_FILTER_MAX_ATTEMPTS", None)
        if env is not None:
            try:
                return max(0, int(env))
            except Exception:
                pass
        try:
            return max(0, int(self.config.get("warehouse_filter_max_attempts", 25)))
        except Exception:
            return 25

    def _get_warehouse_retry_time_limit_seconds(self) -> int:
        env = os.environ.get("VRP_WAREHOUSE_RETRY_TIME_LIMIT_SECONDS", None)
        if env is not None:
            try:
                return max(1, int(env))
            except Exception:
                pass
        try:
            default_retry = max(1, int(self._get_time_limit_seconds()))
            return max(1, int(self.config.get("warehouse_retry_time_limit_seconds", default_retry)))
        except Exception:
            return max(1, int(self._get_time_limit_seconds()))

    def _get_warehouse_drop_batch_size(self) -> int:
        env = os.environ.get("VRP_WAREHOUSE_DROP_BATCH_SIZE", None)
        if env is not None:
            try:
                return max(1, int(env))
            except Exception:
                pass
        try:
            return max(1, int(self.config.get("warehouse_drop_batch_size", 1)))
        except Exception:
            return 1

    def _get_warehouse_retry_use_initial_routes(self) -> bool:
        env = os.environ.get("VRP_WAREHOUSE_RETRY_USE_INITIAL_ROUTES", None)
        if env is not None:
            return str(env).strip().lower() in {"1", "true", "yes", "on"}
        return bool(self.config.get("warehouse_retry_use_initial_routes", True))

    def _get_first_solution_strategy(self) -> str:
        env = os.environ.get("VRP_FIRST_SOLUTION_STRATEGY", None)
        if env:
            return str(env).strip().lower()
        value = self.config.get("first_solution_strategy", "path_cheapest_arc")
        return str(value).strip().lower()

    def _get_local_search_metaheuristic(self) -> str:
        env = os.environ.get("VRP_LOCAL_SEARCH_METAHEURISTIC", None)
        if env:
            return str(env).strip().lower()
        value = self.config.get("local_search_metaheuristic", "guided_local_search")
        return str(value).strip().lower()

    def _get_max_trips_per_vehicle(self) -> int:
        env = os.environ.get("VRP_MAX_TRIPS_PER_VEHICLE", None)
        if env is not None:
            try:
                return max(1, int(env))
            except Exception:
                pass
        try:
            return max(1, int(self.config.get("max_trips_per_vehicle", 2)))  # Default to 2 trips
        except Exception:
            return 1

    def _get_solver_chunk_seconds(self) -> int:
        env = os.environ.get("VRP_SOLVER_CHUNK_SECONDS", None)
        if env is not None:
            try:
                return max(1, int(env))
            except Exception:
                pass
        try:
            return max(1, int(self.config.get("solver_chunk_seconds", self._get_time_limit_seconds())))
        except Exception:
            return max(1, int(self._get_time_limit_seconds()))

    def _get_solver_min_chunks(self) -> int:
        env = os.environ.get("VRP_SOLVER_MIN_CHUNKS", None)
        if env is not None:
            try:
                return max(1, int(env))
            except Exception:
                pass
        try:
            return max(1, int(self.config.get("solver_min_chunks", 1)))
        except Exception:
            return 1

    def _get_solver_max_no_improve_chunks(self) -> int:
        env = os.environ.get("VRP_SOLVER_MAX_NO_IMPROVE_CHUNKS", None)
        if env is not None:
            try:
                return max(0, int(env))
            except Exception:
                pass
        try:
            return max(0, int(self.config.get("solver_max_no_improve_chunks", 0)))
        except Exception:
            return 0

    def _get_solver_continue_improvement_ratio(self) -> float:
        env = os.environ.get("VRP_SOLVER_CONTINUE_IMPROVEMENT_RATIO", None)
        if env is not None:
            try:
                return max(0.0, float(env))
            except Exception:
                pass
        try:
            return max(0.0, float(self.config.get("solver_continue_improvement_ratio", 0.0)))
        except Exception:
            return 0.0

    def _get_solver_enable_incumbent_continuation(self) -> bool:
        env = os.environ.get("VRP_SOLVER_ENABLE_INCUMBENT_CONTINUATION", None)
        if env is not None:
            return str(env).strip().lower() in {"1", "true", "yes", "on"}
        return bool(self.config.get("solver_enable_incumbent_continuation", False))

    def _get_solver_enable_initial_route_seed(self) -> bool:
        env = os.environ.get("VRP_SOLVER_ENABLE_INITIAL_ROUTE_SEED", None)
        if env is not None:
            return str(env).strip().lower() in {"1", "true", "yes", "on"}
        if "solver_enable_initial_route_seed" in self.config:
            return bool(self.config.get("solver_enable_initial_route_seed", False))
        env_prev = os.environ.get("VRP_SOLVER_ENABLE_PREV_DAY_ROUTE_SEED", None)
        if env_prev is not None:
            return str(env_prev).strip().lower() in {"1", "true", "yes", "on"}
        return bool(self.config.get("solver_enable_prev_day_route_seed", False))

    def _get_memory_lean_mode(self) -> bool:
        env = os.environ.get("VRP_MEMORY_LEAN_MODE", None)
        if env is not None:
            return str(env).strip().lower() in {"1", "true", "yes", "on"}
        return bool(self.config.get("memory_lean_mode", False))

    def _get_reload_time_minutes(self) -> int:
        env = os.environ.get("VRP_RELOAD_TIME_MINUTES", None)
        if env is not None:
            try:
                return max(0, int(env))
            except Exception:
                pass
        try:
            default_turnaround = self.unloading_time_minutes + self.loading_time_minutes
            return int(self.config.get("reload_time_minutes", default_turnaround))
        except Exception:
            return int(self.unloading_time_minutes + self.loading_time_minutes)

    def _compute_default_vehicle_start_times(self, active_vehicles: int = None):
        if active_vehicles is None:
            active_vehicles = int(getattr(self, 'num_vehicles', 0) or 0)
        """Default vehicle start times at the depot.

        Ops semantics:
          - depot time_window end is interpreted as *latest departure from depot* (not return cut-off)
          - if picking is preloaded (overnight picking), vehicles can all depart at depot_open with no lane staggering
        """
        depot_open_time = int(self.time_windows[0][0]) if self.time_windows and self.time_windows[0] else 0
        depot_last_departure = int(self.time_windows[0][1]) if self.time_windows and self.time_windows[0] else (depot_open_time + 600)

        picking_preloaded = bool(getattr(self, "picking_preloaded", self.config.get("picking_preloaded", True)))
        if picking_preloaded:
            shift_delay_min = 0
        else:
            depot = self.data.get("depot", {}) if isinstance(self.data, dict) else {}
            num_lanes = int(depot.get("num_lanes", depot.get("gates", 1)))
            picking_speed = float(depot.get("picking_speed_colli_per_min", 2.0))
            estimated_load_per_vehicle = float(depot.get("estimated_load_per_vehicle_colli", 50.0))
            depot_service_total_min = estimated_load_per_vehicle / max(1e-9, picking_speed)
            shift_delay_min = max(0, int(round(depot_service_total_min / max(1, num_lanes))))

        starts = []
        for i in range(int(active_vehicles)):
            s = depot_open_time + i * shift_delay_min
            s = min(s, depot_last_departure)  # never depart after latest allowed departure
            starts.append(int(s))
        return self._apply_gate_release_schedule(starts)

    def _bucketize(self, minute_of_day):
        return int(minute_of_day) // max(1, int(self.bucket_minutes))

    def _apply_gate_release_schedule(self, proposed_starts):
        """Assign each trip start to a gate-feasible departure bucket."""
        if not proposed_starts:
            return []

        latest_departure = int(getattr(self, "depot_last_departure", self.time_windows[0][1] if self.time_windows else 0))
        bucket_size = max(1, int(self.bucket_minutes))
        bucket_loads = defaultdict(int)
        scheduled = []

        indexed_starts = sorted(enumerate(proposed_starts), key=lambda item: (int(item[1]), item[0]))
        tmp = [0] * len(proposed_starts)

        for idx, proposed in indexed_starts:
            start = max(int(proposed), self.depot_open_time)
            bucket = self._bucketize(start)
            while bucket_loads[bucket] >= self.gate_limit:
                bucket += 1
            start_bucket_min = bucket * bucket_size
            if start_bucket_min > latest_departure:
                start_bucket_min = latest_departure
                bucket = self._bucketize(start_bucket_min)
            bucket_loads[bucket] += 1
            tmp[idx] = int(start_bucket_min)

        scheduled.extend(tmp)
        return scheduled

    def _flatten_vehicles(self):
        """
        Flatten vehicle pool from type-counts to individual vehicle instances.
        Note: The Solver trusts the 'count' passed by the Simulation,
        which has already applied availability logic.
        """
        self.vehicle_flat_list = []
        self.vehicle_capacities = {"colli": [], "volume": [], "weight": []}

        target_depot = self.depot_name

        for v_type in self.data["vehicles"]:
            # 1. Depot Match Check (Crucial for Multi-Depot datasets)
            if target_depot is not None and "depot" in v_type and v_type["depot"] != target_depot:
                continue

            # 2. Read Config
            count = int(v_type["count"])
            if count <= 0:
                continue

            cap = v_type["capacity"]

            # 3. Flatten each vehicle instance
            for _ in range(count):
                self.vehicle_flat_list.append(
                    {
                        "type": v_type["type_name"],
                        "max_distance": v_type.get("max_distance_km", 3000),  # Default fallback
                        "max_duration": int(v_type.get("max_duration_hours", 10) * 60),
                    }
                )
                # Inject Capacities (Note Scaling for Volume/Weight)
                self.vehicle_capacities["colli"].append(int(cap["colli"]))
                self.vehicle_capacities["volume"].append(int(cap["volume"] * SCALING_FACTOR))
                self.vehicle_capacities["weight"].append(int(cap["weight"] * SCALING_FACTOR))

        self.num_vehicles = len(self.vehicle_flat_list)
        # How many of the (flat) vehicles are actually available (for fleet-ablation experiments).
        self.active_vehicles = int(self.config.get('active_vehicles', self.num_vehicles))
        self.active_vehicles = max(0, min(self.active_vehicles, self.num_vehicles))

        # Per-vehicle max duration (minutes). Used by time window constraints, and by multi-trip rollovers.
        self.vehicle_max_durations = [int(v.get('max_duration', 0)) for v in self.vehicle_flat_list]


    def _map_orders_to_nodes(self):
        """Map orders to OR-Tools nodes (Node 0 is Depot)"""
        self.orders = self.data["orders"]
        self.num_orders = len(self.orders)
        self.num_nodes = self.num_orders + 1
        self.depot_loc = self.data["depot"]["location"]
        self.order_id_to_solver_node = {}

        depot_open = self.data["depot"]["opening_time"]
        depot_close = self.data["depot"]["closing_time"]

        # Ops semantics flags (per mover validation)
        # - depot closing_time is interpreted as 'latest time a vehicle may depart'
        # - picking can be done before drivers arrive, so vehicles may depart at opening_time without loading queue
        self.depot_close_is_last_departure = bool(self.config.get('depot_close_is_last_departure', True))
        self.picking_preloaded = bool(self.config.get('picking_preloaded', True))

        self.depot_open_time = int(depot_open)
        self.depot_last_departure = int(depot_close)
        self.depot_matrix_node_id = int(self.matrix_assets["depot_node_id"])

        self.time_windows = [(depot_open, depot_close)]  # Node 0 (Depot)
        self.service_times = [0]
        self.order_matrix_node_ids = []

        self.penalties = []
        missing_order_ids = []
        for order in self.orders:
            # Penalty passed in from Simulation layer (preferred)
            if "dynamic_penalty" in order:
                p = int(order["dynamic_penalty"])
            else:
                # Fallback: compute from deadline slack (NOT recommended for stability experiments)
                last_feasible = datetime.strptime(order["feasible_dates"][-1], "%Y-%m-%d")
                delta_t = (last_feasible - self.current_date).days
                if delta_t <= 0:
                    p = int(self.config["urgent_penalty"])
                else:
                    factor = 1 + (self.config["beta"] / (delta_t + self.config["epsilon"]))
                    p = int(self.config["base_penalty"] * factor)

            self.penalties.append(max(p, 1))

            # Node properties
            self.time_windows.append(tuple(order["time_window"]))
            self.service_times.append(order["service_time"])

            order_id = str(order.get("id"))
            matrix_node_id = self.matrix_assets["order_to_node"].get(order_id)
            if matrix_node_id is None:
                missing_order_ids.append(order_id)
                continue
            self.order_matrix_node_ids.append(int(matrix_node_id))
            self.order_id_to_solver_node[order_id] = int(len(self.time_windows) - 1)

        if missing_order_ids:
            sample = ", ".join(missing_order_ids[:10])
            raise ValueError(
                "OSRM matrix is missing order node mappings for current daily orders. "
                f"matrix_dir={self.matrix_dir} missing_count={len(missing_order_ids)} sample=[{sample}]"
            )

    def _compute_distance_matrix(self):
        """Build internal travel matrices from the configured OSRM matrix."""
        matrix_node_ids = [self.depot_matrix_node_id] + self.order_matrix_node_ids
        selected = np.array(matrix_node_ids, dtype=np.int64)
        distance_sub = np.asarray(
            self.matrix_assets["distances"][np.ix_(selected, selected)],
            dtype=np.int64,
        )
        duration_sub_seconds = np.asarray(
            self.matrix_assets["durations"][np.ix_(selected, selected)],
            dtype=np.int64,
        )

        size = len(matrix_node_ids)
        self.distance_matrix = {}
        self.travel_time_matrix = {}
        for i in range(size):
            for j in range(size):
                dist_m = int(distance_sub[i, j])
                dur_seconds = int(duration_sub_seconds[i, j])
                if i == j:
                    travel_min = 0
                elif dur_seconds > 0:
                    # OSRM tables are in seconds; the solver time dimension uses minutes.
                    travel_min = max(1, int(math.ceil(dur_seconds / 60.0)))
                else:
                    travel_min = 0

                self.distance_matrix[(i, j)] = dist_m
                self.travel_time_matrix[(i, j)] = travel_min

    def _init_routing_model(self):
        self.manager = pywrapcp.RoutingIndexManager(self.num_nodes, self.num_vehicles, 0)
        self.routing = pywrapcp.RoutingModel(self.manager)

    def _register_transit_callback(self):
        def distance_callback(from_index, to_index):
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return self.distance_matrix.get((from_node, to_node), 0)

        self.transit_callback_index = self.routing.RegisterTransitCallback(distance_callback)
        self.routing.SetArcCostEvaluatorOfAllVehicles(self.transit_callback_index)

    def _register_time_callback(self):
        """Register Time Callback (Travel + Service)"""

        def time_callback(from_index, to_index):
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)

            travel_time = self.travel_time_matrix.get((from_node, to_node), 0)
            service_time = self.service_times[from_node]
            return travel_time + service_time

        self.time_callback_index = self.routing.RegisterTransitCallback(time_callback)

    def _add_capacity_constraints(self):
        """Add Multi-dimensional Loading Constraints"""
        dimensions = [
            ("colli", self.vehicle_capacities["colli"]),
            ("volume", self.vehicle_capacities["volume"]),
            ("weight", self.vehicle_capacities["weight"]),
        ]
        for dim_name, vehicle_caps in dimensions:

            def demand_callback(from_index, dim=dim_name):
                from_node = self.manager.IndexToNode(from_index)
                if from_node == 0:
                    return 0
                raw_val = self.orders[from_node - 1]["demand"][dim]
                if dim in ["volume", "weight"]:
                    return int(raw_val * SCALING_FACTOR)
                return int(raw_val)

            demand_callback_index = self.routing.RegisterUnaryTransitCallback(demand_callback)
            self.routing.AddDimensionWithVehicleCapacity(
                demand_callback_index, 0, vehicle_caps, True, f"Capacity_{dim_name}"
            )

    def _add_distance_constraints(self):
        """Strict Mileage Constraints per Vehicle Type"""
        max_global_km = max((v["max_distance"] for v in self.vehicle_flat_list), default=3000)

        self.routing.AddDimension(
            self.transit_callback_index,
            0,
            int(max_global_km * 1000),
            True,
            "Distance",
        )
        distance_dimension = self.routing.GetDimensionOrDie("Distance")

        for i in range(self.num_vehicles):
            max_km = self.vehicle_flat_list[i]["max_distance"]
            max_meters = int(max_km * 1000)
            distance_dimension.CumulVar(self.routing.End(i)).SetMax(max_meters)

    def _add_time_window_constraints(self):
        # Add time dimension (minutes)
        horizon = int(self.config.get("horizon_minutes", 30 * 60))
        slack_max = int(self.config.get("slack_max_minutes", 30 * 60))

        self.routing.AddDimension(
            self.time_callback_index,
            slack_max,  # waiting
            horizon,    # horizon cap
            False,      # don't force start cumul to 0
            "Time",
        )
        time_dimension = self.routing.GetMutableDimension("Time")

        depot_open_time = int(self.time_windows[0][0]) if self.time_windows and self.time_windows[0] else 0
        depot_last_departure = int(getattr(self, "depot_last_departure", self.time_windows[0][1] if self.time_windows and self.time_windows[0] else depot_open_time + 600))

        depot_close_is_last_departure = bool(getattr(self, "depot_close_is_last_departure", self.config.get("depot_close_is_last_departure", True)))
        picking_preloaded = bool(getattr(self, "picking_preloaded", self.config.get("picking_preloaded", True)))

        # If close is last-departure, depot 'close' does NOT cap return time.
        end_upper = depot_open_time + horizon if depot_close_is_last_departure else depot_last_departure
        end_upper = max(end_upper, depot_open_time)

        # -------------------------
        # Node time windows
        # -------------------------
        for node, tw in enumerate(self.time_windows):
            index = self.manager.NodeToIndex(node)
            if node == 0 and depot_close_is_last_departure:
                time_dimension.CumulVar(index).SetRange(depot_open_time, end_upper)
            else:
                time_dimension.CumulVar(index).SetRange(int(tw[0]), int(tw[1]))

        # -------------------------
        # Vehicle start/end constraints
        # -------------------------
        v_start_list = self.config.get("vehicle_start_times", None)
        v_max_list = self.config.get("vehicle_max_durations", None)

        if v_start_list is None:
            v_start_list = self._compute_default_vehicle_start_times(int(self.num_vehicles))

        if v_max_list is None:
            v_max_list = self.vehicle_max_durations

        buffer_min = int(self.config.get("depot_last_departure_buffer_min", 0))
        latest_departure = max(depot_open_time, int(depot_last_departure) - buffer_min)

        # Optional lane staggering if picking isn't preloaded and starts weren't provided
        if (not picking_preloaded) and ("vehicle_start_times" not in self.config):
            depot = self.data.get("depot", {}) if isinstance(self.data, dict) else {}
            num_lanes = int(depot.get("num_lanes", depot.get("gates", 1)))
            picking_speed = float(depot.get("picking_speed_colli_per_min", 2.0))
            estimated_load_per_vehicle = float(depot.get("estimated_load_per_vehicle_colli", 50.0))
            depot_service_total_min = estimated_load_per_vehicle / max(1e-9, picking_speed)
            shift_delay_min = max(0, int(round(depot_service_total_min / max(1, num_lanes))))
        else:
            shift_delay_min = 0

        v_start_list = self._apply_gate_release_schedule(list(v_start_list))

        for i in range(int(self.active_vehicles)):
            # Max duration (minutes)
            if isinstance(v_max_list, (list, tuple)):
                max_duration_min = int(v_max_list[i]) if i < len(v_max_list) else int(v_max_list[-1])
            else:
                max_duration_min = int(v_max_list)

            # Start time (minutes)
            if isinstance(v_start_list, (list, tuple)):
                vehicle_start_time = int(v_start_list[i]) if i < len(v_start_list) else depot_open_time
            else:
                vehicle_start_time = int(v_start_list)

            if shift_delay_min > 0 and ("vehicle_start_times" not in self.config):
                vehicle_start_time = depot_open_time + i * shift_delay_min

            vehicle_start_time = max(depot_open_time, vehicle_start_time)

            # End time window
            time_dimension.CumulVar(self.routing.End(i)).SetRange(depot_open_time, end_upper)

            # Disable vehicle if it can't depart in time, or has no remaining duration
            if (max_duration_min <= 0) or (vehicle_start_time > latest_departure):
                self.routing.solver().Add(self.routing.NextVar(self.routing.Start(i)) == self.routing.End(i))
                s = min(max(vehicle_start_time, depot_open_time), end_upper)
                time_dimension.CumulVar(self.routing.Start(i)).SetValue(s)
                time_dimension.CumulVar(self.routing.End(i)).SetValue(s)
                time_dimension.SetSpanUpperBoundForVehicle(0, i)
                continue

            # Gate bucket is hard: each trip is assigned a departure bucket window.
            bucket_start = self._bucketize(vehicle_start_time) * max(1, int(self.bucket_minutes))
            bucket_end = min(bucket_start + max(1, int(self.bucket_minutes)) - 1, latest_departure)
            if bucket_end < bucket_start:
                bucket_end = bucket_start
            time_dimension.CumulVar(self.routing.Start(i)).SetRange(bucket_start, bucket_end)
            time_dimension.SetSpanUpperBoundForVehicle(min(max_duration_min, horizon), i)

    def _add_penalties(self):
        """Add penalties for dropping orders"""
        for i in range(self.num_orders):
            penalty = int(self.penalties[i])
            idx = self.manager.NodeToIndex(i + 1)
            self.routing.AddDisjunction([idx], penalty)

    def _build_search_parameters(self, time_limit_seconds):
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        first_solution_name = self._get_first_solution_strategy()
        local_search_name = self._get_local_search_metaheuristic()
        search_parameters.first_solution_strategy = FIRST_SOLUTION_STRATEGIES.get(
            first_solution_name,
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        )
        search_parameters.local_search_metaheuristic = LOCAL_SEARCH_METAHEURISTICS.get(
            local_search_name,
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
        )
        search_parameters.time_limit.seconds = int(max(1, time_limit_seconds))
        search_parameters.log_search = False
        return search_parameters, first_solution_name, local_search_name

    def _build_initial_routes(self, initial_routes_by_vehicle):
        routes = []
        seeded_orders = 0
        seeded_vehicles = 0
        used_orders = set()
        for vehicle_orders in list(initial_routes_by_vehicle or [])[: self.num_vehicles]:
            route_indices = []
            local_orders = set()
            for order_id in vehicle_orders or []:
                order_key = str(order_id)
                node_index = self.order_id_to_solver_node.get(order_key)
                if node_index is None or order_key in used_orders or order_key in local_orders:
                    continue
                routing_index = self.manager.NodeToIndex(int(node_index))
                if routing_index < 0:
                    continue
                route_indices.append(int(routing_index))
                used_orders.add(order_key)
                local_orders.add(order_key)
            if route_indices:
                seeded_orders += len(route_indices)
                seeded_vehicles += 1
            routes.append(route_indices)
        while len(routes) < self.num_vehicles:
            routes.append([])
        return routes, int(seeded_orders), int(seeded_vehicles)

    def _read_assignment_from_initial_routes(self, initial_routes_by_vehicle, time_limit_seconds):
        routes, seeded_orders, seeded_vehicles = self._build_initial_routes(initial_routes_by_vehicle)
        if seeded_orders <= 0:
            return None, 0, 0
        params, _, _ = self._build_search_parameters(time_limit_seconds)
        self.routing.CloseModelWithParameters(params)
        try:
            assignment = self.routing.ReadAssignmentFromRoutes(routes, True)
        except Exception:
            assignment = None
        if assignment is None:
            return None, 0, 0
        return assignment, int(seeded_orders), int(seeded_vehicles)

    def _solve_once(self, time_limit_seconds=None, initial_routes_by_vehicle=None):
        """Solve a single-trip VRP instance with optional warm-start and chunked continuation."""
        import time

        if initial_routes_by_vehicle is None:
            initial_routes_by_vehicle = self.config.get("initial_routes_by_vehicle")

        actual_time_limit = int(
            time_limit_seconds if time_limit_seconds is not None else self._get_time_limit_seconds()
        )
        chunk_seconds = max(1, min(self._get_solver_chunk_seconds(), actual_time_limit))
        min_chunks = max(1, self._get_solver_min_chunks())
        max_no_improve_chunks = max(0, self._get_solver_max_no_improve_chunks())
        continue_improvement_ratio = max(0.0, self._get_solver_continue_improvement_ratio())
        enable_incumbent_continuation = self._get_solver_enable_incumbent_continuation()
        enable_initial_route_seed = self._get_solver_enable_initial_route_seed()

        seed_assignment = None
        initial_seed_orders = 0
        initial_seed_vehicles = 0
        if enable_initial_route_seed and initial_routes_by_vehicle:
            seed_assignment, initial_seed_orders, initial_seed_vehicles = self._read_assignment_from_initial_routes(
                initial_routes_by_vehicle, min(chunk_seconds, actual_time_limit)
            )

        _safe_print(f"[VRP Solver] Time limit set to: {actual_time_limit}s (from env/config)")
        _safe_print(
            "[VRP Solver] Search config: "
            f"first_solution={self._get_first_solution_strategy()} "
            f"local_search={self._get_local_search_metaheuristic()} "
            f"chunk_seconds={chunk_seconds} "
            f"warm_seed_orders={initial_seed_orders}"
        )

        remaining_budget = int(actual_time_limit)
        cumulative_budget = 0
        chunk_idx = 0
        incumbent_assignment = None
        best_result = None
        best_cost = None
        no_improve_chunks = 0
        total_wall = 0.0
        last_improvement_ratio = 0.0
        warm_start_sources = []

        while remaining_budget > 0:
            chunk_budget = int(min(chunk_seconds, remaining_budget))
            search_parameters, first_solution_name, local_search_name = self._build_search_parameters(chunk_budget)

            warm_start_used = False
            warm_start_source = "none"
            wall_start = time.time()
            if chunk_idx == 0 and seed_assignment is not None:
                solution = self.routing.SolveFromAssignmentWithParameters(seed_assignment, search_parameters)
                warm_start_used = True
                warm_start_source = "prev_day_routes"
            elif chunk_idx > 0 and enable_incumbent_continuation and incumbent_assignment is not None:
                solution = self.routing.SolveFromAssignmentWithParameters(incumbent_assignment, search_parameters)
                warm_start_used = True
                warm_start_source = "incumbent_continuation"
            else:
                solution = self.routing.SolveWithParameters(search_parameters)
            wall_elapsed = time.time() - wall_start
            total_wall += float(wall_elapsed)
            remaining_budget -= chunk_budget
            cumulative_budget += chunk_budget

            chunk_cost = None
            improved = False
            improvement_ratio = 0.0
            if solution:
                incumbent_assignment = solution
                chunk_result = self._process_solution(solution)
                chunk_cost = float(chunk_result.get("cost", 0.0))
                if best_cost is None or chunk_cost + 1e-9 < float(best_cost):
                    if best_cost is None:
                        improvement_ratio = 1.0
                    else:
                        improvement_ratio = max(
                            0.0,
                            (float(best_cost) - float(chunk_cost)) / max(abs(float(best_cost)), 1.0),
                        )
                    best_cost = float(chunk_cost)
                    best_result = chunk_result
                    improved = True
                    no_improve_chunks = 0
                else:
                    no_improve_chunks += 1
            else:
                no_improve_chunks += 1

            last_improvement_ratio = float(improvement_ratio)
            if warm_start_used and warm_start_source not in warm_start_sources:
                warm_start_sources.append(warm_start_source)

            self._solve_once_records.append(
                {
                    "trip_id": int(getattr(self, "trip_id", 1)),
                    "chunk_idx": int(chunk_idx + 1),
                    "order_count": int(len(getattr(self, "orders", []))),
                    "time_limit_seconds": int(actual_time_limit),
                    "chunk_budget_seconds": int(chunk_budget),
                    "cumulative_budget_seconds": int(cumulative_budget),
                    "first_solution_strategy": str(first_solution_name),
                    "local_search_metaheuristic": str(local_search_name),
                    "wall_seconds": float(wall_elapsed),
                    "solution_found": bool(solution),
                    "cost": float(chunk_cost) if chunk_cost is not None else None,
                    "improved": bool(improved),
                    "improvement_ratio": float(improvement_ratio),
                    "warm_start_used": bool(warm_start_used),
                    "warm_start_source": str(warm_start_source),
                }
            )
            _safe_print(
                "[VRP Solver] Chunk "
                f"{chunk_idx + 1}: budget={chunk_budget}s "
                f"wall={wall_elapsed:.2f}s "
                f"found={bool(solution)} "
                f"improved={bool(improved)} "
                f"warm_start={warm_start_source}"
            )

            chunk_idx += 1
            if remaining_budget <= 0:
                break
            if best_result is None:
                continue
            if not enable_incumbent_continuation:
                break
            if chunk_idx < min_chunks:
                continue
            if improvement_ratio >= continue_improvement_ratio:
                continue
            if no_improve_chunks > max_no_improve_chunks:
                break

        _safe_print(f"[VRP Solver] Wall time: {total_wall:.2f}s")
        if best_result is not None:
            best_result["warehouse_feasible"], best_result["warehouse_reason"] = self._warehouse_feasible(best_result.get("routes", []))
            best_result["solver_wall_seconds"] = float(total_wall)
            best_result["solver_time_limit_seconds"] = int(actual_time_limit)
            best_result["solver_budget_used_seconds"] = int(cumulative_budget)
            best_result["solver_chunk_count"] = int(chunk_idx)
            best_result["solver_no_improve_chunks"] = int(no_improve_chunks)
            best_result["solver_last_improvement_ratio"] = float(last_improvement_ratio)
            best_result["solver_warm_start_used"] = bool(warm_start_sources)
            best_result["solver_warm_start_source"] = ",".join(warm_start_sources)
            best_result["solver_initial_seed_orders"] = int(initial_seed_orders)
            best_result["solver_initial_seed_vehicles"] = int(initial_seed_vehicles)
            best_result["solver_first_solution_strategy"] = str(self._get_first_solution_strategy())
            best_result["solver_local_search_metaheuristic"] = str(self._get_local_search_metaheuristic())
            best_result["solver_status"] = "success"
            best_result["solver_attempt_records"] = list(self._solve_once_records)
            return best_result
        return None

    def _warehouse_feasible(self, routes):
        """Check picking throughput / staging feasibility using 22.02 bucket logic."""
        dep_by_bucket = {}
        route_map = defaultdict(list)
        for route in routes or []:
            if not route.get("stops"):
                continue
            bucket = route.get("departure_bucket")
            if bucket is None:
                bucket = self._bucketize(route.get("start_min", 0))
            load = route.get("route_load", {})
            colli = float(load.get("colli", 0.0))
            volume = float(load.get("volume", 0.0))
            c, v = dep_by_bucket.get(bucket, (0.0, 0.0))
            dep_by_bucket[bucket] = (c + colli, v + volume)
            route_map[bucket].append(route)

        if not dep_by_bucket:
            return True, {"reason": "no_routes"}

        open_bucket = self._bucketize(self.picking_open_min)
        close_bucket = self._bucketize(self.picking_close_min)
        cap_colli = float(self.picking_capacity_colli_per_hour) * (self.bucket_minutes / 60.0)
        cap_volume = float(self.picking_capacity_volume_per_hour) * (self.bucket_minutes / 60.0)
        stage_cap = self.max_staging_volume if self.max_staging_volume > 0 else float("inf")

        inv_colli = 0.0
        inv_volume = 0.0
        min_bucket = min(dep_by_bucket.keys())
        max_bucket = max(dep_by_bucket.keys())
        start_bucket = min(open_bucket, min_bucket)

        for bucket in range(start_bucket, max_bucket + 1):
            dep_colli, dep_volume = dep_by_bucket.get(bucket, (0.0, 0.0))

            if inv_colli + 1e-9 < dep_colli or inv_volume + 1e-9 < dep_volume:
                return False, {
                    "reason": "due_to_picking_throughput_or_staging",
                    "bucket": bucket,
                    "routes": route_map.get(bucket, []),
                }

            inv_colli -= dep_colli
            inv_volume -= dep_volume

            if open_bucket <= bucket <= close_bucket:
                remaining_colli = sum(c for k, (c, _) in dep_by_bucket.items() if k > bucket)
                remaining_volume = sum(v for k, (_, v) in dep_by_bucket.items() if k > bucket)

                need_colli = max(0.0, remaining_colli - inv_colli)
                need_volume = max(0.0, remaining_volume - inv_volume)

                pick_colli = min(cap_colli, need_colli)
                pick_volume = min(cap_volume, need_volume, max(0.0, stage_cap - inv_volume))

                inv_colli += pick_colli
                inv_volume += pick_volume

                if inv_volume > stage_cap + 1e-9:
                    return False, {
                        "reason": "due_to_picking_throughput_or_staging",
                        "bucket": bucket,
                        "routes": route_map.get(bucket, []),
                    }

        return True, {"reason": "ok"}

    def _pick_warehouse_drop_candidates(self, warehouse_reason, batch_size=1):
        """Pick a batch of heavy orders to remove from the most constrained departure bucket."""
        routes = warehouse_reason.get("routes") or []
        scored = []
        seen = set()
        for route in routes:
            for stop in route.get("stop_details", []):
                order_id = stop.get("order_id")
                if order_id is None or order_id in seen:
                    continue
                seen.add(order_id)
                key = (
                    float(stop.get("demand_volume", 0.0)),
                    float(stop.get("demand_colli", 0.0)),
                    float(stop.get("demand_weight", 0.0)),
                    int(stop.get("order_id", -1)),
                )
                scored.append((key, order_id))
        scored.sort(reverse=True)
        return [order_id for _, order_id in scored[: max(1, int(batch_size))]]

    def _project_routes_to_initial_routes(self, routes, allowed_orders):
        if not routes:
            return []
        allowed = {str(o.get("id")) for o in allowed_orders if o.get("id") is not None}
        if not allowed:
            return []
        by_vehicle = {}
        max_vehicle = -1
        for route in sorted(routes, key=lambda r: int(r.get("vehicle_id", 10**9))):
            vehicle_id = int(route.get("vehicle_id", -1))
            if vehicle_id < 0 or vehicle_id in by_vehicle:
                continue
            projected = [str(stop) for stop in route.get("stops", []) if str(stop) in allowed]
            if projected:
                by_vehicle[vehicle_id] = projected
                max_vehicle = max(max_vehicle, vehicle_id)
        if max_vehicle < 0:
            return []
        return [list(by_vehicle.get(i, [])) for i in range(max_vehicle + 1)]

    def _compact_routes_for_storage(self, routes):
        compacted = []
        for route in routes or []:
            compacted.append({
                "vehicle_id": int(route.get("vehicle_id", -1)),
                "trip_id": int(route.get("trip_id", 1)),
                "departure_bucket": route.get("departure_bucket"),
                "start_min": route.get("start_min"),
                "end_min": route.get("end_min"),
                "duration_min": route.get("duration_min"),
                "stops": list(route.get("stops", [])),
                "distance_m": route.get("distance_m"),
                "distance": route.get("distance"),
                "route_load": dict(route.get("route_load", {})),
            })
        return compacted

    def _compact_attempt_records(self, records):
        if not records:
            return []
        last = records[-1]
        return [{
            "trip_id": last.get("trip_id"),
            "chunk_idx": last.get("chunk_idx"),
            "time_limit_seconds": last.get("time_limit_seconds"),
            "chunk_budget_seconds": last.get("chunk_budget_seconds"),
            "cumulative_budget_seconds": last.get("cumulative_budget_seconds"),
            "wall_seconds": last.get("wall_seconds"),
            "solution_found": last.get("solution_found"),
            "improved": last.get("improved"),
            "improvement_ratio": last.get("improvement_ratio"),
            "warm_start_source": last.get("warm_start_source"),
        }]

    def _solve_with_warehouse_filter(self, orders_subset, config_override=None, fixed_routes=None):
        """Re-solve while filtering orders until warehouse constraints become feasible."""
        fixed_routes = fixed_routes or []
        config_override = dict(config_override or self.config or {})
        original_orders = list(orders_subset)
        forbidden = set()
        attempts = 0
        max_attempts = min(int(self.warehouse_filter_max_attempts), len(original_orders))
        retry_time_limit = int(self.warehouse_retry_time_limit_seconds)
        drop_batch_size = max(1, int(self.warehouse_drop_batch_size))
        retry_use_initial_routes = bool(self.warehouse_retry_use_initial_routes)
        retry_seed_routes = []
        last_failure_payload = None
        memory_lean_mode = bool(self.memory_lean_mode)

        while attempts <= max_attempts:
            candidate_orders = [o for o in original_orders if o.get("id") not in forbidden]
            if not candidate_orders:
                return {
                    "routes": [],
                    "cost": 0.0,
                    "dropped_indices": [o.get("id") for o in original_orders],
                    "warehouse_log": [],
                    "warehouse_feasible": True,
                    "warehouse_reason": {"reason": "all_filtered"},
                    "warehouse_filter_attempts": int(attempts),
                    "warehouse_filter_max_attempts": int(max_attempts),
                    "warehouse_retry_time_limit_seconds": int(retry_time_limit),
                }

            if attempts == 0 and candidate_orders == list(self.orders) and config_override == dict(self.config or {}):
                candidate_result = self._solve_once(time_limit_seconds=self.time_limit_seconds)
            else:
                child_data = dict(self.data)
                child_data["orders"] = candidate_orders
                child_config = dict(config_override)
                if retry_use_initial_routes and retry_seed_routes:
                    initial_routes = self._project_routes_to_initial_routes(retry_seed_routes, candidate_orders)
                    if sum(len(route) for route in initial_routes) > 0:
                        child_config["solver_enable_initial_route_seed"] = True
                        child_config["initial_routes_by_vehicle"] = initial_routes
                child_solver = RoutingGlsSolver(
                    child_data,
                    self.current_date.strftime("%Y-%m-%d"),
                    config=child_config,
                )
                candidate_result = child_solver._solve_once(time_limit_seconds=retry_time_limit)

            if candidate_result is None:
                return {
                    "routes": [],
                    "cost": 0.0,
                    "dropped_indices": [o.get("id") for o in candidate_orders],
                    "warehouse_log": [],
                    "warehouse_feasible": False,
                    "warehouse_reason": {
                        "reason": "solver_returned_none",
                        "attempts": int(attempts),
                    },
                    "warehouse_filter_attempts": int(attempts),
                    "warehouse_filter_retry_count": int(attempts),
                    "warehouse_filter_solve_count": 0,
                    "warehouse_filter_max_attempts": int(max_attempts),
                    "warehouse_retry_time_limit_seconds": int(retry_time_limit),
                    "solver_status": "no_solution",
                    "solver_attempt_records": [],
                }

            candidate_result.setdefault("solver_attempt_records", list(getattr(self if attempts == 0 and candidate_orders == list(self.orders) and config_override == dict(self.config or {}) else child_solver, "_solve_once_records", [])))
            warehouse_ok, warehouse_reason = self._warehouse_feasible((fixed_routes or []) + candidate_result.get("routes", []))
            candidate_result["warehouse_feasible"] = warehouse_ok
            candidate_result["warehouse_reason"] = warehouse_reason
            candidate_result["warehouse_filter_attempts"] = int(attempts)
            candidate_result["warehouse_filter_retry_count"] = int(attempts)
            candidate_result["warehouse_filter_solve_count"] = int(len(candidate_result.get("solver_attempt_records", [])))
            candidate_result["warehouse_filter_max_attempts"] = int(max_attempts)
            candidate_result["warehouse_retry_time_limit_seconds"] = int(retry_time_limit)

            if warehouse_ok:
                delivered = set()
                for route in candidate_result.get("routes", []):
                    for order_id in route.get("stops", []):
                        delivered.add(order_id)
                dropped = [o.get("id") for o in original_orders if o.get("id") not in delivered]
                candidate_result["dropped_indices"] = dropped
                if memory_lean_mode:
                    candidate_result["routes"] = self._compact_routes_for_storage(candidate_result.get("routes", []))
                    candidate_result["warehouse_log"] = []
                    candidate_result["solver_attempt_records"] = self._compact_attempt_records(candidate_result.get("solver_attempt_records", []))
                return candidate_result

            retry_seed_routes = self._compact_routes_for_storage(candidate_result.get("routes", []))
            drop_ids = [drop_id for drop_id in self._pick_warehouse_drop_candidates(warehouse_reason, batch_size=drop_batch_size) if drop_id not in forbidden]
            last_failure_payload = {
                "routes": self._compact_routes_for_storage(candidate_result.get("routes", [])) if memory_lean_mode else list(candidate_result.get("routes", [])),
                "cost": float(candidate_result.get("cost", 0.0)),
                "dropped_indices": [o.get("id") for o in candidate_orders],
                "warehouse_log": [] if memory_lean_mode else list(candidate_result.get("warehouse_log", [])),
                "warehouse_feasible": False,
                "warehouse_reason": warehouse_reason,
                "warehouse_filter_attempts": int(attempts),
                "warehouse_filter_retry_count": int(attempts),
                "warehouse_filter_solve_count": int(candidate_result.get("warehouse_filter_solve_count", len(candidate_result.get("solver_attempt_records", [])))),
                "warehouse_filter_max_attempts": int(max_attempts),
                "warehouse_retry_time_limit_seconds": int(retry_time_limit),
                "solver_status": "no_solution",
                "solver_attempt_records": self._compact_attempt_records(candidate_result.get("solver_attempt_records", [])) if memory_lean_mode else list(candidate_result.get("solver_attempt_records", [])),
            }
            if not drop_ids:
                return last_failure_payload

            for drop_id in drop_ids:
                forbidden.add(drop_id)
            attempts += len(drop_ids)

            if attempts > 0:
                try:
                    del child_solver
                except Exception:
                    pass
                gc.collect()

        return last_failure_payload

    def solve(self):
        """
        Solve VRP. If VRP_MAX_TRIPS_PER_VEHICLE (or config.max_trips_per_vehicle) >= 2,
        run a 2-wave heuristic: Trip-1 first, then Trip-2 on remaining orders with
        per-vehicle earliest-start + remaining-duration constraints.
        """
        max_trips = int(self._get_max_trips_per_vehicle())
        if max_trips <= 1:
            result = self._solve_with_warehouse_filter(self.orders, config_override=self.config)
            if result is not None:
                result["solver_status"] = result.get("solver_status", "success")
            return result

        # ---- Trip 1 ----
        self.trip_id = 1
        res1 = self._solve_with_warehouse_filter(self.orders, config_override=self.config)
        if res1 is None:
            return None
        if not bool(res1.get("warehouse_feasible", True)) and not res1.get("routes"):
            return res1
        trip_results = [res1]
        all_attempt_records = list(res1.get("solver_attempt_records", []))

        all_orders = list(self.orders)
        delivered = set()
        for r in res1.get("routes", []):
            for oid in (r.get("stops") or []):
                delivered.add(oid)

        default_starts = self._compute_default_vehicle_start_times()
        base_durations = [int(v.get("max_duration", 0)) for v in self.vehicle_flat_list]

        # track per-vehicle totals
        trips_done = [0 for _ in range(int(self.num_vehicles))]
        used_end = [int(default_starts[i]) for i in range(int(self.num_vehicles))]
        used_total = [0 for _ in range(int(self.num_vehicles))]  # minutes, includes completed routes + reloads already happened

        for r in res1.get("routes", []):
            try:
                vid = int(r.get("vehicle_id"))
            except Exception:
                continue
            trips_done[vid] = 1
            try:
                used_end[vid] = int(r.get("end_min", used_end[vid]))
            except Exception:
                pass
            try:
                used_total[vid] = int(r.get("duration_min", used_total[vid]))
            except Exception:
                pass

        total_cost = float(res1.get("cost", 0.0))
        all_routes = list(res1.get("routes", []))
        all_logs = list(res1.get("warehouse_log", []))

        reload_time = int(self._get_reload_time_minutes())
        remaining = [o for o in all_orders if o.get("id") not in delivered]
        remaining_colli = float(sum(float((o.get("demand") or {}).get("colli", 0.0)) for o in remaining))
        delivered_ratio_after_trip1 = (
            float(len(delivered)) / float(len(all_orders)) if all_orders else 1.0
        )
        min_remaining_orders_for_trip2 = int(self.config.get("min_remaining_orders_for_trip2", 0) or 0)
        min_remaining_colli_for_trip2 = float(self.config.get("min_remaining_colli_for_trip2", 0.0) or 0.0)
        min_trip1_delivery_ratio_for_trip2 = float(self.config.get("min_trip1_delivery_ratio_for_trip2", 0.0) or 0.0)
        trip2_gate_passed = True
        trip2_skip_reason = ""
        if len(remaining) < min_remaining_orders_for_trip2:
            trip2_gate_passed = False
            trip2_skip_reason = f"remaining_orders_lt_{min_remaining_orders_for_trip2}"
        elif remaining_colli < min_remaining_colli_for_trip2:
            trip2_gate_passed = False
            trip2_skip_reason = f"remaining_colli_lt_{min_remaining_colli_for_trip2:g}"
        elif delivered_ratio_after_trip1 < min_trip1_delivery_ratio_for_trip2:
            trip2_gate_passed = False
            trip2_skip_reason = f"trip1_delivery_ratio_lt_{min_trip1_delivery_ratio_for_trip2:g}"

        # ---- Trip 2..K ----
        secondary_trip_time_limit = max(
            1,
            int(self.config.get("secondary_trip_time_limit_seconds", self.time_limit_seconds)),
        )
        secondary_trip_retry_time_limit = max(
            1,
            int(
                self.config.get(
                    "secondary_trip_warehouse_retry_time_limit_seconds",
                    min(self.warehouse_retry_time_limit_seconds, secondary_trip_time_limit),
                )
            ),
        )
        trip = 2
        while trip <= max_trips and remaining and trip2_gate_passed:
            v_start = []
            v_dur = []
            for i in range(int(self.num_vehicles)):
                base_max = int(base_durations[i])

                if trips_done[i] >= 1:
                    start_i = int(used_end[i] + reload_time)
                    rem_i = int(base_max - used_total[i] - reload_time)
                else:
                    start_i = int(default_starts[i])
                    rem_i = int(base_max - used_total[i])

                v_start.append(max(0, start_i))
                v_dur.append(max(0, rem_i))

            cfg2 = dict(self.config or {})
            cfg2.pop("initial_routes_by_vehicle", None)
            cfg2["solver_enable_prev_day_route_seed"] = False
            cfg2["vehicle_start_times"] = v_start
            cfg2["vehicle_max_durations"] = v_dur
            cfg2["trip_id"] = int(trip)
            cfg2["reload_time_minutes"] = int(reload_time)
            cfg2["time_limit_seconds"] = int(secondary_trip_time_limit)
            cfg2["warehouse_retry_time_limit_seconds"] = int(secondary_trip_retry_time_limit)

            solver2 = RoutingGlsSolver(dict(self.data, orders=remaining), self.current_date.strftime("%Y-%m-%d"), config=cfg2)
            res2 = solver2._solve_with_warehouse_filter(remaining, config_override=cfg2, fixed_routes=all_routes)
            if res2 is None:
                break
            trip_results.append(res2)
            all_attempt_records.extend(res2.get("solver_attempt_records", []))

            total_cost += float(res2.get("cost", 0.0))
            all_routes.extend(res2.get("routes", []))
            all_logs.extend(res2.get("warehouse_log", []))

            for r in res2.get("routes", []):
                for oid in (r.get("stops") or []):
                    delivered.add(oid)

                try:
                    vid = int(r.get("vehicle_id"))
                except Exception:
                    continue

                if trips_done[vid] >= 1:
                    used_total[vid] += reload_time
                trips_done[vid] += 1

                try:
                    used_end[vid] = int(r.get("end_min", used_end[vid]))
                except Exception:
                    pass
                try:
                    used_total[vid] += int(r.get("duration_min", 0))
                except Exception:
                    pass

            remaining = [o for o in all_orders if o.get("id") not in delivered]
            trip += 1

        dropped_final = [o.get("id") for o in all_orders if o.get("id") not in delivered]
        warehouse_ok, warehouse_reason = self._warehouse_feasible(all_routes)
        trip1_attempt_count = int(sum(1 for rec in all_attempt_records if int(rec.get("trip_id", 1)) == 1))
        trip2plus_attempt_count = int(sum(1 for rec in all_attempt_records if int(rec.get("trip_id", 1)) >= 2))
        trip1_wall_seconds = float(sum(float(rec.get("wall_seconds", 0.0)) for rec in all_attempt_records if int(rec.get("trip_id", 1)) == 1))
        trip2plus_wall_seconds = float(sum(float(rec.get("wall_seconds", 0.0)) for rec in all_attempt_records if int(rec.get("trip_id", 1)) >= 2))
        warehouse_retry_count_total = int(sum(int(r.get("warehouse_filter_retry_count", 0)) for r in trip_results))
        warehouse_filter_solve_count_total = int(sum(int(r.get("warehouse_filter_solve_count", len(r.get("solver_attempt_records", [])))) for r in trip_results))
        return {
            "routes": all_routes,
            "cost": float(total_cost),
            "dropped_indices": dropped_final,
            "warehouse_log": all_logs,
            "warehouse_feasible": warehouse_ok,
            "warehouse_reason": warehouse_reason,
            "solver_wall_seconds": float(sum(float(r.get("solver_wall_seconds", 0.0)) for r in trip_results)),
            "solver_time_limit_seconds": int(self._get_time_limit_seconds()),
            "solver_status": "success",
            "solver_attempt_records": all_attempt_records,
            "trip_count": int(len(trip_results)),
            "trip1_attempt_count": trip1_attempt_count,
            "trip2plus_attempt_count": trip2plus_attempt_count,
            "trip1_wall_seconds": trip1_wall_seconds,
            "trip2plus_wall_seconds": trip2plus_wall_seconds,
            "warehouse_retry_count_total": warehouse_retry_count_total,
            "warehouse_filter_solve_count_total": warehouse_filter_solve_count_total,
            "trip2_gate_passed": bool(trip2_gate_passed),
            "trip2_skip_reason": str(trip2_skip_reason),
            "remaining_orders_after_trip1": int(len(remaining) if not trip2_gate_passed else len([o for o in all_orders if o.get("id") not in delivered])),
            "remaining_colli_after_trip1": float(remaining_colli),
            "trip1_delivery_ratio": float(delivered_ratio_after_trip1),
        }
    def _process_solution(self, solution):
        """Parse solution + generate detailed warehouse schedule log"""

        # --------- dropped nodes (FIXED) ----------
        # Return node_id (1..N) to match upper-layer normalization.
        dropped_nodes = []
        for node_id in range(1, self.num_nodes):
            idx = self.manager.NodeToIndex(node_id)
            if self.routing.IsStart(idx) or self.routing.IsEnd(idx):
                continue
            if solution.Value(self.routing.NextVar(idx)) == idx:
                dropped_nodes.append(node_id)

        # Convert dropped node indices (1..N) to order ids for upstream robustness.
        dropped_order_ids = []
        for nid in dropped_nodes:
            try:
                if 1 <= int(nid) <= len(self.orders):
                    dropped_order_ids.append(self.orders[int(nid) - 1].get("id"))
                else:
                    dropped_order_ids.append(nid)
            except Exception:
                dropped_order_ids.append(nid)

        routes_summary = []
        warehouse_queue = []
        total_distance_km = 0.0

        time_dim = self.routing.GetDimensionOrDie("Time")
        cap_colli_dim = self.routing.GetDimensionOrDie("Capacity_colli")
        cap_volume_dim = self.routing.GetDimensionOrDie("Capacity_volume")
        cap_weight_dim = self.routing.GetDimensionOrDie("Capacity_weight")

        for vehicle_id in range(self.num_vehicles):
            index = self.routing.Start(vehicle_id)
            if self.routing.IsEnd(solution.Value(self.routing.NextVar(index))):
                continue

            start_val = solution.Value(time_dim.CumulVar(index))
            end_index = self.routing.End(vehicle_id)
            end_val = solution.Value(time_dim.CumulVar(end_index))

            warehouse_queue.append({"v_id": vehicle_id, "colli": 0, "clock_in": start_val, "clock_out": end_val})

            route_dist_m = 0
            route_load = {"colli": 0, "volume": 0, "weight": 0}
            stops = []
            stop_details = []

            while not self.routing.IsEnd(index):
                previous_index = index
                index = solution.Value(self.routing.NextVar(index))

                node_index = self.manager.IndexToNode(index)
                if node_index > 0:
                    order = self.orders[node_index - 1]
                    stops.append(order["id"])
                    for k in route_load:
                        route_load[k] += order["demand"][k]
                    arr_min = float(solution.Value(time_dim.CumulVar(index)))
                    arr_max = float(solution.Max(time_dim.CumulVar(index)))
                    tw = order.get("time_window", [None, None])
                    stop_details.append(
                        {
                            "order_id": order.get("id"),
                            "node_index": int(node_index),
                            "arrival_min": arr_min,
                            "arrival_cumul_min": arr_min,
                            "arrival_cumul_max": arr_max,
                            "arrival_source": "ortools_time_dimension_cumul",
                            "time_window_start_min": float(tw[0]) if tw and tw[0] is not None else None,
                            "time_window_end_min": float(tw[1]) if tw and tw[1] is not None else None,
                            "demand_colli": float(order.get("demand", {}).get("colli", 0.0)),
                            "demand_volume": float(order.get("demand", {}).get("volume", 0.0)),
                            "demand_weight": float(order.get("demand", {}).get("weight", 0.0)),
                            "cumul_colli": float(solution.Value(cap_colli_dim.CumulVar(index))),
                            "cumul_volume": float(solution.Value(cap_volume_dim.CumulVar(index))) / SCALING_FACTOR,
                            "cumul_weight": float(solution.Value(cap_weight_dim.CumulVar(index))) / SCALING_FACTOR,
                        }
                    )

                from_node = self.manager.IndexToNode(previous_index)
                to_node = self.manager.IndexToNode(index)
                route_dist_m += self.distance_matrix.get((from_node, to_node), 0)

            total_distance_km += route_dist_m / 1000.0
            warehouse_queue[-1]["colli"] = route_load["colli"]

            routes_summary.append(
                {
                    "vehicle_id": vehicle_id,
                    "trip_id": int(getattr(self, "trip_id", 1)),
                    "departure_bucket": self._bucketize(start_val),
                    "start_min": float(start_val),
                    "end_min": float(end_val),
                    "duration_min": float(end_val - start_val),
                    "stops": stops,
                    "stop_details": stop_details,
                    "distance_m": route_dist_m,
                    "distance": route_dist_m / 1000.0,  # km
                    "route_load": {
                        "colli": float(route_load["colli"]),
                        "volume": float(route_load["volume"]),
                        "weight": float(route_load["weight"]),
                    },
                    "vehicle_capacity": {
                        "colli": float(self.vehicle_capacities["colli"][vehicle_id]),
                        "volume": float(self.vehicle_capacities["volume"][vehicle_id]) / SCALING_FACTOR,
                        "weight": float(self.vehicle_capacities["weight"][vehicle_id]) / SCALING_FACTOR,
                    },
                }
            )

        # --- Generate Detailed Log (For Excel Export) ---
        warehouse_log_data = []

        picking_speed = self.data["depot"].get("picking_capacity", {}).get("colli_per_hour", 200)
        num_gates = self.data["depot"].get("gates", 4)

        depot_open_min = self.data["depot"].get("picking_open_min", self.data["depot"].get("opening_time", 0))
        gate_free_time = [depot_open_min] * num_gates

        warehouse_queue.sort(key=lambda x: x["clock_in"])

        for task in warehouse_queue:
            loading_duration = (task["colli"] / picking_speed) * 60

            load_act = self.data["depot"].get("loading_time_minutes", 30)
            unload_act = self.data["depot"].get("unloading_time_minutes", 15)

            total_loading_time = load_act + loading_duration

            earliest_gate_idx = gate_free_time.index(min(gate_free_time))
            gate_ready = gate_free_time[earliest_gate_idx]

            actual_start_load = max(task["clock_in"], gate_ready)
            actual_depart = actual_start_load + total_loading_time
            gate_free_time[earliest_gate_idx] = actual_depart

            solver_clock_in = task["clock_in"]
            solver_clock_out = task["clock_out"]
            total_duration = solver_clock_out - solver_clock_in

            planned_depart = solver_clock_in
            planned_arrive_back = solver_clock_out

            def fmt(m):
                return f"{int(m // 60):02d}:{int(m % 60):02d}"

            v_type_name = self.vehicle_flat_list[task["v_id"]]["type"]

            log_entry = {
                "VehicleID": f"#{task['v_id']:02d}",
                "VehicleType": v_type_name,
                "Gate": earliest_gate_idx + 1,
                "ColliLoad": task["colli"],
                "SolverDepart": fmt(solver_clock_in),
                "SolverReturn": fmt(solver_clock_out),
                "GateDepart": fmt(actual_depart),
                "ClockIn": fmt(solver_clock_in),
                "LoadingTime": f"{load_act}m",
                "DepartOutput": fmt(planned_depart),
                "ArriveBack": fmt(planned_arrive_back),
                "UnloadingTime": f"{unload_act}m",
                "ClockOut": fmt(solver_clock_out),
                "TotalDuration_h": round(total_duration / 60, 2),
            }
            warehouse_log_data.append(log_entry)

        return {
            "routes": routes_summary,
            "dropped_indices": dropped_order_ids,  # node_id (1..N)
            "cost": total_distance_km,
            "warehouse_log": warehouse_log_data,
        }


# Backward-compatible alias for legacy imports and experiment scripts.
ALNS_Solver = RoutingGlsSolver

__all__ = ["RoutingGlsSolver", "ALNS_Solver"]
