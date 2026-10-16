"""Tests for src/charts.py, using tests/fixtures/expenses_broken.csv."""

from pathlib import Path

import pytest

import charts
import validate

FIXTURE = Path(__file__).parent / "fixtures" / "expenses_broken.csv"

CHART_FILES = [
    "spend_by_restaurant_type.png",
    "spend_by_cuisine.png",
    "spend_by_year.png",
    "avg_cost_per_visit.png",
    "tip_percentage.png",
]
PNG_SIGNATURE = b"\x89PNG"


@pytest.fixture(scope="module")
def clean_rows():
    """The clean rows of the broken fixture."""
    rows, _ = validate.validate_file(FIXTURE)
    return rows


def make_row(receipt_id, date, tip):
    """Return a valid row dict with the given date and tip."""
    return {
        "receipt_id": receipt_id,
        "date": date,
        "merchant": "Chipotle",
        "restaurant_type": "Fast Food",
        "cuisine": "Mexican",
        "description": "Burrito bowl",
        "subtotal": "10.00",
        "tax": "0.00",
        "tip": tip,
        "total": "10.00",
        "currency": "USD",
        "payment_method": "Card",
        "confidence": "low",
        "notes": "Test row",
    }


# --- Chart data ------------------------------------------------------------


def test_spend_by_restaurant_type(clean_rows):
    totals = charts.spend_by(clean_rows, "restaurant_type")
    assert list(totals.index) == ["Casual Dining", "Cafe", "Other", "Fast Food"]
    assert totals["Casual Dining"] == pytest.approx(56.58 + 69.25 + 51.60)
    assert totals["Cafe"] == pytest.approx(39.18 + 12.54)


def test_spend_by_cuisine_largest_first(clean_rows):
    totals = list(charts.spend_by(clean_rows, "cuisine").values)
    assert totals == sorted(totals, reverse=True)


def test_spend_by_year_leaves_out_empty_date(clean_rows):
    totals = charts.spend_by_year(clean_rows)
    assert list(totals.index) == [2015, 2016, 2017]
    assert totals.sum() == pytest.approx(clean_rows["total"].sum() - 12.54)


def test_average_by_restaurant_type(clean_rows):
    averages = charts.average_by_restaurant_type(clean_rows)
    assert averages["Casual Dining"] == pytest.approx((56.58 + 69.25 + 51.60) / 3)
    assert averages["Fast Food"] == pytest.approx(7.61)


def test_tip_percentages_labeled_by_merchant(clean_rows):
    labels, values = charts.tip_percentages_by_receipt(clean_rows)
    assert labels == ["Cheesecake Factory (T003)", "Sage (T006)", "Pho 99 (T005)"]
    assert values == pytest.approx([20.0, 7.38 / 41 * 100, 3 / 18 * 100])


def test_value_axis_limits_leave_room_for_labels():
    low, high = charts.value_axis_limits([0.0, 100.0])
    assert low == 0
    assert high > 100
    assert charts.value_axis_limits([0.0, 0.0]) == (0, pytest.approx(0.18))


# --- Saving charts ---------------------------------------------------------


def test_all_five_charts_saved(clean_rows, tmp_path):
    created, skipped = charts.make_charts(clean_rows, tmp_path)
    assert skipped == []
    names = []
    for path in created:
        names.append(path.name)
    assert names == CHART_FILES
    for path in created:
        with open(path, "rb") as file:
            assert file.read(4) == PNG_SIGNATURE


def test_empty_data_skips_every_chart(tmp_path):
    csv_path = tmp_path / "header_only.csv"
    csv_path.write_text(",".join(validate.COLUMNS) + "\n")
    rows, _ = validate.validate_file(csv_path)
    created, skipped = charts.make_charts(rows, tmp_path / "charts")
    assert created == []
    assert len(skipped) == 5


def test_no_tips_skips_only_tip_chart(tmp_path):
    rows, _ = validate.validate_rows([make_row("X001", "2026-10-02", "")])
    created, skipped = charts.make_charts(rows, tmp_path)
    assert len(created) == 4
    assert skipped == ["Skipped tip_percentage.png: no receipts with a tip line"]


def test_zero_tip_gets_a_bar():
    rows, _ = validate.validate_rows([make_row("X001", "2026-10-02", "0.00")])
    labels, values = charts.tip_percentages_by_receipt(rows)
    assert labels == ["Chipotle (X001)"]
    assert values == [0.0]


def test_no_dates_skips_only_year_chart(tmp_path):
    rows, _ = validate.validate_rows([make_row("X001", "", "1.00")])
    created, skipped = charts.make_charts(rows, tmp_path)
    assert len(created) == 4
    assert skipped == ["Skipped spend_by_year.png: no receipts with a date"]


def test_skipped_chart_removes_old_copy(clean_rows, tmp_path):
    charts.make_charts(clean_rows, tmp_path)
    assert (tmp_path / "tip_percentage.png").exists()

    no_tips, _ = validate.validate_rows([make_row("X001", "2026-10-02", "")])
    charts.make_charts(no_tips, tmp_path)
    assert not (tmp_path / "tip_percentage.png").exists()


def test_skipped_chart_is_logged(tmp_path, caplog):
    rows, _ = validate.validate_rows([make_row("X001", "", "")])
    charts.make_charts(rows, tmp_path)
    assert "Skipped spend_by_year.png" in caplog.text
    assert "Skipped tip_percentage.png" in caplog.text
