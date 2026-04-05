#!/bin/bash
set -euo pipefail

# Herlev Scenario1 v6g cap05 dynamic-time fine-tuning experiment.

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "FATAL: Python runtime not found at $PYTHON_BIN" >&2
    exit 1
fi

export PYTHONPATH=".:src:${PYTHONPATH:-}"
export VRP_MAX_TRIPS_PER_VEHICLE=2

#BSUB -J SC1_V6G_CAP05_DYN90[1-10]
#BSUB -q hpc
#BSUB -o logs/scenario1_robust_v6g_deadline_reservation_v6d_dynrule_noseed_cap05_chunk90_%I.out
#BSUB -e logs/scenario1_robust_v6g_deadline_reservation_v6d_dynrule_noseed_cap05_chunk90_%I.err
#BSUB -n 1
#BSUB -W 06:00
#BSUB -R "rusage[mem=8GB]"

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
  --override "matrix_dir=/zhome/2a/1/202283/thesis/22.03controller_line/data/processed/vrp_matrix_latest"
  --override "use_robust_controller=true"
  --override "robust_horizon_days=3"
  --override "robust_controller_version=v6g_deadline_reservation_value_rerank"
  --override "v6_value_model_path=data/results/EXP_EXP01/_analysis_v6d_value/v6d_value_model.json"
  --override "robust_candidate_limit=5"
  --override "base_compute=60"
  --override "high_compute=300"
  --override "mid_compute=180"
  --override "low_mid_compute=120"
  --override "compute_policy=ratio_rule"
  --override "ratio_thresh_high=0.60"
  --override "ratio_thresh_mid=0.70"
  --override "ratio_thresh_low_mid=0.80"
  --override "solver_min_chunks=1"
  --override "solver_enable_incumbent_continuation=true"
  --override "solver_enable_prev_day_route_seed=false"
  --override "endpoint_key=scenario1_robust_v6g_deadline_reservation_v6d_dynrule_noseed_cap05_chunk90"
  --override "solver_chunk_seconds=90"
  --override "solver_max_no_improve_chunks=1"
  --override "solver_continue_improvement_ratio=0.0025"
)

"$PYTHON_BIN" -m scripts.runner.master_runner --exp EXP01 --seed "$SEED" "${OVERRIDES[@]}"
