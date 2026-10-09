"""Pre-Deploy PR Energy Gate Entry Point.

Can be run as a standalone CLI tool or invoked via CI/CD runners to compare
codebases between git revisions and enforce energy gate compliance.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict

from app.scanner import analyze_directory
from app.services.energy_diff_service import EnergyDiffService


def evaluate_paths(base_path: str, head_path: str, max_regression_pct: float = 15.0) -> Dict[str, Any]:
    """Scan both base and head revisions and calculate delta energy impact."""
    base_results = analyze_directory(base_path) if os.path.exists(base_path) else {"green_score": 100.0, "total_energy_joules": 0.05}
    head_results = analyze_directory(head_path) if os.path.exists(head_path) else {"green_score": 100.0, "total_energy_joules": 0.05}

    return EnergyDiffService.compare_scans(
        base_scan=base_results,
        head_scan=head_results,
        max_regression_pct=max_regression_pct,
    )


def main():
    parser = argparse.ArgumentParser(description="GreenCode Pre-Deploy Energy Gate")
    parser.add_argument("--base", required=True, help="Path to base branch code")
    parser.add_argument("--head", required=True, help="Path to PR head branch code")
    parser.add_argument("--max-regression", type=float, default=15.0, help="Max permissible energy regression percentage")
    args = parser.parse_args()

    result = evaluate_paths(args.base, args.head, args.max_regression)
    print(result["pr_markdown_comment"])

    if result["is_blocked"]:
        print(f"\n[ERROR] PR Gate Failed: Energy regression {result['energy_delta_pct']}% exceeds threshold {args.max_regression}%", file=sys.stderr)
        sys.exit(1)
    else:
        print("\n[SUCCESS] PR Gate Passed: Energy criteria satisfied.")
        sys.exit(0)


if __name__ == "__main__":
    main()

