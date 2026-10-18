"""Save PNG charts of food spending from the validated expense rows.

Use make_charts(clean_rows) with the clean rows from validate.validate_file.
A chart without enough data is skipped and the reason is logged.
"""

import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files only, no window

import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

import report
import validate

DEFAULT_CHART_DIR = Path("output") / "charts"

# Colors from the reference data-viz palette: one series color, ink for text.
BAR_COLOR = "#2a78d6"
SURFACE_COLOR = "#fcfcfb"
TEXT_COLOR = "#0b0b0b"
MUTED_TEXT_COLOR = "#52514e"
GRID_COLOR = "#e4e3df"

BAR_THICKNESS = 0.55
COLUMN_THICKNESS = 0.4
DPI = 150

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chart data
# ---------------------------------------------------------------------------


def spend_by(clean_rows, column):
    """Return total spent per value of column, largest first."""
    totals = clean_rows.groupby(column)["total"].sum()
    return totals.sort_values(ascending=False)


def spend_by_year(clean_rows):
    """Return total spent per year, oldest first. Rows with no date are left out."""
    totals = clean_rows.groupby("year")["total"].sum()
    return totals.sort_index()


def average_by_restaurant_type(clean_rows):
    """Return the average total per visit for each restaurant type, largest first."""
    averages = clean_rows.groupby("restaurant_type")["total"].mean()
    return averages.sort_values(ascending=False)


def tip_percentages_by_receipt(clean_rows):
    """Return tip as a % of subtotal per receipt with a tip, labeled by merchant.

    The receipt_id is added to each label so two visits to the same
    merchant get separate bars. Largest tip first.
    """
    fractions = report.tip_percentages(clean_rows)
    fractions = fractions.sort_values(ascending=False)
    labels = []
    values = []
    for index, fraction in fractions.items():
        merchant = clean_rows.loc[index, "merchant"]
        receipt_id = clean_rows.loc[index, "receipt_id"]
        if merchant == "":
            merchant = "Unknown merchant"
        labels.append(f"{merchant} ({receipt_id})")
        values.append(fraction * 100)
    return labels, values


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def format_money(value):
    """Format a number as dollars, e.g. $1,234.50."""
    return f"${value:,.2f}"


def format_percent(value):
    """Format a number that is already a percentage, e.g. 18.5%."""
    return f"{value:.1f}%"


def value_axis_limits(values):
    """Return (low, high) for the value axis, with room for the value labels."""
    low = min(0, min(values))
    high = max(0, max(values))
    span = high - low
    if span == 0:
        span = 1
    padding = span * 0.18
    if low < 0:
        low = low - padding
    return low, high + padding


def category_axis_limits(count):
    """Return (low, high) for the category axis.

    The extra space at each end stops one or two bars from filling the chart.
    """
    return -0.8, count - 0.2


def style_axes(fig, ax, horizontal):
    """Apply the shared look: light surface, recessive axes, hairline grid."""
    fig.patch.set_facecolor(SURFACE_COLOR)
    ax.set_facecolor(SURFACE_COLOR)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(GRID_COLOR)
    ax.tick_params(colors=MUTED_TEXT_COLOR, length=0)
    if horizontal:
        ax.xaxis.grid(True, color=GRID_COLOR, linewidth=1)
    else:
        ax.yaxis.grid(True, color=GRID_COLOR, linewidth=1)
    ax.set_axisbelow(True)


def draw_bar_chart(chart, path):
    """Draw one bar chart described by a dict and save it as a PNG.

    chart keys: labels, values, title, value_axis, category_axis,
    horizontal, tick_format, label_format.
    """
    labels = chart["labels"]
    values = chart["values"]
    horizontal = chart["horizontal"]

    if horizontal:
        height = 2.0 + 0.45 * len(labels)
        fig, ax = plt.subplots(figsize=(8, height))
        # Reverse so the first item is drawn at the top.
        bars = ax.barh(labels[::-1], values[::-1], height=BAR_THICKNESS, color=BAR_COLOR)
        ax.set_ylim(category_axis_limits(len(labels)))
        ax.set_xlim(value_axis_limits(values))
        ax.xaxis.set_major_formatter(StrMethodFormatter(chart["tick_format"]))
        ax.set_xlabel(chart["value_axis"], color=MUTED_TEXT_COLOR)
        ax.set_ylabel(chart["category_axis"], color=MUTED_TEXT_COLOR)
        bar_values = values[::-1]
    else:
        width = max(4.5, 2.5 + 0.9 * len(labels))
        fig, ax = plt.subplots(figsize=(width, 5))
        bars = ax.bar(labels, values, width=COLUMN_THICKNESS, color=BAR_COLOR)
        ax.set_xlim(category_axis_limits(len(labels)))
        ax.set_ylim(value_axis_limits(values))
        ax.yaxis.set_major_formatter(StrMethodFormatter(chart["tick_format"]))
        ax.set_ylabel(chart["value_axis"], color=MUTED_TEXT_COLOR)
        ax.set_xlabel(chart["category_axis"], color=MUTED_TEXT_COLOR)
        bar_values = values

    style_axes(fig, ax, horizontal)

    value_labels = []
    for value in bar_values:
        value_labels.append(chart["label_format"](value))
    ax.bar_label(bars, labels=value_labels, padding=4, color=TEXT_COLOR, fontsize=9)

    ax.set_title(chart["title"], color=TEXT_COLOR, loc="left", fontsize=13, pad=12)
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, facecolor=SURFACE_COLOR)
    plt.close(fig)


