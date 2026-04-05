"""
Compatibility wrapper for ``src.experiments.plot_utils``.

This module re-exports the implementation that lives under
``code.experiments.plot_utils`` so callers can continue to use the
logical import path::

    from src.experiments.plot_utils import ...

while the actual implementation remains in ``code/experiments``.
"""

from importlib import import_module as _import_module

_impl = _import_module("code.experiments.plot_utils")

__all__ = getattr(
    _impl,
    "__all__",
    [name for name in dir(_impl) if not name.startswith("_")],
)

globals().update({name: getattr(_impl, name) for name in __all__})


def __getattr__(name: str):
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_impl)))
