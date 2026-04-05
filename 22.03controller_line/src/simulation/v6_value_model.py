"""
Compatibility wrapper for ``src.simulation.v6_value_model``.

The real implementation lives in:

    code.simulation.v6_value_model

This module re-exports the public symbols so callers can keep using:

    from src.simulation.v6_value_model import ...

without needing to know the physical implementation path.
"""

from __future__ import annotations

from importlib import import_module as _import_module

_impl = _import_module("code.simulation.v6_value_model")

__all__ = getattr(
    _impl,
    "__all__",
    [name for name in dir(_impl) if not name.startswith("_")],
)

for _name in __all__:
    globals()[_name] = getattr(_impl, _name)

__doc__ = getattr(_impl, "__doc__", __doc__)
