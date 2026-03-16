#!/usr/bin/env python3
"""Count implementation vs verification specification lines of code.

Compares each file against a base git ref (default: develop) to determine
how many lines are implementation (existed on base) vs specification (added
in the current branch for Nagini verification).

Files that do not exist on the base ref are counted as 100% spec.
Blank lines are excluded from all counts.

Usage:
    python count_loc.py [files...] -o FILE [--base-ref REF]
    python count_loc.py *.py -o loc.csv --base-ref develop
"""

import csv
import subprocess
import argparse
from pathlib import Path
from typing import Optional


def _nonblank_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def count_at_ref(ref: str, repo_path: Path, file_path: Path) -> Optional[int]:
    """Return non-blank line count of file_path at git ref, or None if not present."""
    try:
        rel = file_path.resolve().relative_to(repo_path.resolve())
    except ValueError:
        return None
    result = subprocess.run(
        ["git", "show", f"{ref}:{rel.as_posix()}"],
        capture_output=True, text=True, cwd=repo_path,
    )
    if result.returncode != 0:
        return None
    return _nonblank_lines(result.stdout)


def git_root(path: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, cwd=path,
    )
    if result.returncode != 0:
        raise RuntimeError("Not inside a git repository")
    return Path(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count implementation vs Nagini specification lines of code.")
    parser.add_argument("files", nargs="+", help="Python files to analyse")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file")
    parser.add_argument("--append", action="store_true",
                        help="Append to existing CSV instead of overwriting")
    parser.add_argument("--base-ref", default="develop",
                        help="Git ref to treat as implementation baseline (default: develop)")
    args = parser.parse_args()

    repo = git_root(Path("."))

    col_file = 38
    header = f"{'File':<{col_file}} {'Impl':>7} {'Spec':>7} {'Total':>7} {'Spec%':>7}"
    sep = "-" * len(header)
    print(header)
    print(sep)

    mode = "a" if args.append else "w"
    write_header = not args.append or not Path(args.output).exists()
    total_impl = total_spec = 0

    with open(args.output, mode, newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter=";")
        if write_header:
            writer.writerow(["File", "Impl", "Spec", "Total", "Spec%"])

        for file_str in args.files:
            file_path = Path(file_str)
            if not file_path.exists():
                print(f"Error: file not found: {file_path}")
                continue

            total = _nonblank_lines(file_path.read_text())
            impl = count_at_ref(args.base_ref, repo, file_path)
            if impl is None:
                impl = 0  # file not on base ref: entirely new (spec)
            else:
                impl = min(impl, total)  # guard against shrunk files

            spec = total - impl
            pct = 100.0 * spec / total if total else 0.0

            label = str(file_path)
            if len(label) > col_file:
                label = "..." + label[-(col_file - 3):]
            print(f"{label:<{col_file}} {impl:>7} {spec:>7} {total:>7} {pct:>6.1f}%")
            writer.writerow([file_path, impl, spec, total, f"{pct:.1f}"])
            total_impl += impl
            total_spec += spec

        grand_total = total_impl + total_spec
        grand_pct = 100.0 * total_spec / grand_total if grand_total else 0.0
        writer.writerow(["TOTAL", total_impl, total_spec, grand_total, f"{grand_pct:.1f}"])

    print(sep)
    print(f"{'TOTAL':<{col_file}} {total_impl:>7} {total_spec:>7} {grand_total:>7} {grand_pct:>6.1f}%")


if __name__ == "__main__":
    main()
