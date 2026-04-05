#!/usr/bin/env python3
"""
Unified CLI for retained experiment tooling (EXP00/EXP01 only).
"""

import argparse
import sys
from typing import List


def _run_module(mod: str, argv: List[str]) -> int:
    import runpy

    old_argv = sys.argv[:]
    try:
        sys.argv = [mod] + argv
        runpy.run_module(mod, run_name="__main__")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    finally:
        sys.argv = old_argv


def cmd_run_exp(args: argparse.Namespace) -> int:
    argv: List[str] = ["--exp", args.exp]
    if args.seed is not None:
        argv += ["--seed", str(args.seed)]
    for ov in args.override or []:
        argv += ["--override", ov]
    if args.override_json:
        argv += ["--override_json", args.override_json]
    if args.dry_run:
        argv.append("--dry-run")
    return _run_module("scripts.runner.master_runner", argv)


def cmd_hpc_generate(args: argparse.Namespace) -> int:
    argv: List[str] = []
    if args.all:
        argv.append("--all")
    if args.exp:
        argv += ["--exp", args.exp]
    if args.mode:
        argv += ["--mode", args.mode]
    return _run_module("scripts.runner.generate_hpc_jobs", argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Thesis tooling CLI (EXP00/EXP01)")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run-exp", help="Run one experiment through master_runner")
    run.add_argument("--exp", required=True, help="Experiment ID: EXP00 or EXP01")
    run.add_argument("--seed", type=int, default=1, help="Random seed")
    run.add_argument("--override", action="append", help="Override parameter (key=value)")
    run.add_argument("--override_json", help="Path to JSON with overrides")
    run.add_argument("--dry-run", action="store_true", help="Print config without running")
    run.set_defaults(func=cmd_run_exp)

    hpc = sub.add_parser("hpc-generate", help="Generate HPC submission scripts")
    hpc.add_argument("--all", action="store_true", help="Generate scripts for all retained experiments")
    hpc.add_argument("--exp", help="Generate script for one experiment (EXP00/EXP01)")
    hpc.add_argument(
        "--mode",
        choices=["proactive", "greedy"],
        default="proactive",
        help="Policy mode for generated scripts",
    )
    hpc.set_defaults(func=cmd_hpc_generate)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
