from __future__ import annotations

"""
Compatibility wrapper for ``src.simulation.future_sampler``.

This wrapper explicitly exports the key public symbol used throughout the
retained 22.03 thesis codebase while delegating all other attribute access to
the implementation module under ``code.simulation.future_sampler``.
"""

from code.simulation import future_sampler as _impl
from code.simulation.future_sampler import FutureSampler

__all__ = ["FutureSampler"]


def __getattr__(name: str):
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(dir(_impl)))
