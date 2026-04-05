#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from array import array
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests


DEFAULT_BENCHMARK = Path("data/processed/multiday_benchmark_herlev.json")
DEFAULT_OUTPUT_DIR = Path("data/processed/vrp_matrix_latest")
DEFAULT_OSRM_URL = "http://127.0.0.1:5080"
DEFAULT_OSRM_DATA = Path(
    "../22.02thesis/data/processed/vrp_data/vrp_maps/denmark/20260223/denmark-latest.osrm"
)
DEFAULT_OSRM_IMAGE = "ghcr.io/project-osrm/osrm-backend:v5.27.1"
DEFAULT_BLOCK_SIZE = 100


def format_coord(value: float) -> str:
    return f"{value:.7f}".rstrip("0").rstrip(".")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def chunk_ranges(n: int, block_size: int) -> list[tuple[int, int]]:
    return [(start, min(start + block_size, n)) for start in range(0, n, block_size)]


def check_osrm_health(osrm_url: str, timeout_s: float = 10.0) -> None:
    response = requests.get(
        f"{osrm_url.rstrip('/')}/nearest/v1/driving/12.4333188,55.7171287",
        timeout=timeout_s,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM health check failed: {payload}")


def table_request(
    session: requests.Session,
    osrm_url: str,
    coords: list[tuple[float, float]],
    source_indices: list[int] | None,
    destination_indices: list[int] | None,
    timeout_s: float,
) -> dict[str, object]:
    coord_str = ";".join(f"{format_coord(lon)},{format_coord(lat)}" for lat, lon in coords)
    params: dict[str, str] = {"annotations": "duration,distance"}
    if source_indices is not None:
        params["sources"] = ";".join(str(i) for i in source_indices)
    if destination_indices is not None:
        params["destinations"] = ";".join(str(i) for i in destination_indices)
    url = f"{osrm_url.rstrip('/')}/table/v1/driving/{coord_str}?{urlencode(params)}"
    response = session.get(url, timeout=timeout_s)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM table failed: {payload.get('code')} {payload}")
    return payload


def write_nodes_csv(path: Path, dataset: dict[str, object]) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    depot_lat, depot_lon = dataset["depot"]["location"]
    coords.append((float(depot_lat), float(depot_lon)))
    with path.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["node_id", "kind", "order_id", "lat", "lon"])
        writer.writerow([0, "depot", "", depot_lat, depot_lon])
        for node_id, order in enumerate(dataset["orders"], start=1):
            lat, lon = order["location"]
            writer.writerow([node_id, "order", str(order["id"]), lat, lon])
            coords.append((float(lat), float(lon)))
    return coords


def write_orders_csv(path: Path, dataset: dict[str, object]) -> None:
    with path.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(
            [
                "order_id",
                "release_date",
                "feasible_dates",
                "deadline",
                "time_window_start",
                "time_window_end",
                "service_time",
                "colli",
                "volume",
                "weight",
                "is_flexible",
                "delivery_window_days",
                "order_date",
            ]
        )
        for order in dataset["orders"]:
            feasible_dates = list(order["feasible_dates"])
            writer.writerow(
                [
                    str(order["id"]),
                    order["release_date"],
                    "|".join(feasible_dates),
                    max(feasible_dates),
                    int(order["time_window"][0]),
                    int(order["time_window"][1]),
                    int(order["service_time"]),
                    float(order["demand"]["colli"]),
                    float(order["demand"]["volume"]),
                    float(order["demand"]["weight"]),
                    "true" if order["is_flexible"] else "false",
                    int(order["delivery_window_days"]),
                    order["order_date"],
                ]
            )


