#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAPER_DIR="${ROOT}/22.01paper"

if [[ ! -x "${PAPER_DIR}/build_thesis.sh" ]]; then
  echo "Missing executable script: ${PAPER_DIR}/build_thesis.sh" >&2
  exit 1
fi

"${PAPER_DIR}/build_thesis.sh" "${1:-build}"
