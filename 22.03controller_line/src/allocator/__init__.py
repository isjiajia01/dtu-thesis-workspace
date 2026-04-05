"""
Allocator package marker for the retained thesis workspace.

This package currently exists to provide a stable import location for
``src.allocator`` during static analysis and future maintenance.

The active thesis line does not currently ship allocator submodules under
this package, but keeping the package present avoids package-resolution
ambiguity and leaves a clear place for future allocator-related code.
"""

__all__: list[str] = []
