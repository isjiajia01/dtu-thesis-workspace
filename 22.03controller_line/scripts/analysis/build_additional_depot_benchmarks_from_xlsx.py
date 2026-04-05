#!/usr/bin/env python3
"""
Build processed multi-day benchmark JSON files for non-Herlev depots from the
raw Excel workbook used in 22.02.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_XLSX = Path("../22.02thesis/data/raw/RangeOfDaysSimulationDataTemplate - Test Data 001.xlsx")
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed"
EXCEL_EPOCH = datetime(1899, 12, 30)

# Public address pages were used only to recover missing warehouse coordinates
# for the three non-Herlev depots absent from the workbook warehouse sheet.
DEPOT_COORD_OVERRIDES = {
    "Aalborg": [57.0381306, 9.9246674],
    "Odense": [55.3602445, 10.3399254],
    "Aabyhoj": [56.15071261, 10.17171014],
}

DEPOT_NAME_MAP = {
    "Herlev": "Herlev",
    "Aalborg": "Aalborg",
    "Odense": "Odense",
    "Åbyhøj": "Aabyhoj",
    "Aabyhøj": "Aabyhoj",
}

NS_MAIN = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_REL = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def col_to_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref)
    if not letters:
        return 0
    value = 0
    for char in letters.group(0):
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def load_sheet_rows(xlsx_path: Path, sheet_name: str) -> list[list[str]]:
    with zipfile.ZipFile(xlsx_path) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", NS_MAIN):
                shared_strings.append("".join((t.text or "") for t in si.iterfind(".//a:t", NS_MAIN)))

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels
        }

        target = None
        for sheet in workbook.find("a:sheets", NS_MAIN):
            if sheet.attrib["name"] == sheet_name:
                rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                target = "xl/" + rel_map[rid]
                break
        if target is None:
            raise ValueError(f"Sheet not found: {sheet_name}")

        root = ET.fromstring(zf.read(target))
        rows: list[list[str]] = []
        for row in root.find("a:sheetData", NS_MAIN).findall("a:row", NS_MAIN):
            values_by_idx: dict[int, str] = {}
            max_idx = -1
            for cell in row.findall("a:c", NS_MAIN):
                idx = col_to_index(cell.attrib["r"])
                max_idx = max(max_idx, idx)
                value_node = cell.find("a:v", NS_MAIN)
                text = ""
                if value_node is not None:
                    text = value_node.text or ""
                    if cell.attrib.get("t") == "s":
                        text = shared_strings[int(text)]
                values_by_idx[idx] = text
            if max_idx < 0:
                rows.append([])
                continue
            rows.append([values_by_idx.get(i, "") for i in range(max_idx + 1)])
        return rows


def parse_records(rows: list[list[str]]) -> list[dict[str, str]]:
    if len(rows) < 2:
        return []
    header = rows[1]
    records: list[dict[str, str]] = []
    for row in rows[2:]:
        if not any(str(v).strip() for v in row):
            continue
        padded = row + [""] * (len(header) - len(row))
        records.append({str(header[i]).strip(): str(padded[i]).strip() for i in range(len(header))})
    return records


def excel_serial_to_date(value: str) -> str:
    days = int(float(value))
    return (EXCEL_EPOCH + timedelta(days=days)).strftime("%Y-%m-%d")


def excel_fraction_to_minutes(value: str) -> int:
    return int(round(float(value) * 24 * 60))


def clean_address(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", ", ")).strip(" ,")


def normalize_depot_name(raw_name: str) -> str:
    name = str(raw_name).strip()
    return DEPOT_NAME_MAP.get(name, name)


def build_depot_dataset(
    *,
    depot_name: str,
    orders: list[dict[str, str]],
    warehouses: dict[str, dict[str, str]],
    vehicles: list[dict[str, str]],
) -> dict[str, object]:
    canonical = normalize_depot_name(depot_name)
    wh = warehouses[canonical]

    earliest_release = min(excel_serial_to_date(order["DateRequested"]) for order in orders)
    earliest_delivery = min(excel_serial_to_date(order["DeliveryDateFrom"]) for order in orders)
    latest_delivery = max(excel_serial_to_date(order["DeliveryDateFrom2"]) for order in orders)

    depot_location = [
        float(wh["Latitude"]),
        float(wh["Longitude"]),
    ] if wh.get("Latitude") and wh.get("Longitude") else DEPOT_COORD_OVERRIDES[canonical]

    dataset = {
        "metadata": {
            "description": "Multi-day Rolling Horizon Dataset",
            "depot_name": canonical,
            "source_workbook": DEFAULT_XLSX.name,
            "horizon_start": earliest_delivery,
            "horizon_end": latest_delivery,
            "total_orders_in_file": len(orders),
        },
        "depot": {
            "name": canonical,
            "location": depot_location,
            "opening_time": excel_fraction_to_minutes(wh["EarliestArrival"]),
            "closing_time": excel_fraction_to_minutes(wh["LatestDeparture"]),
            "picking_open_min": excel_fraction_to_minutes(wh["PickingOpeningHours"]),
            "picking_close_min": excel_fraction_to_minutes(wh["PickingClosingHours"]),
            "gates": int(float(wh["Gates"])),
            "picking_capacity": {
                "colli_per_hour": float(wh["PickingCapacityColliPerHour"]),
                "volume_per_hour": float(wh["PickingCapacityVolumePerHour"]),
                "max_staging_volume": float(wh["MaxStagingSpace"]),
            },
            "loading_time_minutes": int(float(wh["VehicleLoadingTime"])),
            "unloading_time_minutes": int(float(wh["VehicleUnloadingTime"])),
            "pickup_address": clean_address(next(order["PickupAddress"] for order in orders if order.get("PickupAddress"))),
            "raw_name": depot_name,
        },
        "vehicles": [],
        "orders": [],
    }

    for vehicle in vehicles:
        if normalize_depot_name(vehicle["Depot"]) != canonical:
            continue
        dataset["vehicles"].append(
            {
                "type_name": vehicle["VehicleTypeName"],
                "count": int(float(vehicle["Number of vehicles"])),
                "depot": canonical,
                "capacity": {
                    "colli": float(vehicle["CapacityColliCount"]),
                    "volume": float(vehicle["CapacityVolume"]),
                    "weight": float(vehicle["CapacityWeight"]),
                },
                "max_duration_hours": float(vehicle["MaxRouteDuration"]),
                "max_distance_km": float(vehicle["MaxRouteDistance"]),
            }
        )

    for idx, order in enumerate(orders):
        release_date = excel_serial_to_date(order["DateRequested"])
        start_date = excel_serial_to_date(order["DeliveryDateFrom"])
        end_date = excel_serial_to_date(order["DeliveryDateFrom2"])
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        feasible_dates = [
            (start_dt + timedelta(days=offset)).strftime("%Y-%m-%d")
            for offset in range((end_dt - start_dt).days + 1)
        ]
        dataset["orders"].append(
            {
                "id": idx,
                "original_id": str(idx),
                "feasible_dates": feasible_dates,
                "location": [
                    float(order["DeliveryLatitude"]),
                    float(order["DeliveryLongitude"]),
                ],
                "demand": {
                    "colli": float(order["ColliCount"]),
                    "volume": float(order["Volume"]),
                    "weight": float(order["Weight"]),
                },
                "time_window": [
                    excel_fraction_to_minutes(order["DeliveryEarliestTime"]),
                    excel_fraction_to_minutes(order["DeliveryLatestTime"]),
                ],
                "service_time": int(float(order["DeliveryTaskTime"])),
                "order_date": release_date,
                "release_date": release_date,
                "is_flexible": len(feasible_dates) > 1,
                "delivery_window_days": len(feasible_dates),
                "pickup_address": clean_address(order["PickupAddress"]),
                "delivery_address": clean_address(order["DeliveryAddress"]),
                "raw_depot": depot_name,
            }
        )

    return dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Build processed benchmark JSONs for non-Herlev depots from raw XLSX")
    parser.add_argument("--xlsx", default=str(DEFAULT_XLSX))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    orders_records = parse_records(load_sheet_rows(xlsx_path, "Orders"))
    warehouse_records = parse_records(load_sheet_rows(xlsx_path, "Warehouses"))
    vehicle_records = parse_records(load_sheet_rows(xlsx_path, "Vehicles Settings"))

    warehouses = {normalize_depot_name(row["StartLocation"]): row for row in warehouse_records}
    depots = ["Aalborg", "Odense", "Aabyhoj"]

    for depot in depots:
        depot_orders = [row for row in orders_records if normalize_depot_name(row["Depot"]) == depot]
        if not depot_orders:
            raise ValueError(f"No orders found for depot {depot}")
        dataset = build_depot_dataset(
            depot_name=depot,
            orders=depot_orders,
            warehouses=warehouses,
            vehicles=vehicle_records,
        )
        out_path = output_dir / f"multiday_benchmark_{depot.lower()}.json"
        out_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))
        print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
