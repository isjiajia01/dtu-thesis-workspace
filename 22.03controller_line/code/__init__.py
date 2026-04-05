"""
Top-level implementation package for the retained `22.03controller_line` codebase.

This file exists primarily to make the `code/` directory an explicit Python
package so that static analysis tools and package-based imports can resolve
modules under:

- `code.simulation`
- `code.experiments`
- `code.solvers`
- `code.allocator`

more reliably.
"""
