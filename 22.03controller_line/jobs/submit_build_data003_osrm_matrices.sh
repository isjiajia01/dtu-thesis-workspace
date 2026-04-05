#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

bsub < jobs/submit_build_data003_osrm_matrix_east.sh
bsub < jobs/submit_build_data003_osrm_matrix_west.sh
