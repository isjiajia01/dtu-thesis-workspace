"""
Compatibility wrapper for ``src.solvers.alns_solver``.

This module re-exports the public API from ``code.solvers.alns_solver`` so
imports using the logical package path

    from src.solvers.alns_solver import ...

continue to work even when callers depend on the ``src`` facade layout.
"""

from importlib import import_module as _import_module

_impl = _import_module("code.solvers.alns_solver")

__all__ = getattr(
    _impl,
    "__all__",
    [name for name in dir(_impl) if not name.startswith("_")],
)

globals().update({name: getattr(_impl, name) for name in __all__})