def generate_matrix(
    *,
    benchmark_path: Path,
    output_dir: Path,
    osrm_url: str,
    osrm_data: Path,
    osrm_image: str,
    block_size: int,
    timeout_s: float,
    strict_no_fallback: bool,
) -> dict[str, object]:
    dataset = json.loads(benchmark_path.read_text())
    output_dir.mkdir(parents=True, exist_ok=True)

    nodes_csv = output_dir / "nodes.csv"
    orders_csv = output_dir / "orders.csv"
    durations_bin = output_dir / "durations.int32.bin"
    distances_bin = output_dir / "distances.int32.bin"
    fallback_file = output_dir / "fallback_pairs.jsonl"
    metadata_file = output_dir / "metadata.json"
    index_file = output_dir / "index.json"

    coords = write_nodes_csv(nodes_csv, dataset)
    write_orders_csv(orders_csv, dataset)

    n_nodes = len(coords)
    ranges = chunk_ranges(n_nodes, block_size)
    fallback_pairs: list[dict[str, object]] = []
    session = requests.Session()

    start_ts = time.time()
    with durations_bin.open("wb") as durations_fp, distances_bin.open("wb") as distances_fp:
        for src_block_idx, (src_start, src_end) in enumerate(ranges):
            duration_rows = [array("i", [0] * n_nodes) for _ in range(src_end - src_start)]
            distance_rows = [array("i", [0] * n_nodes) for _ in range(src_end - src_start)]
            src_coords = coords[src_start:src_end]

            for dst_block_idx, (dst_start, dst_end) in enumerate(ranges):
                dst_coords = coords[dst_start:dst_end]
                if src_start == dst_start and src_end == dst_end:
                    payload = table_request(
                        session=session,
                        osrm_url=osrm_url,
                        coords=src_coords,
                        source_indices=None,
                        destination_indices=None,
                        timeout_s=timeout_s,
                    )
                else:
                    merged = src_coords + dst_coords
                    payload = table_request(
                        session=session,
                        osrm_url=osrm_url,
                        coords=merged,
                        source_indices=list(range(len(src_coords))),
                        destination_indices=list(range(len(src_coords), len(merged))),
                        timeout_s=timeout_s,
                    )

                durations = payload.get("durations")
                distances = payload.get("distances")
                if durations is None or distances is None:
                    raise RuntimeError(f"Missing annotations in OSRM response for block {src_block_idx}->{dst_block_idx}")

                for i, row in enumerate(durations):
                    if row is None:
                        raise RuntimeError(f"Null duration row at source block {src_block_idx}, row {i}")
                    for j, value in enumerate(row):
                        if value is None:
                            fallback_pairs.append(
                                {
                                    "source_node_id": src_start + i,
                                    "destination_node_id": dst_start + j,
                                    "reason": "null_duration",
                                }
                            )
                            duration_rows[i][dst_start + j] = -1
                        else:
                            duration_rows[i][dst_start + j] = int(round(float(value)))

                for i, row in enumerate(distances):
                    if row is None:
                        raise RuntimeError(f"Null distance row at source block {src_block_idx}, row {i}")
                    for j, value in enumerate(row):
                        if value is None:
                            fallback_pairs.append(
                                {
                                    "source_node_id": src_start + i,
                                    "destination_node_id": dst_start + j,
                                    "reason": "null_distance",
                                }
                            )
                            distance_rows[i][dst_start + j] = -1
                        else:
                            distance_rows[i][dst_start + j] = int(round(float(value)))

            for row in duration_rows:
                row.tofile(durations_fp)
            for row in distance_rows:
                row.tofile(distances_fp)

            elapsed = time.time() - start_ts
            print(
                f"[matrix] {benchmark_path.stem}: source_block {src_block_idx + 1}/{len(ranges)} "
                f"rows={src_start}:{src_end} elapsed={elapsed:.1f}s",
                flush=True,
            )

    if strict_no_fallback and fallback_pairs:
        with fallback_file.open("w") as fp:
            for pair in fallback_pairs:
                fp.write(json.dumps(pair, ensure_ascii=False) + "\n")
        raise RuntimeError(f"{benchmark_path.stem}: fallback pairs detected: {len(fallback_pairs)}")

    with fallback_file.open("w") as fp:
        for pair in fallback_pairs:
            fp.write(json.dumps(pair, ensure_ascii=False) + "\n")

    metadata = {
        "note": "Generated by build_matrix_from_benchmark.py",
        "benchmark_path": str(benchmark_path.resolve()),
        "osrm_data": str(osrm_data),
        "runtime": "docker",
        "osrm_image": osrm_image,
        "osrm_image_digest": "unknown",
    }
    metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")

    matrix_cells = n_nodes * n_nodes
    fallback_count = len(fallback_pairs)
    index = {
        "nodes_csv_sha256": sha256_file(nodes_csv),
        "fallback_file": fallback_file.name,
        "fallback_count": fallback_count,
        "osrm_image_digest": "unknown",
        "max_nodes_used": n_nodes,
        "distances_sha256": sha256_file(distances_bin),
        "osrm_algorithm": "ch",
        "osrm_max_table_size": block_size,
        "n_nodes": n_nodes,
        "dtype": "int32",
        "durations_bin": durations_bin.name,
        "fallback_ratio": 0.0 if matrix_cells == 0 else fallback_count / matrix_cells,
        "nodes_csv": nodes_csv.name,
        "durations_sha256": sha256_file(durations_bin),
        "layout": "row_major",
        "distances_bin": distances_bin.name,
        "fallback_file_sha256": sha256_file(fallback_file),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "osrm_image": osrm_image,
    }
    index_file.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    return index


