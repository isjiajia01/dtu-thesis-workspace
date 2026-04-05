#!/usr/bin/env python3
"""
Master runner for the retained EXP00/EXP01 experiment set.
"""

import argparse
import json
import os
import shutil
import sys
import traceback
from datetime import datetime
from importlib import import_module
from pathlib import Path

from .. import ensure_src
from ..experiment_definitions import EXPERIMENTS
from src.results_layout import classify_exp01_endpoint

ensure_src()
run_rolling_horizon = import_module(
    "src.simulation.rolling_horizon_integrated"
).run_rolling_horizon


def _is_lsf_job() -> bool:
    return bool(os.environ.get("LSB_JOBID"))


def _allow_local_run() -> bool:
    return os.environ.get("ALLOW_LOCAL_EXPERIMENT_RUN", "").strip() == "1"


def _cleanup_failed_run(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)


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


def _safe_print_json(payload) -> None:
    _safe_print(json.dumps(payload, indent=2))


def _safe_print_exc() -> None:
    stream = getattr(sys, "stderr", None) or sys.__stderr__
    if stream is None:
        return
    try:
        traceback.print_exc(file=stream)
        stream.flush()
    except (BrokenPipeError, OSError, ValueError):
        _disable_stdio()


def parse_overrides(override_args):
    overrides = {}
    for arg in override_args or []:
        if "=" not in arg:
            continue
        key, value = arg.split("=", 1)
        lower = value.lower()
        if lower == "true":
            value = True
        elif lower == "false":
            value = False
        elif lower == "none":
            value = None
        else:
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
        overrides[key] = value
    return overrides


def merge_config(base_params, overrides):
    merged = base_params.copy()
    merged.update(overrides)
    return merged


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=lambda item: str(item))]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass
    if hasattr(value, "tolist"):
        try:
            return _json_safe(value.tolist())
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def validate_concrete_params(exp_id, exp_config, params):
    unresolved = [
        key for key in ("ratios", "max_trips_list", "variants") if key in params
    ]
    if unresolved:
        raise ValueError(f"{exp_id} still has unresolved sweep keys: {unresolved}")


def create_output_dir(exp_id, seed, overrides=None):
    base_dir = Path("data/results") / f"EXP_{exp_id}"
    overrides = overrides or {}
    endpoint_key = overrides.get("endpoint_key")
    if exp_id == "EXP01" and not endpoint_key:
        endpoint_key = "baseline"
    if endpoint_key:
        if exp_id == "EXP01":
            base_dir = base_dir / classify_exp01_endpoint(str(endpoint_key)) / str(endpoint_key)
        else:
            base_dir = base_dir / str(endpoint_key)
    elif overrides:
        suffix_parts = []
        for key in ("ratio", "max_trips", "base_compute", "mode"):
            if key in overrides:
                suffix_parts.append(f"{key}_{overrides[key]}")
        if suffix_parts:
            base_dir = base_dir / "_".join(suffix_parts)
    output_dir = base_dir / f"Seed_{seed}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_config_dump(output_dir, exp_id, seed, params, overrides):
    config_dump = {
        "experiment_id": exp_id,
        "seed": seed,
        "timestamp": datetime.now().isoformat(),
        "parameters": params,
        "overrides_applied": overrides if overrides else {},
        "merge_rule": "experiment_definition < job_override",
    }
    config_path = output_dir / "config_dump.json"
    config_path.write_text(json.dumps(config_dump, indent=2))
    return config_path


def run_simulation(exp_id, seed, params, output_dir):
    config = params.copy()
    base_compute = int(config.get("base_compute", 60))
    high_compute = int(config.get("high_compute", base_compute))
    config["capacity_ratio"] = config.pop("ratio", 1.0)
    config["total_days"] = int(config.get("total_days", 12))
    config["seed"] = seed
    config["results_dir"] = "data/results"
    config["base_compute"] = base_compute
    config["high_compute"] = high_compute
    config["mode"] = config.get("mode", "proactive")
    config["compute_policy"] = config.get("compute_policy", "static")
    config["max_trips_per_vehicle"] = int(config.pop("max_trips", 2))
    endpoint_key = str(params.get("endpoint_key", "baseline"))
    run_id = config.get("run_id")
    if not run_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_endpoint = endpoint_key.replace("/", "_").replace(" ", "_")
        config["run_id"] = f"{timestamp}_{safe_endpoint}_seed{seed}"
    config["base_dir"] = str(output_dir)
    if params.get("crunch_start") is not None:
        config["crunch_start"] = params["crunch_start"]
        config["crunch_end"] = params["crunch_end"]
    os.environ["VRP_TIME_LIMIT_SECONDS"] = str(base_compute)
    os.environ["VRP_HIGH_COMPUTE_LIMIT"] = str(high_compute)
    os.environ["VRP_MAX_TRIPS_PER_VEHICLE"] = str(int(params.get("max_trips", 2)))

    try:
        results = run_rolling_horizon(config)
        results_path = output_dir / "simulation_results.json"
        results_path.write_text(json.dumps(_json_safe(results), indent=2))
        return results
    except Exception:
        import traceback

        _safe_print_exc()
        _cleanup_failed_run(output_dir)
        return None


def extract_summary(output_dir, results):
    if results is None:
        return None
    summary = results.get("summary", {})
    summary_path = output_dir / "summary_final.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description="EXP00/EXP01 runner")
    parser.add_argument("--exp", type=str, required=True, help="Experiment ID")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    parser.add_argument(
        "--override", action="append", help="Override parameter (key=value)"
    )
    parser.add_argument(
        "--override_json", type=str, help="Path to JSON file with overrides"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print config without running"
    )
    args = parser.parse_args()

    if not args.dry_run and not _is_lsf_job() and not _allow_local_run():
        _safe_print("Refusing to run experiment locally.")
        _safe_print("Submit through HPC (LSF / bsub) instead.")
        _safe_print("Use --dry-run for config inspection only.")
        _safe_print("Escape hatch for maintenance only: ALLOW_LOCAL_EXPERIMENT_RUN=1")
        return 2

    exp_id = args.exp.upper()
    if exp_id not in EXPERIMENTS:
        _safe_print(f"Unknown experiment: {exp_id}")
        _safe_print(f"Available: {', '.join(EXPERIMENTS.keys())}")
        return 1

    exp_config = EXPERIMENTS[exp_id]
    overrides = {}
    if args.override_json:
        overrides.update(json.loads(Path(args.override_json).read_text()))
    overrides.update(parse_overrides(args.override))
    params = merge_config(exp_config["params"].copy(), overrides)
    validate_concrete_params(exp_id, exp_config, params)

    output_dir = create_output_dir(exp_id, args.seed, overrides)
    save_config_dump(output_dir, exp_id, args.seed, params, overrides)
    if args.dry_run:
        _safe_print_json({"exp": exp_id, "seed": args.seed, "params": params})
        return 0

    results = run_simulation(exp_id, args.seed, params, output_dir)
    if not results:
        _cleanup_failed_run(output_dir)
        return 1
    summary = extract_summary(output_dir, results) or {}
    _safe_print_json(
        {
            "exp": exp_id,
            "seed": args.seed,
            "service_rate": summary.get(
                "service_rate_within_window", summary.get("service_rate")
            ),
            "cost_raw": summary.get("cost_raw"),
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
