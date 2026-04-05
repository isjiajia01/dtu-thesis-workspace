"""
Compatibility facade package for ``solvers.*`` imports.

Core solver implementation code physically lives under:

    <REPO_ROOT>/code/solvers/

This package maps imports like:

    from solvers.alns_solver import ALNS_Solver
    from solvers.alns_solver import RoutingGlsSolver

onto:

    <REPO_ROOT>/code/solvers/alns_solver.py

so that legacy callers can keep using the logical package name
``solvers`` while the repository keeps its actual code under ``code/solvers``.
The canonical class name is ``RoutingGlsSolver``; ``ALNS_Solver`` remains a
compatibility alias.
"""

from pathlib import Path

# Resolve the repo root from this file:
#   <REPO_ROOT>/src/solvers/__init__.py -> parents[2] = <REPO_ROOT>
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SOLVERS_ROOT = _REPO_ROOT / "code" / "solvers"

# Treat ``solvers`` as a namespace package whose search path points at
# the real solver implementation directory.
__path__ = [str(_SOLVERS_ROOT)]
