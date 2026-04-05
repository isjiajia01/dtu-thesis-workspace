"""
Facade package for ``src.experiments`` imports.

The actual experiment modules live under:

    <REPO_ROOT>/code/experiments/

This package exposes that directory so imports such as:

    from src.experiments.exp_utils import run_batch

resolve to the implementation in ``code/experiments``.
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXPERIMENTS_ROOT = _REPO_ROOT / "code" / "experiments"

__path__ = [str(_EXPERIMENTS_ROOT)]
