#!/bin/bash
set -euo pipefail

#BSUB -J BUILD_DATA003_OSRM_EAST
#BSUB -q hpc
#BSUB -o logs/build_data003_osrm_matrix_east.out
#BSUB -e logs/build_data003_osrm_matrix_east.err
#BSUB -n 1
#BSUB -W 06:00
#BSUB -R "rusage[mem=16GB]"

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "FATAL: Python runtime not found at $PYTHON_BIN" >&2
    exit 1
fi

export PYTHONPATH=".:src:${PYTHONPATH:-}"

BENCHMARK_PATH="${BENCHMARK_PATH:-data/processed/multiday_benchmark_east.json}"
OUTPUT_DIR="${OUTPUT_DIR:-data/processed/vrp_matrix_east}"
OSRM_DATA="${OSRM_DATA:-../22.02thesis/data/processed/vrp_data/vrp_maps/denmark/20260223/denmark-latest.osrm}"
OSRM_RUNTIME="${OSRM_RUNTIME:-auto}"
OSRM_URL="${OSRM_URL:-}"
MATRIX_BLOCK_SIZE="${MATRIX_BLOCK_SIZE:-100}"
MATRIX_MAX_TABLE_SIZE="${MATRIX_MAX_TABLE_SIZE:-200}"
MATRIX_PORT="${MATRIX_PORT:-5100}"

ARGS=(
  --benchmark "$BENCHMARK_PATH"
  --output-dir "$OUTPUT_DIR"
  --osrm-data "$OSRM_DATA"
  --runtime "$OSRM_RUNTIME"
  --block-size "$MATRIX_BLOCK_SIZE"
  --max-table-size "$MATRIX_MAX_TABLE_SIZE"
  --port "$MATRIX_PORT"
  --overwrite
)

if [ -n "$OSRM_URL" ]; then
  ARGS+=(--osrm-url "$OSRM_URL")
fi

"$PYTHON_BIN" scripts/analysis/build_osrm_matrix.py "${ARGS[@]}"
