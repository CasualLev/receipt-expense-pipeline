"""Tests for src/run_pipeline.py, using tests/fixtures/expenses_broken.csv."""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

import run_pipeline
import validate

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "expenses_broken.csv"
SCRIPT = ROOT / "src" / "run_pipeline.py"

EXPECTED_FILES = [
    "expenses_clean.csv",
    "issues.csv",
    "food_report.xlsx",
    "charts/spend_by_restaurant_type.png",
    "charts/spend_by_cuisine.png",
    "charts/spend_by_year.png",
    "charts/avg_cost_per_visit.png",
    "charts/tip_percentage.png",
]


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """Run the pipeline on the broken fixture once. Returns (summary, output dir)."""
    output_dir = tmp_path_factory.mktemp("output")
    summary = run_pipeline.run_pipeline(FIXTURE, output_dir)
    return summary, output_dir


def test_summary_counts(run):
    summary, _ = run
    assert summary["rows_read"] == 11
    assert summary["rows_kept"] == 7
    assert summary["rows_excluded"] == 4
    assert summary["rows_flagged"] == 6
    assert summary["warnings"] > 0
    assert summary["file_problems"] == []
    assert summary["charts_skipped"] == []


def test_every_file_is_created(run):
    summary, output_dir = run
    expected = []
    for name in EXPECTED_FILES:
        expected.append(output_dir / name)
    assert summary["files_created"] == expected
    for path in expected:
        assert path.exists()


def test_clean_csv(run):
    _, output_dir = run
    clean = pd.read_csv(output_dir / "expenses_clean.csv", dtype=str, keep_default_na=False)
    assert len(clean) == 7
    assert list(clean.columns) == validate.COLUMNS + ["row", "year"]
    t004 = clean[clean["receipt_id"] == "T004"].iloc[0]
    assert t004["total"] == "7.61"
    t003 = clean[clean["receipt_id"] == "T003"].iloc[0]
    assert t003["date"] == "2015-04-25"
    assert t003["subtotal"] == "40.00"


def test_issues_csv(run):
    summary, output_dir = run
    issues = pd.read_csv(output_dir / "issues.csv")
    assert list(issues.columns) == validate.ISSUE_FIELDS
    assert (issues["severity"] == "warning").sum() == summary["warnings"]
    excluded_rows = set(issues[issues["severity"] == "error"]["row"])
    assert excluded_rows == {8, 9, 10, 11}


def test_unreadable_file_writes_nothing(tmp_path):
    output_dir = tmp_path / "output"
    summary = run_pipeline.run_pipeline(tmp_path / "missing.csv", output_dir)
    assert len(summary["file_problems"]) == 1
    assert summary["files_created"] == []
    assert not output_dir.exists()


def test_one_command_runs(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE), "--output-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Rows read:     11" in result.stdout
    assert "Rows kept:     7" in result.stdout
    assert "Rows excluded: 4" in result.stdout


def test_one_command_missing_file(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "missing.csv"), "--output-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Stopped: Could not read file" in result.stdout
