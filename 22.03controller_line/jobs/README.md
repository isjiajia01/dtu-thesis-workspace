# Retained Job Set

This directory keeps only the paper-facing and reproducibility-critical HPC entrypoints.

Retained job categories:

- baseline backbone: `submit_exp00.sh`, `submit_exp-baseline_greedy.sh`, `submit_exp01.sh`
- Herlev mainline progression: `submit_scenario1_robust_v2_compute300.sh`, `submit_scenario1_robust_v4_event_commitment_compute300.sh`, `submit_scenario1_robust_v5_risk_budgeted_compute300.sh`, `submit_scenario1_robust_v6f_execution_guard_compute300.sh`, `submit_scenario1_robust_v6g_deadline_reservation_v6d_compute300.sh`
- runtime-policy follow-up: `submit_scenario1_robust_v6g_deadline_reservation_v6d_automode.sh`, `submit_scenario1_robust_v6g_deadline_reservation_v6d_fixed300_cap05_control.sh`
- OOD transfer: the three `submit_scenario1_ood_*_v6g_v6d_compute300.sh` jobs
- auxiliary DATA003 lines: one retained east line and one retained west line
- matrix generation helpers for retained DATA003 assets

Archived jobs live under `jobs/archive/`.
They are kept only for historical traceability and should not be used as default paper-facing entrypoints.

Archive layout:

- `jobs/archive/runtime/` = historical runtime-policy, cap, reopt, and time-budget sweeps
- `jobs/archive/ood/` = historical OOD sensitivity sweeps
- `jobs/archive/tuning/` = abandoned controller branches, probes, and older tuning paths
