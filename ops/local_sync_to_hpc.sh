#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_ROOT="${DTU_THESIS_REMOTE_ROOT:-/zhome/2a/1/202283/thesis/}"
TRANSFER_HOST="${DTU_HPC_TRANSFER_HOST:-s232278@transfer.gbar.dtu.dk}"

RSYNC_RSH_CMD="${RSYNC_RSH_CMD:-ssh -o ControlMaster=no -o ControlPath=none}"

echo "Local root:    $ROOT_DIR/"
echo "Transfer host: ${TRANSFER_HOST}"
echo "Remote root:   ${REMOTE_ROOT}"

EXCLUDES=(
  --exclude .venv
  --exclude __pycache__
  --exclude .DS_Store
  --exclude archive/crash-dumps
  --exclude 22.02thesis/results
  --exclude 22.02thesis/data/processed
  --exclude 22.02thesis/logs
  --exclude 22.03controller_line/data/results
  --exclude 22.03controller_line/data/processed
  --exclude 22.03controller_line/logs
)

RSYNC_RSH="$RSYNC_RSH_CMD" rsync -az \
  "${EXCLUDES[@]}" \
  "$ROOT_DIR/" \
  "${TRANSFER_HOST}:${REMOTE_ROOT}"

echo "sync_ok"
