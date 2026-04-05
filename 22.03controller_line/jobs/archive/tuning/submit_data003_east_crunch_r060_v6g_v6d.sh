#!/bin/bash
set -euo pipefail

#BSUB -J DATA003_EAST_R060_V6G300[1-10]
#BSUB -q hpc
#BSUB -o logs/data003_east_r060_v6g300_%I.out
#BSUB -e logs/data003_east_r060_v6g300_%I.err
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
  --override "endpoint_key=data003_east_crunch_r060_v6g_v6d_compute300"
  --override "data_file=data/processed/multiday_benchmark_east.json"
  --override "matrix_dir=data/processed/vrp_matrix_east"
  --override "ratio=0.6"
  --override "total_days=10"
  --override "crunch_start=5"
  --override "crunch_end=9"
  --override "use_robust_controller=true"
  --override "robust_horizon_days=3"
  --override "robust_controller_version=v6g_deadline_reservation_value_rerank"
  --override "v6_value_model_path=data/results/EXP_EXP01/_analysis_v6d_value/v6d_value_model.json"
  --override "base_compute=300"
  --override "high_compute=300"
)

"$PYTHON_BIN" -m scripts.runner.master_runner --exp EXP01 --seed "$SEED" "${OVERRIDES[@]}"
