"""
Compatibility wrapper for ``src.simulation.v6_risk_budget``.

The real implementation lives in ``code.simulation.v6_risk_budget``.
This file re-exports its public symbols so imports that target the
``src.simulation`` namespace continue to work.
"""

from importlib import import_module as _import_module

_impl = _import_module("code.simulation.v6_risk_budget")

if hasattr(_impl, "__all__"):
    __all__ = list(_impl.__all__)  # type: ignore[attr-defined]
else:
    __all__ = [name for name in dir(_impl) if not name.startswith("_")]

globals().update({name: getattr(_impl, name) for name in __all__})