def validate_outputs(benchmark_path: Path, matrix_dir: Path) -> None:
    dataset = json.loads(benchmark_path.read_text())
    index = json.loads((matrix_dir / "index.json").read_text())

    with (matrix_dir / "nodes.csv").open(newline="") as fp:
        node_rows = list(csv.DictReader(fp))
    with (matrix_dir / "orders.csv").open(newline="") as fp:
        order_rows = list(csv.DictReader(fp))

    expected_nodes = 1 + len(dataset["orders"])
    if len(node_rows) != expected_nodes:
        raise RuntimeError(f"{matrix_dir.name}: expected {expected_nodes} nodes, found {len(node_rows)}")
    if int(index["n_nodes"]) != expected_nodes:
        raise RuntimeError(f"{matrix_dir.name}: index n_nodes={index['n_nodes']} != {expected_nodes}")
    if not node_rows or int(node_rows[0]["node_id"]) != 0 or node_rows[0]["kind"] != "depot":
        raise RuntimeError(f"{matrix_dir.name}: depot is not node 0")

    order_ids_in_nodes = {row["order_id"] for row in node_rows if row["kind"] == "order"}
    order_ids_expected = {str(order["id"]) for order in dataset["orders"]}
    missing = sorted(order_ids_expected - order_ids_in_nodes)
    if missing:
        raise RuntimeError(f"{matrix_dir.name}: missing order ids in nodes.csv, sample={missing[:10]}")
    if len(order_rows) != len(dataset["orders"]):
        raise RuntimeError(f"{matrix_dir.name}: orders.csv rows={len(order_rows)} != dataset orders={len(dataset['orders'])}")

    expected_size = expected_nodes * expected_nodes * 4
    duration_size = (matrix_dir / "durations.int32.bin").stat().st_size
    distance_size = (matrix_dir / "distances.int32.bin").stat().st_size
    if duration_size != expected_size:
        raise RuntimeError(f"{matrix_dir.name}: durations size {duration_size} != expected {expected_size}")
    if distance_size != expected_size:
        raise RuntimeError(f"{matrix_dir.name}: distances size {distance_size} != expected {expected_size}")
    if int(index.get("fallback_count", -1)) != 0:
        raise RuntimeError(f"{matrix_dir.name}: fallback_count={index.get('fallback_count')} but strict OSRM is required")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an OSRM matrix directory from a benchmark JSON")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--osrm-url", default=DEFAULT_OSRM_URL)
    parser.add_argument("--osrm-data", type=Path, default=DEFAULT_OSRM_DATA)
    parser.add_argument("--osrm-image", default=DEFAULT_OSRM_IMAGE)
    parser.add_argument("--block-size", type=int, default=DEFAULT_BLOCK_SIZE)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--allow-fallback", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    check_osrm_health(args.osrm_url)
    benchmark_path = args.benchmark.resolve()
    output_dir = args.output_dir.resolve()
    print(f"[benchmark] {benchmark_path}", flush=True)
    print(f"[output] {output_dir}", flush=True)
    generate_matrix(
        benchmark_path=benchmark_path,
        output_dir=output_dir,
        osrm_url=args.osrm_url,
        osrm_data=args.osrm_data.resolve(),
        osrm_image=args.osrm_image,
        block_size=args.block_size,
        timeout_s=args.timeout_s,
        strict_no_fallback=not args.allow_fallback,
    )
    validate_outputs(benchmark_path, output_dir)
    print(f"[validated] {output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
