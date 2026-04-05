#!/usr/bin/env python3
"""
Minimal acceptance test for the reduced EXP00/EXP01 workflow.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PASS = 0
FAIL = 0


def _pass(label: str) -> None:
    global PASS
    PASS += 1
    print(f"  [PASS] {label}")


def _fail(label: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    msg = f"  [FAIL] {label}"
    if detail:
        msg += f" - {detail}"
    print(msg, file=sys.stderr)


def check_init_files() -> None:
    for rel in ("scripts/__init__.py", "scripts/runner/__init__.py", "scripts/preflight/__init__.py"):
        if (REPO_ROOT / rel).is_file():
            _pass(rel)
        else:
            _fail(rel, "missing")


def check_wrappers() -> None:
    wrappers = {
        "scripts/master_runner.py": "scripts.runner.master_runner",
        "scripts/generate_hpc_jobs.py": "scripts.runner.generate_hpc_jobs",
    }
    for rel, target_mod in wrappers.items():
        path = REPO_ROOT / rel
        if not path.is_file():
            _fail(rel, "missing")
            continue
        text = path.read_text()
        if "runpy" in text and target_mod in text:
            _pass(rel)
        else:
            _fail(rel, "wrapper target mismatch")


def check_cli_parsing() -> None:
    for args in (["--help"], ["run-exp", "--help"], ["hpc-generate", "--help"]):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.cli", *args],
            capture_output=True,
            cwd=str(REPO_ROOT),
            timeout=15,
        )
        if result.returncode == 0:
            _pass("cli " + " ".join(args))
        else:
            _fail("cli " + " ".join(args), result.stderr.decode()[:200])


def check_modules_locatable() -> None:
    for mod in ("scripts.cli", "scripts.runner.master_runner", "scripts.runner.generate_hpc_jobs"):
        if importlib.util.find_spec(mod) is not None:
            _pass(mod)
        else:
            _fail(mod, "find_spec returned None")


def check_ensure_src() -> None:
    try:
        from scripts import ensure_src

        ensure_src(verbose=True)
        _pass("ensure_src")
    except Exception as exc:
        _fail("ensure_src", str(exc))


def main() -> int:
    check_init_files()
    check_wrappers()
    check_cli_parsing()
    check_modules_locatable()
    check_ensure_src()
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
