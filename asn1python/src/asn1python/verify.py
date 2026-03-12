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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    parser.add_argument("-j", "--jobs", type=int, default=1,
                        help="Number of parallel verification jobs (default: 1)")
    parser.add_argument("--env", default=DEFAULT_ENV,
                        help=f"Conda environment name (default: {DEFAULT_ENV})")
    parser.add_argument("--base-dir", default=DEFAULT_BASE_DIR,
                        help=f"Nagini --base-dir argument (default: {DEFAULT_BASE_DIR!r})")
    args = parser.parse_args()

    print_lock = threading.Lock()

    def verify_and_report(file_path: Path, name: str) -> tuple[str, bool, float, str]:
        success, elapsed, output = run_nagini(file_path, name, args.env, args.base_dir)
        result_str = "ok" if success else "FAIL"
        with print_lock:
            print(f"  {name} ... {elapsed:.2f}s  {result_str}")
            if not success:
                for line in output.splitlines():
                    print(f"    {line}")
        return name, success, elapsed, result_str

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
            print(f"\n=== {file_path} ({len(names)} functions, {args.jobs} job(s)) ===")

            results: dict[str, tuple[bool, float, str]] = {}
            with ThreadPoolExecutor(max_workers=args.jobs) as executor:
                futures = {executor.submit(verify_and_report, file_path, name): name for name in names}
                for future in as_completed(futures):
                    name, success, elapsed, result_str = future.result()
                    results[name] = (success, elapsed, result_str)
                    writer.writerow([file_path, name, f"{elapsed:.3f}", result_str])
                    csv_file.flush()

            # Write TOTAL row in original function order
            file_total = sum(elapsed for _, elapsed, _ in results.values())
            any_failed = any(not success for success, _, _ in results.values())
            total_result = "FAIL" if any_failed else "ok"
            writer.writerow([file_path, "TOTAL", f"{file_total:.3f}", total_result])
            csv_file.flush()
            print(f"  Total: {file_total:.2f}s  {total_result}")


if __name__ == "__main__":
    main()
