"""
Compatibility wrapper for ``src.simulation.policies``.

This module re-exports the policy implementation from
``code.simulation.policies`` so that imports using the logical
``src.simulation`` namespace continue to work.
"""

from importlib import import_module as _import_module

_impl = _import_module("code.simulation.policies")

BasePolicy = _impl.BasePolicy
GreedyPolicy = _impl.GreedyPolicy
ProactivePolicy = _impl.ProactivePolicy
StabilityPolicy = _impl.StabilityPolicy

if hasattr(_impl, "_uses_oracle_targets"):
    _uses_oracle_targets = _impl._uses_oracle_targets


def __getattr__(name: str):
    return getattr(_impl, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_impl)))


__all__ = list(getattr(_impl, "__all__", []))
if not __all__:
    __all__ = [name for name in dir(_impl) if not name.startswith("_")]
