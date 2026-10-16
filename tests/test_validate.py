"""Tests for src/validate.py, based on tests/fixtures/README.md."""

from pathlib import Path

import pandas as pd
import pytest

import validate

FIXTURE = Path(__file__).parent / "fixtures" / "expenses_broken.csv"

# Spreadsheet row of each fixture row (header is row 1). T002 appears twice.
ROW_T001 = 2
ROW_T002_FIRST = 3
ROW_T003 = 4
ROW_T004 = 5
ROW_T005 = 6
ROW_T006 = 7
ROW_T007 = 8
ROW_T008 = 9
ROW_T002_SECOND = 10
ROW_T010 = 11
ROW_T011 = 12


@pytest.fixture(scope="module")
def result():
    """Validate the broken fixture once and share the result."""
    return validate.validate_file(FIXTURE)


def issues_for_row(issues, row):
    """Return the issues logged for one spreadsheet row."""
    found = []
    for issue in issues:
        if issue.row == row:
            found.append(issue)
    return found


def has_issue(issues, row, column, severity):
    """Return True if row has an issue with this column and severity."""
    for issue in issues_for_row(issues, row):
        if issue.column == column and issue.severity == severity:
            return True
    return False


def has_error(issues, row):
    """Return True if row has any error."""
    for issue in issues_for_row(issues, row):
        if issue.severity == validate.ERROR:
            return True
    return False


def clean_row(clean_rows, row):
    """Return the clean row with this spreadsheet row number as a dict."""
    matches = clean_rows[clean_rows["row"] == row]
    assert len(matches) == 1, f"row {row} should be kept"
    return matches.iloc[0].to_dict()


# --- Totals ---------------------------------------------------------------


def test_row_counts(result):
    clean_rows, issues = result
    excluded = validate.excluded_rows(issues)
    assert len(clean_rows) + len(excluded) == 11
    assert len(clean_rows) == 7
    assert len(excluded) == 4


def test_kept_and_excluded_rows(result):
    clean_rows, issues = result
    kept = list(clean_rows["row"])
    assert kept == [
        ROW_T001,
        ROW_T002_FIRST,
        ROW_T003,
        ROW_T004,
        ROW_T005,
        ROW_T006,
        ROW_T011,
    ]
    excluded = validate.excluded_rows(issues)
    assert excluded == [ROW_T007, ROW_T008, ROW_T002_SECOND, ROW_T010]


def test_clean_rows_have_schema_columns(result):
    clean_rows, _ = result
    assert list(clean_rows.columns) == validate.COLUMNS + ["row", "year"]


def test_every_issue_is_complete(result):
    _, issues = result
    assert len(issues) > 0
    for issue in issues:
        assert issue.severity in (validate.ERROR, validate.WARNING)
        assert issue.receipt_id != ""
        assert issue.row >= 2
        assert issue.column in validate.COLUMNS
        assert issue.problem != ""


# --- One test per fixture row ---------------------------------------------


def test_t001_clean_row_has_no_issues(result):
    clean_rows, issues = result
    assert issues_for_row(issues, ROW_T001) == []
    row = clean_row(clean_rows, ROW_T001)
    assert row["receipt_id"] == "T001"
    assert row["total"] == 56.58


def test_t002_first_spaces_trimmed(result):
    clean_rows, issues = result
    row = clean_row(clean_rows, ROW_T002_FIRST)
    assert row["merchant"] == "Grand Lux Cafe"
    assert row["restaurant_type"] == "Casual Dining"
    assert has_issue(issues, ROW_T002_FIRST, "merchant", validate.WARNING)
    assert has_issue(issues, ROW_T002_FIRST, "restaurant_type", validate.WARNING)
    assert not has_error(issues, ROW_T002_FIRST)


def test_t003_date_converted(result):
    clean_rows, issues = result
    row = clean_row(clean_rows, ROW_T003)
    assert row["date"] == "2015-04-25"
    assert has_issue(issues, ROW_T003, "date", validate.WARNING)
    assert not has_error(issues, ROW_T003)


def test_t004_dollar_sign_stripped(result):
    clean_rows, issues = result
    row = clean_row(clean_rows, ROW_T004)
    assert row["total"] == 7.61
    assert has_issue(issues, ROW_T004, "total", validate.WARNING)
    assert not has_error(issues, ROW_T004)


def test_t005_unknown_values_mapped_to_other(result):
    clean_rows, issues = result
    row = clean_row(clean_rows, ROW_T005)
    assert row["restaurant_type"] == "Other"
    assert row["cuisine"] == "Other"
    assert has_issue(issues, ROW_T005, "restaurant_type", validate.WARNING)
    assert has_issue(issues, ROW_T005, "cuisine", validate.WARNING)
    assert not has_error(issues, ROW_T005)


def test_t006_sum_mismatch_is_warning(result):
    clean_rows, issues = result
    row = clean_row(clean_rows, ROW_T006)
    assert row["total"] == 39.18
    assert has_issue(issues, ROW_T006, "total", validate.WARNING)
    assert not has_error(issues, ROW_T006)


def test_t007_missing_total_excluded(result):
    _, issues = result
    assert has_issue(issues, ROW_T007, "total", validate.ERROR)


