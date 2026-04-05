"""
Compatibility wrapper for ``src.experiments.exp_utils``.

The retained 22.03 thesis workspace keeps the concrete experiment utilities
under:

    code.experiments.exp_utils

This module re-exports that implementation so imports such as:

    from src.experiments.exp_utils import run_batch

continue to work with a stable ``src.*`` import path.
"""

from importlib import import_module as _import_module

_IMPL = _import_module("code.experiments.exp_utils")

__all__ = getattr(
    _IMPL,
    "__all__",
    [name for name in dir(_IMPL) if not name.startswith("_")],
)

globals().update({name: getattr(_IMPL, name) for name in __all__})


def __getattr__(name: str):
    return getattr(_IMPL, name)


def __dir__():
    return sorted(set(__all__) | set(globals().keys()))
