from __future__ import annotations

"""
Compatibility wrapper for ``src.simulation.control_actions``.

This module provides a stable import surface for callers that use the logical
``src.simulation`` namespace while the concrete implementation lives under:

    <REPO_ROOT>/code/simulation/control_actions.py
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPL_PATH = _REPO_ROOT / "code" / "simulation" / "control_actions.py"
_IMPL_MODULE_NAME = "_thesis22_03_code_simulation_control_actions"


def _load_impl() -> ModuleType:
    existing = globals().get("_IMPL")
    if isinstance(existing, ModuleType):
        return existing

    spec = spec_from_file_location(_IMPL_MODULE_NAME, _IMPL_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create import spec for {_IMPL_PATH}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_IMPL = _load_impl()

ControlAction = _IMPL.ControlAction
build_candidate_actions = _IMPL.build_candidate_actions

__all__ = [
    "ControlAction",
    "build_candidate_actions",
]


def __getattr__(name: str) -> Any:
    return getattr(_IMPL, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()) | set(dir(_IMPL)))
