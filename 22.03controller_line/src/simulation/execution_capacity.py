"""
Compatibility wrapper for ``src.simulation.execution_capacity``.

This module re-exports the concrete implementation from the retained
``22.03controller_line`` code tree so imports of the form

    from src.simulation.execution_capacity import ...

continue to work even when tools or editors expect a real file to exist
under ``src/simulation``.
"""

from importlib import import_module as _import_module

_IMPL = None
_LAST_ERROR = None

for _module_name in (
    "code.simulation.execution_capacity",
    "simulation.execution_capacity",
):
    try:
        _IMPL = _import_module(_module_name)
        break
    except ModuleNotFoundError as exc:
        _LAST_ERROR = exc

if _IMPL is None:
    raise ImportError(
        "Unable to locate the execution_capacity implementation in the "
        "retained 22.03 thesis codebase."
    ) from _LAST_ERROR

if hasattr(_IMPL, "__all__"):
    __all__ = list(_IMPL.__all__)  # type: ignore[attr-defined]
else:
    __all__ = [name for name in dir(_IMPL) if not name.startswith("_")]

globals().update({name: getattr(_IMPL, name) for name in __all__})

__doc__ = getattr(_IMPL, "__doc__", __doc__)
