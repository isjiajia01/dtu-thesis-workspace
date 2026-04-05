"""
Facade package for `src.*` imports.

This package exposes the sibling `code/` directory as the logical `src`
package root, so imports like:

    from src.simulation.rolling_horizon_integrated import run_rolling_horizon

resolve to modules under:

    <REPO_ROOT>/code/
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CODE_ROOT = _REPO_ROOT / "code"

__path__ = [str(_CODE_ROOT)] if _CODE_ROOT.is_dir() else []
__all__: list[str] = []
