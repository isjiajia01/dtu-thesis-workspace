"""
Compatibility wrapper for ``src.simulation.robust_controller``.

This module exposes the retained 22.03 implementation that physically lives in
``code.simulation.robust_controller`` while making the key public symbols
explicit for static analysis tools and downstream imports.
"""

from __future__ import annotations

from importlib import import_module as _import_module
from typing import Any

_impl = _import_module("code.simulation.robust_controller")

RobustDecision = _impl.RobustDecision
RobustController = _impl.RobustController

__all__ = [
    "RobustDecision",
    "RobustController",
]


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()) | set(dir(_impl)))
