#!/bin/bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "FATAL: Python runtime not found at $PYTHON_BIN" >&2
    exit 1
fi

export PYTHONPATH=".:src:${PYTHONPATH:-}"
export VRP_MAX_TRIPS_PER_VEHICLE=2

#BSUB -J DATA003_EAST_BAU_V6G60RPT12[1-10]
#BSUB -q hpc
#BSUB -o logs/data003_east_bau_v6g60_w12h_reopt_%I.out
#BSUB -e logs/data003_east_bau_v6g60_w12h_reopt_%I.err
#BSUB -n 1
#BSUB -W 12:00
#BSUB -R "rusage[mem=24GB]"

case $LSB_JOBINDEX in
1) SEED="1" ;;
2) SEED="2" ;;
3) SEED="3" ;;
4) SEED="4" ;;
5) SEED="5" ;;
6) SEED="6" ;;
7) SEED="7" ;;
8) SEED="8" ;;
9) SEED="9" ;;
10) SEED="10" ;;
*) echo "FATAL: unknown LSB_JOBINDEX=$LSB_JOBINDEX" >&2; exit 1 ;;
esac

OVERRIDES=(
  --override "endpoint_key=data003_east_bau_v6g60_w12h_reopt"
  --override "data_file=data/processed/multiday_benchmark_east.json"
  --override "matrix_dir=data/processed/vrp_matrix_east"
  --override "use_robust_controller=true"
  --override "robust_horizon_days=3"
  --override "robust_controller_version=v6g_deadline_reservation_value_rerank"
  --override "v6_value_model_path=data/results/EXP_EXP01/_analysis_v6d_value/v6d_value_model.json"
  --override "base_compute=60"
  --override "high_compute=300"
  --override "mid_compute=180"
  --override "low_mid_compute=120"
  --override "compute_policy=ratio_rule"
  --override "ratio_thresh_high=0.60"
  --override "ratio_thresh_mid=0.70"
  --override "ratio_thresh_low_mid=0.80"
  --override "solver_chunk_seconds=60"
  --override "solver_min_chunks=1"
  --override "solver_max_no_improve_chunks=1"
  --override "solver_continue_improvement_ratio=0.0025"
  --override "solver_enable_incumbent_continuation=true"
  --override "solver_enable_prev_day_route_seed=false"
  --override "warehouse_retry_time_limit_seconds=60"
  --override "warehouse_drop_batch_size=5"
  --override "warehouse_retry_use_initial_routes=true"
  --override "solver_enable_initial_route_seed=true"
  --override "total_days=10"
)

"$PYTHON_BIN" -m scripts.runner.master_runner --exp EXP00 --seed "$SEED" "${OVERRIDES[@]}"
