#!/bin/bash
set -euo pipefail

# OOD dynamic-time tuning experiment.

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "FATAL: Python runtime not found at $PYTHON_BIN" >&2
    exit 1
fi

export PYTHONPATH=".:src:${PYTHONPATH:-}"
export VRP_MAX_TRIPS_PER_VEHICLE=2

#BSUB -J OOD_AALBORG_D60[1-5]
#BSUB -q hpc
#BSUB -o logs/scenario1_ood_aalborg_v6g_v6d_dyn60_cap05_%I.out
#BSUB -e logs/scenario1_ood_aalborg_v6g_v6d_dyn60_cap05_%I.err
#BSUB -n 1
#BSUB -W 04:00
#BSUB -R "rusage[mem=8GB]"

case $LSB_JOBINDEX in
1) SEED="1" ;;
2) SEED="2" ;;
3) SEED="3" ;;
4) SEED="4" ;;
5) SEED="5" ;;
*) echo "FATAL: unknown LSB_JOBINDEX=$LSB_JOBINDEX" >&2; exit 1 ;;
esac

OVERRIDES=(
  --override "use_robust_controller=true"
  --override "robust_horizon_days=3"
  --override "robust_controller_version=v6g_deadline_reservation_value_rerank"
  --override "v6_value_model_path=data/results/EXP_EXP01/_analysis_v6d_value/v6d_value_model.json"
  --override "endpoint_key=scenario1_ood_aalborg_v6g_v6d_dyn60_cap05"
  --override "data_path=data/processed/multiday_benchmark_aalborg.json"
  --override "matrix_dir=data/processed/vrp_matrix_aalborg"
  --override "base_compute=60"
  --override "high_compute=300"
  --override "mid_compute=180"
  --override "low_mid_compute=120"
  --override "compute_policy=ratio_rule"
  --override "ratio_thresh_high=0.60"
  --override "ratio_thresh_mid=0.70"
  --override "ratio_thresh_low_mid=0.80"
  --override "robust_candidate_limit=5"
  --override "solver_chunk_seconds=60"
  --override "solver_min_chunks=1"
  --override "solver_max_no_improve_chunks=1"
  --override "solver_continue_improvement_ratio=0.0025"
  --override "solver_enable_incumbent_continuation=true"
  --override "solver_enable_prev_day_route_seed=false"
)

"$PYTHON_BIN" -m scripts.runner.master_runner --exp EXP01 --seed "$SEED" "${OVERRIDES[@]}"
