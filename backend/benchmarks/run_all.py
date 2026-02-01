#!/usr/bin/env python3
"""
Run TraceLens unit tests and benchmarks.

Usage:
  python -m benchmarks.run_all              # unit tests + benchmarks
  python -m benchmarks.run_all --benchmark-only
  python -m benchmarks.run_all --no-benchmark
  python -m benchmarks.run_all --save myrun  # save benchmark results
"""
import argparse
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark-only", action="store_true")
    ap.add_argument("--no-benchmark", action="store_true")
    ap.add_argument("--save", type=str, metavar="NAME")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    def run(cmd, cwd=BACKEND):
        return subprocess.run(cmd, cwd=str(cwd))

    # 1. Unit tests (exclude bench)
    if not args.benchmark_only:
        cmd = [sys.executable, "-m", "pytest", "tests", "-k", "not bench", "-v" if args.verbose else "-q"]
        if run(cmd).returncode != 0:
            sys.exit(1)

    if args.no_benchmark:
        return

    # 2. Benchmarks
    cmd = [sys.executable, "-m", "pytest", "tests/bench_metrics.py", "--benchmark-only", "-v"]
    if args.save:
        cmd += [f"--benchmark-save={args.save}"]
    if run(cmd).returncode != 0:
        sys.exit(1)

    print("\nSee docs/METRICS.md for interpreting results.")


if __name__ == "__main__":
    main()
