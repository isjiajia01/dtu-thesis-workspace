#!/usr/bin/env python3
"""
Build a full OSRM travel-time / distance matrix for a processed benchmark JSON.

This script writes the same artifact family used by the retained 22.03 depot
matrices:
  - nodes.csv
  - orders.csv
  - index.json
  - durations.int32.bin
  - distances.int32.bin
  - metadata.json
  - fallback_pairs.jsonl (empty; fallback is disallowed)
  - audit/matrix_report.json
  - blocks/status.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OSRM_DATA = ROOT.parent / "22.02thesis" / "data" / "processed" / "vrp_data" / "vrp_maps" / "denmark" / "20260223" / "denmark-latest.osrm"
DEFAULT_OSRM_IMAGE = "ghcr.io/project-osrm/osrm-backend:v5.27.1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _json_dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _csv_write(path: Path, header: list[str], rows: Iterable[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(header)
        writer.writerows(rows)


def _format_coords(coords: list[tuple[float, float]]) -> str:
    # OSRM expects lon,lat order.
    return ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in coords)


def _request_json(url: str, timeout: float = 120.0) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _find_open_port(start_port: int) -> int:
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Could not find an open local port starting from {start_port}")


class OsrmServer:
    def __init__(
        self,
        *,
        runtime: str,
        osrm_data: Path,
        osrm_url: str | None,
        host: str,
        port: int,
        algorithm: str,
        osrm_image: str,
    ) -> None:
        self.runtime = runtime
        self.osrm_data = osrm_data
        self.osrm_url = osrm_url.rstrip("/") if osrm_url else None
        self.host = host
        self.port = port
        self.algorithm = algorithm
        self.osrm_image = osrm_image
        self.process: subprocess.Popen[str] | None = None
        self.effective_runtime = runtime

    @property
    def base_url(self) -> str:
        if self.osrm_url:
            return self.osrm_url
        return f"http://{self.host}:{self.port}"

    def start(self, probe_coord: tuple[float, float]) -> None:
        if self.osrm_url:
            self.effective_runtime = "external_url"
            self._wait_ready(probe_coord)
            return

        runtime = self.runtime
        if runtime == "auto":
            if shutil.which("osrm-routed"):
                runtime = "binary"
            elif shutil.which("docker"):
                runtime = "docker"
            else:
                raise RuntimeError(
                    "No OSRM runtime found. Expected one of: osrm-routed, docker, or --osrm-url."
                )

        self.port = _find_open_port(self.port)

        if runtime == "binary":
            cmd = [
                "osrm-routed",
                "--algorithm",
                self.algorithm,
                "--port",
                str(self.port),
                str(self.osrm_data),
            ]
        elif runtime == "docker":
            cmd = [
                "docker",
                "run",
                "--rm",
                "-p",
                f"{self.port}:5000",
                "-v",
                f"{self.osrm_data.parent}:/data",
                self.osrm_image,
                "osrm-routed",
                "--algorithm",
                self.algorithm,
                f"/data/{self.osrm_data.name}",
            ]
        else:
            raise RuntimeError(f"Unsupported runtime: {runtime}")

        self.effective_runtime = runtime
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._wait_ready(probe_coord)

    def _wait_ready(self, probe_coord: tuple[float, float], timeout_s: float = 60.0) -> None:
        deadline = time.time() + timeout_s
        lat, lon = probe_coord
        probe_url = f"{self.base_url}/nearest/v1/driving/{lon:.7f},{lat:.7f}"
        while time.time() < deadline:
            if self.process is not None and self.process.poll() is not None:
                output = ""
                if self.process.stdout is not None:
                    output = self.process.stdout.read()
                raise RuntimeError(f"OSRM server exited before becoming ready:\n{output}")
            try:
                payload = _request_json(probe_url, timeout=5.0)
                if payload.get("code") == "Ok":
                    return
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
                time.sleep(1.0)
                continue
        raise RuntimeError(f"OSRM server did not become ready within {timeout_s:.0f}s: {self.base_url}")

    def stop(self) -> None:
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5.0)


def _write_nodes_csv(output_dir: Path, depot_name: str, depot_location: list[float], orders: list[dict]) -> None:
    rows = [[0, "depot", "", depot_location[0], depot_location[1]]]
    for idx, order in enumerate(orders, start=1):
        rows.append([idx, "order", order["id"], order["location"][0], order["location"][1]])
    _csv_write(output_dir / "nodes.csv", ["node_id", "kind", "order_id", "lat", "lon"], rows)


def _write_orders_csv(output_dir: Path, orders: list[dict]) -> None:
    rows = []
    for order in orders:
        rows.append(
            [
                order["id"],
                order["release_date"],
                "|".join(order.get("feasible_dates", [])),
                max(order.get("feasible_dates", [])) if order.get("feasible_dates") else "",
                order["time_window"][0],
                order["time_window"][1],
                order["service_time"],
                order["demand"]["colli"],
                order["demand"]["volume"],
                order["demand"]["weight"],
                str(bool(order.get("is_flexible", False))).lower(),
                order.get("delivery_window_days", len(order.get("feasible_dates", []))),
                order.get("order_date", order.get("release_date", "")),
            ]
        )
    _csv_write(
        output_dir / "orders.csv",
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
        ],
        rows,
    )


def _fetch_block(
    *,
    server: OsrmServer,
    coords: list[tuple[float, float]],
    src_slice: slice,
    dst_slice: slice,
    annotations: str = "duration,distance",
) -> tuple[np.ndarray, np.ndarray]:
    src_coords = coords[src_slice]
    dst_coords = coords[dst_slice]
    block_coords = src_coords + dst_coords
    params = urlencode(
        {
            "sources": ";".join(str(i) for i in range(len(src_coords))),
            "destinations": ";".join(str(i + len(src_coords)) for i in range(len(dst_coords))),
            "annotations": annotations,
        }
    )
    url = f"{server.base_url}/table/v1/driving/{_format_coords(block_coords)}?{params}"
    payload = _request_json(url, timeout=300.0)
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM table failed for {src_slice} x {dst_slice}: {payload}")

    durations = payload.get("durations")
    distances = payload.get("distances")
    if durations is None or distances is None:
        raise RuntimeError(f"OSRM table missing annotations for {src_slice} x {dst_slice}")

    if any(value is None for row in durations for value in row):
        raise RuntimeError(f"OSRM returned null durations for {src_slice} x {dst_slice}")
    if any(value is None for row in distances for value in row):
        raise RuntimeError(f"OSRM returned null distances for {src_slice} x {dst_slice}")

    durations_arr = np.rint(np.array(durations, dtype=np.float64)).astype(np.int32)
    distances_arr = np.rint(np.array(distances, dtype=np.float64)).astype(np.int32)
    return durations_arr, distances_arr


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OSRM matrix artifacts for a processed benchmark JSON")
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--osrm-data", default=str(DEFAULT_OSRM_DATA))
    parser.add_argument("--runtime", default="auto", choices=["auto", "binary", "docker"])
    parser.add_argument("--osrm-url", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--block-size", type=int, default=100)
    parser.add_argument("--max-table-size", type=int, default=200)
    parser.add_argument("--algorithm", default="ch")
    parser.add_argument("--osrm-image", default=DEFAULT_OSRM_IMAGE)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark).resolve()
    output_dir = Path(args.output_dir).resolve()
    osrm_data = Path(args.osrm_data).resolve()

    if args.block_size <= 0:
        raise ValueError("block-size must be positive")
    if args.block_size * 2 > args.max_table_size:
        raise ValueError("block-size * 2 must be <= max-table-size")

    if output_dir.exists():
        if not args.overwrite:
            raise FileExistsError(f"Output dir already exists: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "audit").mkdir(parents=True, exist_ok=True)
    (output_dir / "blocks").mkdir(parents=True, exist_ok=True)

    benchmark = json.loads(benchmark_path.read_text())
    depot = benchmark["depot"]
    orders = list(benchmark["orders"])
    n_nodes = len(orders) + 1
    coords = [tuple(depot["location"])]
    coords.extend(tuple(order["location"]) for order in orders)

    _write_nodes_csv(output_dir, depot["name"], depot["location"], orders)
    _write_orders_csv(output_dir, orders)
    (output_dir / "fallback_pairs.jsonl").write_text("")

    durations_path = output_dir / "durations.int32.bin"
    distances_path = output_dir / "distances.int32.bin"
    durations = np.memmap(durations_path, dtype=np.int32, mode="w+", shape=(n_nodes, n_nodes))
    distances = np.memmap(distances_path, dtype=np.int32, mode="w+", shape=(n_nodes, n_nodes))

    server = OsrmServer(
        runtime=args.runtime,
        osrm_data=osrm_data,
        osrm_url=args.osrm_url,
        host=args.host,
        port=args.port,
        algorithm=args.algorithm,
        osrm_image=args.osrm_image,
    )

    status_rows: list[list[object]] = []
    started_at = time.time()
    try:
        server.start(coords[0])
        for row_start in range(0, n_nodes, args.block_size):
            row_end = min(row_start + args.block_size, n_nodes)
            for col_start in range(0, n_nodes, args.block_size):
                col_end = min(col_start + args.block_size, n_nodes)
                block_started = time.time()
                dur_block, dist_block = _fetch_block(
                    server=server,
                    coords=coords,
                    src_slice=slice(row_start, row_end),
                    dst_slice=slice(col_start, col_end),
                )
                durations[row_start:row_end, col_start:col_end] = dur_block
                distances[row_start:row_end, col_start:col_end] = dist_block
                status_rows.append(
                    [
                        row_start,
                        row_end - 1,
                        col_start,
                        col_end - 1,
                        "ok",
                        round(time.time() - block_started, 3),
                    ]
                )
    finally:
        server.stop()

    durations.flush()
    distances.flush()
    elapsed_s = round(time.time() - started_at, 3)

    _csv_write(
        output_dir / "blocks" / "status.csv",
        ["row_start", "row_end", "col_start", "col_end", "status", "elapsed_s"],
        status_rows,
    )

    nodes_sha = _sha256_file(output_dir / "nodes.csv")
    dist_sha = _sha256_file(distances_path)
    dur_sha = _sha256_file(durations_path)
    fallback_sha = _sha256_file(output_dir / "fallback_pairs.jsonl")

    metadata = {
        "note": "Generated by scripts/build_osrm_matrix.py",
        "benchmark_path": str(benchmark_path),
        "osrm_data": str(osrm_data),
        "runtime": server.effective_runtime,
        "osrm_image": args.osrm_image,
        "osrm_image_digest": "unknown",
    }
    _json_dump(output_dir / "metadata.json", metadata)

    index = {
        "nodes_csv_sha256": nodes_sha,
        "fallback_file": "fallback_pairs.jsonl",
        "fallback_count": 0,
        "osrm_image_digest": "unknown",
        "max_nodes_used": n_nodes,
        "distances_sha256": dist_sha,
        "osrm_algorithm": args.algorithm,
        "osrm_max_table_size": args.max_table_size,
        "n_nodes": n_nodes,
        "dtype": "int32",
        "durations_bin": "durations.int32.bin",
        "fallback_ratio": 0.0,
        "nodes_csv": "nodes.csv",
        "durations_sha256": dur_sha,
        "layout": "row_major",
        "distances_bin": "distances.int32.bin",
        "fallback_file_sha256": fallback_sha,
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "osrm_image": args.osrm_image,
    }
    _json_dump(output_dir / "index.json", index)

    audit = {
        "benchmark_path": str(benchmark_path),
        "output_dir": str(output_dir),
        "osrm_data": str(osrm_data),
        "runtime": server.effective_runtime,
        "n_nodes": n_nodes,
        "n_orders": len(orders),
        "duration_unit": "seconds",
        "distance_unit": "meters",
        "block_size": args.block_size,
        "max_table_size": args.max_table_size,
        "elapsed_s": elapsed_s,
        "min_duration_s": int(durations.min()),
        "max_duration_s": int(durations.max()),
        "min_distance_m": int(distances.min()),
        "max_distance_m": int(distances.max()),
        "status_rows": len(status_rows),
    }
    _json_dump(output_dir / "audit" / "matrix_report.json", audit)

    print(
        json.dumps(
            {
                "benchmark": str(benchmark_path),
                "output_dir": str(output_dir),
                "n_nodes": n_nodes,
                "n_orders": len(orders),
                "runtime": server.effective_runtime,
                "elapsed_s": elapsed_s,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
