"""
Facade package for ``src.simulation`` imports.

Implementation modules physically live under:

    <REPO_ROOT>/code/simulation/

This package makes imports such as:

    from src.simulation.rolling_horizon_integrated import run_rolling_horizon

resolve to the corresponding modules in ``code/simulation``.
"""

from pathlib import Path

# <REPO_ROOT>/src/simulation/__init__.py -> parents[2] = <REPO_ROOT>
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SIMULATION_ROOT = _REPO_ROOT / "code" / "simulation"

# Treat ``src.simulation`` as a namespace package backed by ``code/simulation``.
__path__ = [str(_SIMULATION_ROOT)]
