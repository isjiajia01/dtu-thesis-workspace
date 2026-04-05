#!/bin/bash
set -euo pipefail

#BSUB -J EXP-BASELINE_exp-baseline_greedy[1-10]
#BSUB -q hpc
#BSUB -o logs/exp-baseline_greedy_%I.out
#BSUB -e logs/exp-baseline_greedy_%I.err
#BSUB -n 1
#BSUB -W 01:00
#BSUB -R "rusage[mem=4GB]"


# Business-as-usual greedy baseline on the retained HPC pipeline. (greedy)

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "FATAL: Python runtime not found at $PYTHON_BIN" >&2
    exit 1
fi

export PYTHONPATH=".:src:${PYTHONPATH:-}"
export VRP_MAX_TRIPS_PER_VEHICLE=2

case $LSB_JOBINDEX in
1)
    SEED="1"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
2)
    SEED="2"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
3)
    SEED="3"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
4)
    SEED="4"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
5)
    SEED="5"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
6)
    SEED="6"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
7)
    SEED="7"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
8)
    SEED="8"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
9)
    SEED="9"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
10)
    SEED="10"
    ENDPOINT_KEY="baseline"
    OVERRIDES=(--override "endpoint_key=baseline")
    ;;
*)
    echo "FATAL: unknown LSB_JOBINDEX=$LSB_JOBINDEX" >&2
    exit 1
    ;;
esac

echo "Starting EXP-BASELINE - Seed $SEED"
echo "Job ID: $LSB_JOBID, Array Index: $LSB_JOBINDEX"
echo "Endpoint: $ENDPOINT_KEY"
"$PYTHON_BIN" -m scripts.runner.master_runner --exp EXP-BASELINE --seed $SEED "${OVERRIDES[@]}"
echo "Completed EXP-BASELINE - Seed $SEED ($ENDPOINT_KEY)"
