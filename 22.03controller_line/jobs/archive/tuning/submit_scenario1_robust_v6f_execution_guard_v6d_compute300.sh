#!/bin/bash
set -euo pipefail

#BSUB -J SCENARIO1_RobustV6FExec_V6D_T300[1-10]
#BSUB -q hpc
#BSUB -o logs/scenario1_robust_v6f_execution_guard_v6d_compute300_%I.out
#BSUB -e logs/scenario1_robust_v6f_execution_guard_v6d_compute300_%I.err
#BSUB -n 1
#BSUB -W 04:00
#BSUB -R "rusage[mem=8GB]"

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
  --override "endpoint_key=scenario1_robust_v6f_execution_guard_v6d_compute300"
  --override "use_robust_controller=true"
  --override "robust_horizon_days=3"
  --override "robust_controller_version=v6f_execution_guard_value_rerank"
  --override "v6_value_model_path=data/results/EXP_EXP01/_analysis_v6d_value/v6d_value_model.json"
  --override "base_compute=300"
  --override "high_compute=300"
)

"$PYTHON_BIN" -m scripts.runner.master_runner --exp EXP01 --seed "$SEED" "${OVERRIDES[@]}"