# ---------------------------------------------------------------------------
# The five charts
# ---------------------------------------------------------------------------


def money_bar_chart(series, title, category_axis, value_axis, horizontal):
    """Describe a bar chart of dollar amounts from a pandas Series."""
    labels = []
    for label in series.index:
        labels.append(str(label))
    return {
        "labels": labels,
        "values": list(series.values),
        "title": title,
        "value_axis": value_axis,
        "category_axis": category_axis,
        "horizontal": horizontal,
        "tick_format": "${x:,.0f}",
        "label_format": format_money,
    }


def build_charts(clean_rows):
    """Return {file name: chart dict or a reason it was skipped}."""
    charts = {}

    by_type = spend_by(clean_rows, "restaurant_type")
    if len(by_type) == 0:
        charts["spend_by_restaurant_type.png"] = "no receipts to chart"
    else:
        charts["spend_by_restaurant_type.png"] = money_bar_chart(
            by_type, "Total spent by restaurant type", "Restaurant type", "Total spent ($)", True
        )

    by_cuisine = spend_by(clean_rows, "cuisine")
    if len(by_cuisine) == 0:
        charts["spend_by_cuisine.png"] = "no receipts to chart"
    else:
        charts["spend_by_cuisine.png"] = money_bar_chart(
            by_cuisine, "Total spent by cuisine", "Cuisine", "Total spent ($)", True
        )

    by_year = spend_by_year(clean_rows)
    if len(by_year) == 0:
        charts["spend_by_year.png"] = "no receipts with a date"
    else:
        charts["spend_by_year.png"] = money_bar_chart(
            by_year, "Total spent by year", "Year", "Total spent ($)", False
        )

    averages = average_by_restaurant_type(clean_rows)
    if len(averages) == 0:
        charts["avg_cost_per_visit.png"] = "no receipts to chart"
    else:
        charts["avg_cost_per_visit.png"] = money_bar_chart(
            averages,
            "Average cost per visit by restaurant type",
            "Restaurant type",
            "Average total per visit ($)",
            True,
        )

    tip_labels, tip_values = tip_percentages_by_receipt(clean_rows)
    if len(tip_values) == 0:
        charts["tip_percentage.png"] = "no receipts with a tip line"
    else:
        charts["tip_percentage.png"] = {
            "labels": tip_labels,
            "values": tip_values,
            "title": "Tip as a percentage of subtotal",
            "value_axis": "Tip (% of subtotal)",
            "category_axis": "Merchant (receipt)",
            "horizontal": True,
            "tick_format": "{x:.0f}%",
            "label_format": format_percent,
        }

    return charts


def make_charts(clean_rows, chart_dir=DEFAULT_CHART_DIR):
    """Save every chart that has data. Returns (created paths, skip messages).

    When a chart is skipped, an old copy from an earlier run is deleted so
    it can't be mistaken for a chart of this data.
    """
    chart_dir = Path(chart_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)

    created = []
    skipped = []
    for file_name, chart in build_charts(clean_rows).items():
        path = chart_dir / file_name
        if isinstance(chart, str):
            message = f"Skipped {file_name}: {chart}"
            logger.warning(message)
            skipped.append(message)
            if path.exists():
                path.unlink()
            continue
        draw_bar_chart(chart, path)
        created.append(path)
    return created, skipped


def main():
    """Validate a CSV and save the charts: python src/charts.py data/expenses.csv"""
    if len(sys.argv) != 2:
        print("Usage: python src/charts.py path/to/expenses.csv")
        return 1

    logging.basicConfig(format="%(message)s")
    clean_rows, _ = validate.validate_file(sys.argv[1])
    created, _ = make_charts(clean_rows)
    for path in created:
        print(f"Chart saved to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
