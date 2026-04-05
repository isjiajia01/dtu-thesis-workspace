from __future__ import annotations

"""
Compatibility wrapper for ``src.simulation.rolling_horizon_integrated``.

This module exposes the concrete implementation that lives under:

    <REPO_ROOT>/code/simulation/rolling_horizon_integrated.py

The wrapper exists so callers can continue importing through the logical
``src.simulation`` package while the retained thesis code keeps its actual
implementation under ``code/``.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPL_PATH = _REPO_ROOT / "code" / "simulation" / "rolling_horizon_integrated.py"
_IMPL_MODULE_NAME = "_thesis_2203_impl_rolling_horizon_integrated"


def _load_impl() -> ModuleType:
    existing = globals().get("_IMPL")
    if isinstance(existing, ModuleType):
        return existing

    if not _IMPL_PATH.is_file():
        raise ImportError(
            f"Cannot locate rolling horizon implementation at {_IMPL_PATH}"
        )

    spec = spec_from_file_location(_IMPL_MODULE_NAME, _IMPL_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create import spec for {_IMPL_PATH}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_IMPL = _load_impl()

OnlineCapacityAnalyzer = getattr(_IMPL, "OnlineCapacityAnalyzer")
RollingHorizonIntegrated = getattr(_IMPL, "RollingHorizonIntegrated")
run_rolling_horizon = getattr(_IMPL, "run_rolling_horizon")

__all__ = [
    "OnlineCapacityAnalyzer",
    "RollingHorizonIntegrated",
    "run_rolling_horizon",
]


def __getattr__(name: str) -> Any:
    return getattr(_IMPL, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()) | set(dir(_IMPL)))
