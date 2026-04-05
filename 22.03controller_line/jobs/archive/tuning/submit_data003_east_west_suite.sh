#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

bsub < jobs/submit_data003_east_bau_v6g_v6d.sh
bsub < jobs/submit_data003_east_crunch_r060_v6g_v6d.sh
bsub < jobs/submit_data003_west_bau_v6g_v6d.sh
bsub < jobs/submit_data003_west_crunch_r060_v6g_v6d.sh
