from __future__ import annotations

from pathlib import Path

EXP01_RETAINED_ENDPOINTS = {
    "baseline",
    "scenario1_robust_v2_compute300",
    "scenario1_robust_v4_event_commitment_compute300",
    "scenario1_robust_v5_risk_budgeted_compute300",
    "scenario1_robust_v6f_execution_guard_compute300",
    "scenario1_robust_v6g_deadline_reservation_v6d_compute300",
    "scenario1_robust_v6g_deadline_reservation_v6d_compute300_cap05",
    "scenario1_robust_v6g_deadline_reservation_v6d_automode",
    "scenario1_robust_v6g_deadline_reservation_v6d_fixed300_cap05_control",
    "scenario1_ood_aalborg_v6g_v6d_compute300",
    "scenario1_ood_odense_v6g_v6d_compute300",
    "scenario1_ood_aabyhoj_v6g_v6d_compute300",
    "data003_east_crunch_r060_v6g_v6d_compute300_w12h_dyn90_reopt",
    "data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt",
}


def _is_analysis_path(path: Path) -> bool:
    return any(part.startswith("_analysis") for part in path.parts)


def iter_endpoint_dirs(results_dir: str | Path) -> list[Path]:
    root = Path(results_dir)
    endpoint_dirs: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_dir():
            continue
        if _is_analysis_path(path.relative_to(root)):
            continue
        if any(child.is_dir() and child.name.startswith("Seed_") for child in path.iterdir()):
            endpoint_dirs.append(path)
    return endpoint_dirs


def find_endpoint_dir(results_dir: str | Path, endpoint_name: str) -> Path:
    matches = [path for path in iter_endpoint_dirs(results_dir) if path.name == endpoint_name]
    if not matches:
        raise FileNotFoundError(f"Endpoint {endpoint_name!r} not found under {results_dir}")
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in matches)
        raise ValueError(f"Endpoint {endpoint_name!r} is ambiguous under {results_dir}: {joined}")
    return matches[0]


def find_seed_dir(result_file: str | Path, *, results_dir: str | Path | None = None) -> Path:
    path = Path(result_file)
    stop = Path(results_dir).resolve() if results_dir is not None else None
    for parent in path.parents:
        if parent.name.startswith("Seed_"):
            return parent
        if stop is not None and parent.resolve() == stop:
            break
    raise ValueError(f"Could not locate Seed_* ancestor for {path}")


def endpoint_name_from_result_file(result_file: str | Path, *, results_dir: str | Path | None = None) -> str:
    seed_dir = find_seed_dir(result_file, results_dir=results_dir)
    return seed_dir.parent.name


def classify_exp01_endpoint(endpoint_name: str) -> str:
    return "_retained" if endpoint_name in EXP01_RETAINED_ENDPOINTS else "_historical"
