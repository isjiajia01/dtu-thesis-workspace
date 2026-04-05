#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRANSFER_HOST="${DTU_HPC_TRANSFER_HOST:-s232278@transfer.gbar.dtu.dk}"
REMOTE_ROOT="${DTU_THESIS_REMOTE_ROOT:-/zhome/2a/1/202283/thesis/}"
STATE_ROOT="${DTU_LOCAL_STATE_ROOT:-$HOME/thesis-local-state/dtu-sem6}"
REMOTE_PATH=""
LOCAL_SUBDIR="hpc-pulls"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  ./pull_hpc_results.sh --remote-path <path-relative-to-remote-root> [options]

Options:
  --remote-path PATH    Remote path relative to remote thesis root.
  --local-subdir PATH   Local subdirectory under local state root. Default: hpc-pulls.
  --host HOST           Transfer host for rsync. Default: $DTU_HPC_TRANSFER_HOST or s232278@transfer.gbar.dtu.dk.
  --remote-root PATH    Remote thesis root. Default: $DTU_THESIS_REMOTE_ROOT.
  --dry-run             Print the rsync command without executing it.
  -h, --help            Show help.

Example:
  ./pull_hpc_results.sh \
    --remote-path 22.03controller_line/data/results/EXP_EXP01 \
    --local-subdir hpc-pulls/exp01
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote-path)
      REMOTE_PATH="$2"
      shift 2
      ;;
    --local-subdir)
      LOCAL_SUBDIR="$2"
      shift 2
      ;;
    --host)
      TRANSFER_HOST="$2"
      shift 2
      ;;
    --remote-root)
      REMOTE_ROOT="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$REMOTE_PATH" ]]; then
  echo "Error: --remote-path is required." >&2
  usage >&2
  exit 1
fi

LOCAL_DEST="$STATE_ROOT/$LOCAL_SUBDIR"
mkdir -p "$LOCAL_DEST"

REMOTE_FULL="${TRANSFER_HOST}:${REMOTE_ROOT%/}/${REMOTE_PATH}"
CMD=(rsync -avz --progress --stats --partial -e ssh "$REMOTE_FULL" "$LOCAL_DEST/")

echo "Remote: $REMOTE_FULL"
echo "Local:  $LOCAL_DEST/"

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf '+ '
  printf '%q ' "${CMD[@]}"
  printf '\n'
else
  "${CMD[@]}"
fi
