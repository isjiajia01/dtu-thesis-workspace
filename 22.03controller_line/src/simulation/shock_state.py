"""
Compatibility wrapper for ``src.simulation.shock_state``.

This module exposes the retained 22.03 implementation that physically lives in
``code.simulation.shock_state`` while making the key public symbols explicit
for static analysis tools and downstream imports.
"""

from __future__ import annotations

from importlib import import_module as _import_module
from typing import Any

_impl = _import_module("code.simulation.shock_state")

ShockState = _impl.ShockState
ShockStateBuilder = _impl.ShockStateBuilder

__all__ = [
    "ShockState",
    "ShockStateBuilder",
]


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()) | set(dir(_impl)))
