"""Run the whole Stage 2 pipeline: validation, report and charts.

Usage: python src/run_pipeline.py data/expenses.csv
       python src/run_pipeline.py data/expenses.csv --output-dir some/folder
"""

import argparse
import logging
import sys
from pathlib import Path

import charts
import report
import validate

DEFAULT_OUTPUT_DIR = Path("output")


def file_problems(issues):
    """Return the problems that stopped the file being read at all (row 0)."""
    problems = []
    for issue in issues:
        if issue.row == 0:
            problems.append(issue.problem)
    return problems


def count_warnings(issues):
    """Count the warnings in a list of issues."""
    count = 0
    for issue in issues:
        if issue.severity == validate.WARNING:
            count += 1
    return count


def write_csv(frame, path):
    """Write a DataFrame to CSV with money as 2 decimals."""
    frame.to_csv(path, index=False, float_format="%.2f", lineterminator="\n")


def run_pipeline(csv_path, output_dir=DEFAULT_OUTPUT_DIR):
    """Validate the CSV, then write the clean data, issues, report and charts.

    Returns a summary dict. If the file can't be read, nothing is written and
    the reason is in summary["file_problems"].
    """
    output_dir = Path(output_dir)
    clean_rows, issues = validate.validate_file(csv_path)

    summary = {
        "rows_read": 0,
        "rows_kept": 0,
        "rows_excluded": 0,
        "warnings": 0,
        "rows_flagged": 0,
        "file_problems": file_problems(issues),
        "charts_skipped": [],
        "files_created": [],
    }
    if len(summary["file_problems"]) > 0:
        return summary

    output_dir.mkdir(parents=True, exist_ok=True)
    created = summary["files_created"]

    clean_path = output_dir / "expenses_clean.csv"
    write_csv(clean_rows, clean_path)
    created.append(clean_path)

    issues_path = output_dir / "issues.csv"
    write_csv(validate.issues_to_dataframe(issues), issues_path)
    created.append(issues_path)

    created.append(report.write_report(clean_rows, issues, output_dir / "food_report.xlsx"))

    chart_paths, skipped = charts.make_charts(clean_rows, output_dir / "charts")
    created.extend(chart_paths)
    summary["charts_skipped"] = skipped

    excluded = len(validate.excluded_rows(issues))
    summary["rows_read"] = len(clean_rows) + excluded
    summary["rows_kept"] = len(clean_rows)
    summary["rows_excluded"] = excluded
    summary["warnings"] = count_warnings(issues)
    summary["rows_flagged"] = report.flagged_row_count(clean_rows, issues)
    return summary


def print_summary(csv_path, summary):
    """Print a short, readable summary of a pipeline run."""
    print()
    print(f"Pipeline summary for {csv_path}")
    print(f"  Rows read:     {summary['rows_read']}")
    print(f"  Rows kept:     {summary['rows_kept']}")
    print(f"  Rows excluded: {summary['rows_excluded']}")
    print(f"  Warnings:      {summary['warnings']} (on {summary['rows_flagged']} kept rows)")
    if len(summary["charts_skipped"]) > 0:
        print(f"  Charts skipped: {len(summary['charts_skipped'])} (see warnings above)")
    print("  Files created:")
    for path in summary["files_created"]:
        print(f"    {path}")


def main():
    """Parse the command line, run the pipeline and print the summary."""
    parser = argparse.ArgumentParser(description="Validate food expenses and build the report.")
    parser.add_argument("csv_path", help="CSV file that follows schema.md")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="folder for generated files (default: output)",
    )
    args = parser.parse_args()
    logging.basicConfig(format="%(levelname)s: %(message)s")

    try:
        summary = run_pipeline(args.csv_path, args.output_dir)
    except PermissionError as problem:
        print(f"Could not write {problem.filename}. Is it open in another program?")
        return 1

    if len(summary["file_problems"]) > 0:
        for problem in summary["file_problems"]:
            print(f"Stopped: {problem}")
        return 1

    print_summary(args.csv_path, summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
