"""
Experiment scripts package.

This package is organized into a reduced set of submodules:
- runner: experiment definitions and runners
- preflight: repo-hygiene checks
- legacy: compatibility wrappers kept for historical commands

DEPENDENCY CONTRACT (A1)
========================
Modules in ``scripts.runner`` import from the logical ``src`` package.
``src`` lives under <REPO_ROOT>/code/ and is exposed through the lightweight
facade in <REPO_ROOT>/src/.

For HPC jobs:
    export PYTHON_BIN=/usr/bin/python3
    cd <REPO_ROOT>
    export PYTHONPATH=.:src:$PYTHONPATH
    $PYTHON_BIN -m scripts.cli run-exp --exp EXP01 --seed 1 --dry-run
    $PYTHON_BIN -m scripts.cli hpc-generate --exp EXP01
    bsub < jobs/submit_exp01.sh
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_FACADE_ROOT = _REPO_ROOT / "src"

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if _SRC_FACADE_ROOT.exists() and str(_SRC_FACADE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_FACADE_ROOT))

REPO_ROOT = _REPO_ROOT


def ensure_src(*, verbose: bool = False) -> bool:
    try:
        import src  # noqa: F401

        if verbose:
            print(f"[preflight] src package OK  (location: {src.__file__})")
        return True
    except ImportError:
        msg = (
            "\n"
            + "=" * 70
            + "\nFATAL: cannot import 'src' package.\n"
            + "=" * 70
            + "\n\nThe scripts.runner modules depend on the 'src' package located at:\n"
            + f"    {_REPO_ROOT / 'code'}\n\n"
            + "Possible causes:\n"
            + "  1) You are running from the wrong directory.\n"
            + "  2) The code/ directory is missing or incomplete.\n"
            + "  3) PYTHONPATH does not include the repo root.\n"
            + f"     -> export PYTHONPATH={_REPO_ROOT}:$PYTHONPATH\n"
        )
        raise ImportError(msg)