def test_t008_impossible_date_excluded(result):
    _, issues = result
    assert has_issue(issues, ROW_T008, "date", validate.ERROR)


def test_t002_second_duplicate_excluded(result):
    clean_rows, issues = result
    assert has_issue(issues, ROW_T002_SECOND, "receipt_id", validate.ERROR)
    assert has_issue(issues, ROW_T002_SECOND, "payment_method", validate.WARNING)
    assert "Shake Shack" not in list(clean_rows["merchant"])


def test_t010_text_total_excluded(result):
    _, issues = result
    assert has_issue(issues, ROW_T010, "total", validate.ERROR)


def test_t011_empty_date_kept_with_warning(result):
    clean_rows, issues = result
    row = clean_row(clean_rows, ROW_T011)
    assert row["date"] == ""
    assert row["total"] == 12.54
    assert has_issue(issues, ROW_T011, "date", validate.WARNING)
    assert not has_error(issues, ROW_T011)


def test_t011_left_out_of_yearly_totals(result):
    clean_rows, _ = result
    row = clean_row(clean_rows, ROW_T011)
    assert pd.isna(row["year"])

    by_year = clean_rows.groupby("year")["total"].sum()
    assert by_year.sum() == pytest.approx(clean_rows["total"].sum() - 12.54)


# --- Smaller rules, using validate_rows directly --------------------------


def make_row(**changes):
    """Return a valid row dict, with some values changed."""
    row = {
        "receipt_id": "X001",
        "date": "2026-10-02",
        "merchant": "Chipotle",
        "restaurant_type": "Fast Food",
        "cuisine": "Mexican",
        "description": "Burrito bowl and soda",
        "subtotal": "12.45",
        "tax": "1.12",
        "tip": "",
        "total": "13.57",
        "currency": "USD",
        "payment_method": "Card",
        "confidence": "high",
        "notes": "",
    }
    row.update(changes)
    return row


def test_valid_row_has_no_issues():
    clean_rows, issues = validate.validate_rows([make_row()])
    assert len(clean_rows) == 1
    assert issues == []


def test_short_year_date_converted():
    clean_rows, issues = validate.validate_rows([make_row(date="10/02/26")])
    assert clean_rows.iloc[0]["date"] == "2026-10-02"
    assert has_issue(issues, 2, "date", validate.WARNING)


def test_empty_tip_counts_as_zero_in_sum_check():
    _, issues = validate.validate_rows([make_row(total="20.00")])
    assert has_issue(issues, 2, "total", validate.WARNING)


def test_sum_within_tolerance_is_not_flagged():
    _, issues = validate.validate_rows([make_row(total="13.62")])
    assert issues == []


def test_empty_date_is_warning():
    clean_rows, issues = validate.validate_rows(
        [make_row(date="", confidence="low", notes="Date faded")]
    )
    assert len(clean_rows) == 1
    assert has_issue(issues, 2, "date", validate.WARNING)
    assert not has_error(issues, 2)


def test_unparseable_date_is_error():
    clean_rows, issues = validate.validate_rows([make_row(date="sometime in May")])
    assert len(clean_rows) == 0
    assert has_issue(issues, 2, "date", validate.ERROR)


def test_year_column_from_date():
    clean_rows, _ = validate.validate_rows([make_row()])
    assert clean_rows.iloc[0]["year"] == 2026


def test_lowercase_enum_fixed_with_warning():
    clean_rows, issues = validate.validate_rows([make_row(payment_method="card")])
    assert clean_rows.iloc[0]["payment_method"] == "Card"
    assert has_issue(issues, 2, "payment_method", validate.WARNING)


def test_unknown_payment_method_becomes_unknown():
    clean_rows, _ = validate.validate_rows([make_row(payment_method="Check")])
    assert clean_rows.iloc[0]["payment_method"] == "Unknown"


def test_non_numeric_tax_is_cleared_with_warning():
    clean_rows, issues = validate.validate_rows([make_row(tax="abc")])
    assert len(clean_rows) == 1
    assert has_issue(issues, 2, "tax", validate.WARNING)


# --- Bad files never crash ------------------------------------------------


def test_missing_file_does_not_crash(tmp_path):
    clean_rows, issues = validate.validate_file(tmp_path / "nope.csv")
    assert len(clean_rows) == 0
    assert issues[0].severity == validate.ERROR


def test_empty_file_does_not_crash(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    clean_rows, issues = validate.validate_file(path)
    assert len(clean_rows) == 0
    assert issues[0].severity == validate.ERROR


def test_missing_column_does_not_crash(tmp_path):
    path = tmp_path / "no_total.csv"
    path.write_text("receipt_id,date,merchant\nX001,2026-10-02,Chipotle\n")
    clean_rows, issues = validate.validate_file(path)
    assert len(clean_rows) == 0
    assert has_issue(issues, 1, "total", validate.ERROR)


def test_short_row_is_excluded(tmp_path):
    path = tmp_path / "short.csv"
    header = ",".join(validate.COLUMNS)
    path.write_text(header + "\nX001,2026-10-02,Chipotle\n")
    clean_rows, issues = validate.validate_file(path)
    assert len(clean_rows) == 0
    assert has_error(issues, 2)
