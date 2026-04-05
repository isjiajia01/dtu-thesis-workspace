#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH_HOST="${DTU_HPC_SSH_HOST:-dtu-hpc}"
TRANSFER_HOST="${DTU_HPC_TRANSFER_HOST:-s232278@transfer.gbar.dtu.dk}"
REMOTE_ROOT="${DTU_THESIS_REMOTE_ROOT:-/zhome/2a/1/202283/thesis/}"
JOB_PATH=""
SMOKE_CMD="${SMOKE_CMD:-}"
REMOTE_WORKDIR=""
SKIP_SMOKE=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  ./push_and_submit_lsf.sh --job <relative/path/to/job.lsf> [options]

Options:
  --job PATH              LSF job file path relative to repository root on HPC.
  --smoke-cmd CMD         Local smoke test command to run before sync.
  --remote-workdir PATH   Remote working directory relative to remote root.
  --host HOST             SSH login host for submission. Default: $DTU_HPC_SSH_HOST or dtu-hpc.
  --transfer-host HOST    Transfer host for rsync. Default: $DTU_HPC_TRANSFER_HOST or s232278@transfer.gbar.dtu.dk.
  --remote-root PATH      Remote thesis root. Default: $DTU_THESIS_REMOTE_ROOT.
  --skip-smoke            Skip local smoke test.
  --dry-run               Print actions without executing them.
  -h, --help              Show this help.

Examples:
  ./push_and_submit_lsf.sh \
    --job 22.03controller_line/jobs/submit_exp01.sh \
    --smoke-cmd "python -m pytest 22.03controller_line/tests -q"

  ./push_and_submit_lsf.sh \
    --job 22.02thesis/hpc_jobs/submit_phase0_benchmark.sh \
    --smoke-cmd "python 22.02thesis/src/optimization/validate_phase0_benchmark.py"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --job)
      JOB_PATH="$2"
      shift 2
      ;;
    --smoke-cmd)
      SMOKE_CMD="$2"
      shift 2
      ;;
    --remote-workdir)
      REMOTE_WORKDIR="$2"
      shift 2
      ;;
    --host)
      SSH_HOST="$2"
      shift 2
      ;;
    --transfer-host)
      TRANSFER_HOST="$2"
      shift 2
      ;;
    --remote-root)
      REMOTE_ROOT="$2"
      shift 2
      ;;
    --skip-smoke)
      SKIP_SMOKE=1
      shift
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

if [[ -z "$JOB_PATH" ]]; then
  echo "Error: --job is required." >&2
  usage >&2
  exit 1
fi

if [[ ! -f "$ROOT_DIR/$JOB_PATH" ]]; then
  echo "Error: local job file not found: $ROOT_DIR/$JOB_PATH" >&2
  exit 1
fi

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "+ $*"
  else
    eval "$@"
  fi
}

echo "Root dir:       $ROOT_DIR"
echo "SSH host:       $SSH_HOST"
echo "Transfer host:  $TRANSFER_HOST"
echo "Remote root:    $REMOTE_ROOT"
echo "LSF job path:   $JOB_PATH"

if [[ "$SKIP_SMOKE" -eq 0 && -n "$SMOKE_CMD" ]]; then
  echo
  echo "== Local smoke test =="
  run_cmd "cd \"$ROOT_DIR\" && $SMOKE_CMD"
elif [[ "$SKIP_SMOKE" -eq 0 ]]; then
  echo
  echo "== Local smoke test =="
  echo "No smoke command provided; skipping. Use --smoke-cmd to enable."
fi

echo
echo "== Sync to HPC =="
run_cmd "cd \"$ROOT_DIR\" && DTU_HPC_TRANSFER_HOST=\"$TRANSFER_HOST\" ./local_sync_to_hpc.sh"

REMOTE_CD="$REMOTE_ROOT"
if [[ -n "$REMOTE_WORKDIR" ]]; then
  REMOTE_CD="$REMOTE_ROOT/$REMOTE_WORKDIR"
fi

REMOTE_JOB_PATH="$REMOTE_ROOT/$JOB_PATH"
REMOTE_SUBMIT="cd \"$REMOTE_CD\" && bsub < \"$REMOTE_JOB_PATH\""

echo
echo "== Submit on HPC =="
run_cmd "ssh \"$SSH_HOST\" '$REMOTE_SUBMIT'"

echo
echo "submit_ok"
