#!/usr/bin/env python3
"""Regenerate embedded data for dashboard_email_demo.html."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = ROOT / "dashboard_email_demo.html"
SUITE_CSV = ROOT / "data/results/EXP_EXP01/_analysis_suite/suite_endpoint_summary.csv"

DETAIL_SPECS = [
    {
        "key": "herlev",
        "name": "Herlev",
        "role": "Mainline",
        "endpoint": "scenario1_robust_v6g_deadline_reservation_v6d_compute300",
        "benchmark": ROOT / "data/processed/multiday_benchmark_herlev.json",
    },
    {
        "key": "east",
        "name": "East",
        "role": "Auxiliary",
        "endpoint": "data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt",
        "benchmark": ROOT / "data/processed/multiday_benchmark_east.json",
    },
    {
        "key": "west",
        "name": "West",
        "role": "Auxiliary",
        "endpoint": "data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt",
        "benchmark": ROOT / "data/processed/multiday_benchmark_west.json",
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def request_json(url: str) -> dict:
    with urlopen(url, timeout=20.0) as response:
        return json.loads(response.read().decode("utf-8"))


def month_label(date_str: str) -> str:
    _, month, day = date_str.split("-")
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    return f"{months[int(month) - 1]} {int(day)}"


def fleet_label(vehicles: list[dict]) -> str:
    return " + ".join(
        f"{int(vehicle['count'])} {vehicle['type_name']}" for vehicle in vehicles
    )


def load_suite_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with SUITE_CSV.open() as handle:
        for row in csv.DictReader(handle):
            rows[row["endpoint"]] = row
    return rows


def fetch_osrm_polyline(
    coordinates: list[list[float]],
    osrm_url: str | None,
) -> str | None:
    if not osrm_url or len(coordinates) < 2:
        return None
    coord_str = ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in coordinates)
    url = (
        f"{osrm_url.rstrip('/')}/route/v1/driving/{quote(coord_str, safe=';,')}"
        "?overview=full&geometries=polyline6&steps=false"
    )
    try:
        payload = request_json(url)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    if payload.get("code") != "Ok":
        return None
    routes = payload.get("routes") or []
    if not routes:
        return None
    return routes[0].get("geometry")


def build_city_compare() -> list[dict]:
    suite_rows = load_suite_rows()
    items = []
    for spec in DETAIL_SPECS:
        row = suite_rows[spec["endpoint"]]
        benchmark = load_json(spec["benchmark"])
        if row["days_total_max"]:
            horizon_days = int(row["days_total_max"])
        else:
            start = benchmark["metadata"]["horizon_start"]
            end = benchmark["metadata"]["horizon_end"]
            horizon_days = int(end.split("-")[2]) - int(start.split("-")[2]) + 1
        items.append(
            {
                "key": spec["key"],
                "name": spec["name"],
                "role": spec["role"],
                "endpoint": spec["endpoint"],
                "orders": int(round(float(row["eligible_count_mean"]))),
                "service_rate": round(float(row["service_rate_mean"]) * 100.0, 2),
                "failed_orders": round(float(row["failed_orders_mean"]), 1),
                "cost_per_order": round(float(row["cost_per_order_mean"]), 2),
                "load_mse": round(float(row["load_mse_mean"]), 1),
                "horizon_days": horizon_days,
            }
        )
    return items


def build_detail_dataset(
    spec: dict,
    osrm_url: str | None,
    detail_seed: int = 1,
) -> tuple[dict, list[dict]]:
    benchmark = load_json(spec["benchmark"])
    base = (
        ROOT
        / "data/results/EXP_EXP01/_retained"
        / spec["endpoint"]
        / f"Seed_{detail_seed}"
    )
    simulation = load_json(base / "simulation_results.json")
    summary = load_json(base / "summary_final.json")

    orders = benchmark["orders"]
    order_by_id = {int(order["id"]): order for order in orders}
    node_coords = {str(int(order["id"])): order["location"] for order in orders}

    delivered_ids: set[int] = set()
    for trace in simulation["vrp_audit_traces"]:
        delivered_ids.update(int(order_id) for order_id in trace["delivered_order_ids"])

    all_ids = set(order_by_id)
    failed_ids = sorted(all_ids - delivered_ids)
    failure_day = {
        order_id: max(order_by_id[order_id]["feasible_dates"])
        for order_id in failed_ids
    }
    failure_by_day = Counter(failure_day.values())

    order_meta = {}
    for order_id, order in order_by_id.items():
        order_meta[str(order_id)] = {
            "r": order["release_date"],
            "d": max(order["feasible_dates"]),
            "f": order["feasible_dates"],
            "tw": order["time_window"],
            "c": order["demand"]["colli"],
            "v": order["demand"]["volume"],
            "w": order["demand"]["weight"],
            "flex": bool(order["is_flexible"]),
            "wd": order["delivery_window_days"],
            "n": order_id,
        }

    total_colli_capacity = sum(
        int(vehicle["count"]) * float(vehicle["capacity"]["colli"])
        for vehicle in benchmark["vehicles"]
    )
    total_time_capacity = sum(
        int(vehicle["count"]) * float(vehicle["max_duration_hours"]) * 60.0
        for vehicle in benchmark["vehicles"]
    )

    daily_flow = []
    bottleneck = []
    for day_stats, audit in zip(
        simulation["daily_stats"], simulation["vrp_audit_traces"]
    ):
        date = day_stats["date"]
        day_failed_ids = sorted(
            order_id
            for order_id, failure_date in failure_day.items()
            if failure_date == date
        )
        routes = []
        active_vehicles = set()
        route_minutes = 0.0
        for route in audit["routes"]:
            vehicle_id = int(route["vehicle_id"])
            active_vehicles.add(vehicle_id)
            route_minutes += float(route["duration_min"])
            stop_details = [
                {
                    "order_id": int(stop["order_id"]),
                    "node": int(stop["order_id"]),
                    "arrival": round(float(stop["arrival_min"]), 1),
                    "tw_start": round(float(stop["time_window_start_min"]), 1),
                    "tw_end": round(float(stop["time_window_end_min"]), 1),
                }
                for stop in route["stop_details"]
            ]
            geometry_polyline = fetch_osrm_polyline(
                [benchmark["depot"]["location"]]
                + [
                    order_by_id[int(stop["order_id"])]["location"]
                    for stop in route["stop_details"]
                ]
                + [benchmark["depot"]["location"]],
                osrm_url,
            )
            routes.append(
                {
                    "vehicle": vehicle_id,
                    "trip": int(route["trip_id"]),
                    "stops": [int(stop_id) for stop_id in route["stops"]],
                    "duration": round(float(route["duration_min"]), 1),
                    "stop_details": stop_details,
                    "geometry_polyline": geometry_polyline,
                }
            )

        cap_ratio = float(day_stats["capacity_ratio"])
        effective_colli_capacity = (
            total_colli_capacity * cap_ratio if cap_ratio else 0.0
        )
        effective_time_capacity = total_time_capacity * cap_ratio if cap_ratio else 0.0
        colli_util = (
            (float(day_stats["served_colli"]) / effective_colli_capacity) * 100.0
            if effective_colli_capacity
            else 0.0
        )
        time_util = (
            (route_minutes / effective_time_capacity) * 100.0
            if effective_time_capacity
            else 0.0
        )
        bottleneck.append(
            {
                "date": date,
                "label": month_label(date),
                "delivered": int(day_stats["delivered_today"]),
                "dropped": int(failure_by_day.get(date, 0)),
                "vehicles": len(active_vehicles),
                "time_util": round(time_util, 1),
                "colli_util": round(colli_util, 1),
                "cap_ratio": round(cap_ratio, 2),
            }
        )
        daily_flow.append(
            {
                "date": date,
                "visible": int(day_stats["visible_open_orders"]),
                "planned": int(day_stats["planned_today"]),
                "delivered": int(day_stats["delivered_today"]),
                "dropped": len(day_failed_ids),
                "delivered_ids": [
                    int(order_id) for order_id in audit["delivered_order_ids"]
                ],
                "dropped_ids": day_failed_ids,
                "routes": routes,
            }
        )

    data = {
        "daily_flow": daily_flow,
        "has_spatial_detail": True,
        "daily_stats": [
            {
                "date": day["date"],
                "cost": round(float(day["cost"]), 3),
                "served_colli": round(float(day["served_colli"]), 1),
                "vrp_routes": int(day["vrp_routes"]),
                "vrp_avg_dist": round(float(day["vrp_avg_dist"]), 2),
                "vrp_dropped": int(day["vrp_dropped"]),
                "failures": int(day["failures"]),
                "visible": int(day["visible_open_orders"]),
                "planned": int(day["planned_today"]),
                "delivered": int(day["delivered_today"]),
                "capacity": round(float(day["capacity"]), 1),
                "mode": str(day["mode_status"]),
            }
            for day in simulation["daily_stats"]
        ],
        "node_coords": node_coords,
        "order_meta": order_meta,
        "depot": benchmark["depot"]["location"],
        "summary": {
            "city_key": spec["key"],
            "city_name": spec["name"],
            "role": spec["role"],
            "total_orders": int(summary["eligible_count"]),
            "delivered": int(summary["delivered_within_window_count"]),
            "failed": int(summary["failed_orders"]),
            "service_rate": round(
                float(summary["service_rate_within_window"]) * 100.0,
                2,
            ),
            "cost_raw": round(float(summary["cost_raw"]), 2),
            "cost_per_order": round(float(summary["cost_per_order"]), 2),
            "horizon": (
                f"{benchmark['metadata']['horizon_start']} to {benchmark['metadata']['horizon_end']}"
            ),
            "fleet": fleet_label(benchmark["vehicles"]),
            "strategy": str(summary["strategy"]),
            "source_endpoint": spec["endpoint"],
            "detail_seed": detail_seed,
            "has_osrm_geometry": any(
                route.get("geometry_polyline")
                for day in daily_flow
                for route in day["routes"]
            ),
        },
    }
    return data, bottleneck


def build_detail_bundle(
    osrm_url: str | None,
) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    detail_data = {}
    detail_bottleneck = {}
    for spec in DETAIL_SPECS:
        data, bottleneck = build_detail_dataset(spec, osrm_url=osrm_url)
        detail_data[spec["key"]] = data
        detail_bottleneck[spec["key"]] = bottleneck
    return detail_data, detail_bottleneck


def replace_constants(
    html_text: str,
    detail_data: dict[str, dict],
    detail_bottleneck: dict[str, list[dict]],
    city_compare: list[dict],
) -> str:
    block = (
        "const HERLEV_DATA = "
        + json.dumps(detail_data["herlev"], ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        + "const HERLEV_BOTTLENECK = "
        + json.dumps(detail_bottleneck["herlev"], ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        + "const EAST_DATA = "
        + json.dumps(detail_data["east"], ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        + "const EAST_BOTTLENECK = "
        + json.dumps(detail_bottleneck["east"], ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        + "const WEST_DATA = "
        + json.dumps(detail_data["west"], ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        + "const WEST_BOTTLENECK = "
        + json.dumps(detail_bottleneck["west"], ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        + "const DETAIL_DATA = {herlev: HERLEV_DATA, east: EAST_DATA, west: WEST_DATA};\n"
        + "const DETAIL_BOTTLENECK = {herlev: HERLEV_BOTTLENECK, east: EAST_BOTTLENECK, west: WEST_BOTTLENECK};\n"
        + "const CITY_COMPARE = "
        + json.dumps(city_compare, ensure_ascii=False, separators=(",", ":"))
        + ";\n\n"
    )
    pattern = r"const HERLEV_DATA = .*?const VEHICLE_COLORS ="
    replacement = block + "const VEHICLE_COLORS ="
    updated, count = re.subn(pattern, replacement, html_text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Could not locate embedded dashboard data block")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate embedded dashboard data with optional OSRM route geometry.",
    )
    parser.add_argument(
        "--osrm-url",
        default=None,
        help="Base URL of a running OSRM service, e.g. http://127.0.0.1:5080",
    )
    args = parser.parse_args()

    detail_data, detail_bottleneck = build_detail_bundle(osrm_url=args.osrm_url)
    city_compare = build_city_compare()
    html_text = HTML_PATH.read_text()
    updated = replace_constants(html_text, detail_data, detail_bottleneck, city_compare)
    HTML_PATH.write_text(updated)
    print(HTML_PATH)


if __name__ == "__main__":
    main()
