#!/usr/bin/env python3
"""Run nagini verification for each function individually and write results as CSV.

Progress is printed to stdout; CSV rows (file, function, time_s, result) are
written to --output file.

Usage:
    python verify.py [files...] [-o FILE] [--env ENV] [--base-dir DIR]

Examples:
    python verify.py verification.py -o results.csv
    python verify.py verification.py bitstream.py -o results.csv
"""

import ast
import csv
import subprocess
import argparse
import sys
import time
from pathlib import Path

DEFAULT_ENV = "nagini"
DEFAULT_BASE_DIR = "../"


def extract_names(file_path: Path) -> list[str]:
    """Extract top-level function and class method names from a Python file.

    Methods are returned as 'ClassName.method_name'.
    """
    source = file_path.read_text()
    tree = ast.parse(source)
    names = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names.append(node.name)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    names.append(f"{node.name}.{item.name}")
    return names


def run_nagini(file_path: Path, name: str, env: str, base_dir: str) -> tuple[bool, float, str]:
    """Run nagini --select for a single function/method.

    Returns (success, elapsed_seconds, combined_output).
    """
    cmd = [
        "conda", "run", "--no-capture-output", "-n", env,
        "nagini", f"--base-dir={base_dir}", str(file_path), "--select", name,
    ]
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    success = result.returncode == 0
    output = result.stdout + result.stderr
    return success, elapsed, output


def main():
    parser = argparse.ArgumentParser(
        description="Verify nagini functions individually and write timing results as CSV.")
    parser.add_argument("files", nargs="+", help="Python files to verify")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file")
    parser.add_argument("--append", action="store_true",
                        help="Append to existing CSV instead of overwriting")
    parser.add_argument("--env", default=DEFAULT_ENV,
                        help=f"Conda environment name (default: {DEFAULT_ENV})")
    parser.add_argument("--base-dir", default=DEFAULT_BASE_DIR,
                        help=f"Nagini --base-dir argument (default: {DEFAULT_BASE_DIR!r})")
    args = parser.parse_args()

    mode = "a" if args.append else "w"
    write_header = not args.append or not Path(args.output).exists()
    with open(args.output, mode, newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter=";")
        if write_header:
            writer.writerow(["File", "Function", "Time", "Result"])

        for file_str in args.files:
            file_path = Path(file_str)
            if not file_path.exists():
                print(f"Error: file not found: {file_path}")
                continue

            names = extract_names(file_path)
            print(f"\n=== {file_path} ({len(names)} functions) ===")

            file_total = 0.0
            any_failed = False
            for name in names:
                print(f"  {name} ...", end="", flush=True)
                success, elapsed, output = run_nagini(file_path, name, args.env, args.base_dir)
                file_total += elapsed
                result_str = "ok" if success else "FAIL"
                print(f" {elapsed:.2f}s  {result_str}")
                if not success:
                    any_failed = True
                    for line in output.splitlines():
                        print(f"    {line}")
                writer.writerow([file_path, name, f"{elapsed:.3f}", result_str])
                csv_file.flush()

            total_result = "FAIL" if any_failed else "ok"
            writer.writerow([file_path, "TOTAL", f"{file_total:.3f}", total_result])
            csv_file.flush()
            print(f"  Total: {file_total:.2f}s  {total_result}")


if __name__ == "__main__":
    main()
