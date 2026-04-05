#!/bin/bash
set -euo pipefail

# Rerun variant to avoid clobbering the currently running arrays.

#BSUB -J DATA003_WEST_BAU_V6G300R2[1-10]
#BSUB -q hpc
#BSUB -o logs/data003_west_bau_v6g300_r2_%I.out
#BSUB -e logs/data003_west_bau_v6g300_r2_%I.err
#BSUB -n 1
#BSUB -W 08:00
#BSUB -R "rusage[mem=24GB]"

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "FATAL: Python runtime not found at $PYTHON_BIN" >&2
    exit 1
fi

export PYTHONPATH=".:src:${PYTHONPATH:-}"
export VRP_MAX_TRIPS_PER_VEHICLE=2

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
  --override "endpoint_key=data003_west_bau_v6g_v6d_compute300_r2"
  --override "data_file=data/processed/multiday_benchmark_west.json"
  --override "matrix_dir=data/processed/vrp_matrix_west"
  --override "total_days=11"
  --override "use_robust_controller=true"
  --override "robust_horizon_days=3"
  --override "robust_controller_version=v6g_deadline_reservation_value_rerank"
  --override "v6_value_model_path=data/results/EXP_EXP01/_analysis_v6d_value/v6d_value_model.json"
  --override "base_compute=300"
  --override "high_compute=300"
)

"$PYTHON_BIN" -m scripts.runner.master_runner --exp EXP00 --seed "$SEED" "${OVERRIDES[@]}"
