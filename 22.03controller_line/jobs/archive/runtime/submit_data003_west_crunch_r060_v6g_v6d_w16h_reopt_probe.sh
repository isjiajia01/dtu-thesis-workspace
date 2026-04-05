#!/bin/bash
set -euo pipefail

#BSUB -J DATA003_WEST_R060_V6G300RPTPROBE
#BSUB -q hpc
#BSUB -o logs/data003_west_r060_v6g300_w16h_reopt_probe.out
#BSUB -e logs/data003_west_r060_v6g300_w16h_reopt_probe.err
#BSUB -n 1
#BSUB -W 04:00
#BSUB -R "rusage[mem=48GB]"

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "FATAL: Python runtime not found at $PYTHON_BIN" >&2
    exit 1
fi

export PYTHONPATH=".:src:${PYTHONPATH:-}"
export VRP_MAX_TRIPS_PER_VEHICLE=2
SEED=1

OVERRIDES=(
  --override "endpoint_key=data003_west_crunch_r060_v6g_v6d_compute300_w16h_reopt_probe"
  --override "data_file=data/processed/multiday_benchmark_west.json"
  --override "matrix_dir=data/processed/vrp_matrix_west"
  --override "ratio=0.6"
  --override "total_days=11"
  --override "crunch_start=5"
  --override "crunch_end=10"
  --override "use_robust_controller=true"
  --override "robust_horizon_days=3"
  --override "robust_controller_version=v6g_deadline_reservation_value_rerank"
  --override "v6_value_model_path=data/results/EXP_EXP01/_analysis_v6d_value/v6d_value_model.json"
  --override "base_compute=300"
  --override "high_compute=300"
  --override "warehouse_retry_time_limit_seconds=60"
  --override "warehouse_drop_batch_size=8"
  --override "warehouse_retry_use_initial_routes=true"
  --override "solver_enable_initial_route_seed=true"
)

"$PYTHON_BIN" -m scripts.runner.master_runner --exp EXP01 --seed "$SEED" "${OVERRIDES[@]}"
