#!/usr/bin/env python3
"""
Generate HPC submission scripts for the retained baseline experiments.
"""

import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    from scripts.experiment_definitions import EXPERIMENTS
else:
    from ..experiment_definitions import EXPERIMENTS


def _format_scalar(value):
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def generate_job_script(exp_id, exp_config, output_dir="jobs", mode="proactive"):
    mode = str(mode).lower()
    if mode not in {"proactive", "greedy"}:
        raise ValueError(f"Unsupported mode: {mode}")
    base_mode = str(exp_config.get("params", {}).get("mode", "proactive")).lower()
    effective_mode = mode if mode != "proactive" else base_mode

    resource = exp_config.get("resource", "standard")
    if resource == "heavy":
        walltime = "04:00"
        mem = "8GB"
        slots = 2
    else:
        walltime = "01:00"
        mem = "4GB"
        slots = 1

    tasks = [
        {"seed": int(seed), "endpoint_key": "baseline"}
        for seed in exp_config.get("seeds", [1])
    ]
    array_size = len(tasks)
    job_suffix = "" if effective_mode == "proactive" else f"_{effective_mode}"
    job_name = f"{exp_id}_{exp_config['name']}{job_suffix}"
    log_stem = f"{exp_id.lower()}{job_suffix}"

    case_lines = []
    for idx, task in enumerate(tasks, start=1):
        overrides = [f'--override "endpoint_key={task["endpoint_key"]}"']
        if mode == "greedy":
            overrides.append('--override "mode=greedy"')
        override_str = " ".join(overrides)
        case_lines.append(
            f"""{idx})
    SEED="{task["seed"]}"
    ENDPOINT_KEY="{task["endpoint_key"]}"
    OVERRIDES=({override_str})
    ;;"""
        )
    case_block = "\n".join(case_lines)

    script = f"""#!/bin/bash
set -euo pipefail

#BSUB -J {job_name}[1-{array_size}]
#BSUB -q hpc
#BSUB -o logs/{log_stem}_%I.out
#BSUB -e logs/{log_stem}_%I.err
#BSUB -n {slots}
#BSUB -W {walltime}
#BSUB -R "rusage[mem={mem}]"
{'#BSUB -R "span[hosts=1]"' if slots > 1 else ""}

# {exp_config["description"]} ({effective_mode})

PYTHON_BIN="${{PYTHON_BIN:-/usr/bin/python3}}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "FATAL: Python runtime not found at $PYTHON_BIN" >&2
    exit 1
fi

export PYTHONPATH=".:src:${{PYTHONPATH:-}}"
export VRP_MAX_TRIPS_PER_VEHICLE=2

case $LSB_JOBINDEX in
{case_block}
*)
    echo "FATAL: unknown LSB_JOBINDEX=$LSB_JOBINDEX" >&2
    exit 1
    ;;
esac

echo "Starting {exp_id} - Seed $SEED"
echo "Job ID: $LSB_JOBID, Array Index: $LSB_JOBINDEX"
echo "Endpoint: $ENDPOINT_KEY"
"$PYTHON_BIN" -m scripts.runner.master_runner --exp {exp_id} --seed $SEED "${{OVERRIDES[@]}}"
echo "Completed {exp_id} - Seed $SEED ($ENDPOINT_KEY)"
"""

    output_path = Path(output_dir) / f"submit_{log_stem}.sh"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script)
    os.chmod(output_path, 0o755)
    return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate HPC job scripts")
    parser.add_argument(
        "--all", action="store_true", help="Generate scripts for all experiments"
    )
    parser.add_argument("--exp", type=str, help="Generate a single experiment")
    parser.add_argument(
        "--mode",
        choices=["proactive", "greedy"],
        default="proactive",
        help="Policy mode for generated scripts",
    )
    args = parser.parse_args()

    if args.all:
        for exp_id, exp_config in EXPERIMENTS.items():
            generate_job_script(exp_id, exp_config, mode=args.mode)
        return 0

    if args.exp:
        exp_id = args.exp.upper()
        if exp_id not in EXPERIMENTS:
            print(f"Unknown experiment: {exp_id}")
            return 1
        generate_job_script(exp_id, EXPERIMENTS[exp_id], mode=args.mode)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
