#!/usr/bin/env python3
"""Compare per-class line counts between CustomTest.py and CustomTest-Verify.py.

For each top-level class, reports:
  Impl  – non-blank lines in the base file (CustomTest.py)
  Spec  – additional non-blank lines in the verify file (CustomTest-Verify.py)
  Total – non-blank lines in the verify file
  Spec% – fraction that is Nagini annotation overhead

Usage:
    python compare_class_loc.py [base_file] [verify_file]
    python compare_class_loc.py CustomTest.py CustomTest-Verify.py
"""

import csv
import sys
import ast
from pathlib import Path


def nonblank_lines(lines: list[str]) -> int:
    return sum(1 for l in lines if l.strip())


def class_ranges(source: str) -> dict[str, tuple[int, int]]:
    """Return {class_name: (start_line, end_line)} using the AST.

    Line numbers are 1-based, end_line is inclusive.
    """
    tree = ast.parse(source)
    lines = source.splitlines()
    total = len(lines)

    # Collect top-level class nodes sorted by start line
    nodes = sorted(
        (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.col_offset == 0),
        key=lambda n: n.lineno,
    )

    ranges: dict[str, tuple[int, int]] = {}
    for i, node in enumerate(nodes):
        start = node.lineno
        if i + 1 < len(nodes):
            # End just before the next top-level class
            end = nodes[i + 1].lineno - 1
        else:
            end = total
        ranges[node.name] = (start, end)
    return ranges


def count_class_lines(file_path: Path) -> dict[str, int]:
    source = file_path.read_text(encoding="utf-8")
    all_lines = source.splitlines()
    ranges = class_ranges(source)
    return {
        name: nonblank_lines(all_lines[start - 1: end])
        for name, (start, end) in ranges.items()
    }


def main() -> None:
    args = sys.argv[1:]
    base_path = Path(args[0])
    verify_path = Path(args[1])
    csv_path = Path(args[2]) if len(args) > 2 else Path("compare_class_loc.csv")

    for p in (base_path, verify_path):
        if not p.exists():
            print(f"Error: file not found: {p}")
            sys.exit(1)

    base_counts = count_class_lines(base_path)
    verify_counts = count_class_lines(verify_path)

    all_classes = list(dict.fromkeys(list(base_counts) + list(verify_counts)))

    col_class = 30
    header = f"{'Class':<{col_class}} {'Impl':>7} {'Spec':>7} {'Total':>7} {'Spec%':>7}"
    sep = "-" * len(header)
    print(f"\n{base_path}  vs  {verify_path}\n")
    print(header)
    print(sep)

    total_impl = total_spec = 0
    with open(csv_path, "w", newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter=";")
        writer.writerow(["Class", "Impl", "Spec", "Total", "Spec%"])

        for name in all_classes:
            impl = base_counts.get(name, 0)
            total = verify_counts.get(name, 0)
            if total == 0:
                total = impl  # class only in base; no verify overhead
            impl = min(impl, total)
            spec = total - impl
            pct = 100.0 * spec / total if total else 0.0

            label = name if len(name) <= col_class else "..." + name[-(col_class - 3):]
            print(f"{label:<{col_class}} {impl:>7} {spec:>7} {total:>7} {pct:>6.1f}%")
            writer.writerow([name, impl, spec, total, f"{pct:.1f}"])
            total_impl += impl
            total_spec += spec

        grand_total = total_impl + total_spec
        grand_pct = 100.0 * total_spec / grand_total if grand_total else 0.0
        writer.writerow(["TOTAL", total_impl, total_spec, grand_total, f"{grand_pct:.1f}"])

    print(sep)
    print(f"{'TOTAL':<{col_class}} {total_impl:>7} {total_spec:>7} {grand_total:>7} {grand_pct:>6.1f}%")
    print(f"\nWritten to {csv_path}")


if __name__ == "__main__":
    main()
