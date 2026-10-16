# Stage 2 Prompts: Validation, Report and Charts (IDE AI)

**Tool:** any IDE AI assistant (tested with Claude Code in VS Code)
**Input:** `data/expenses.csv` following [`schema.md`](../schema.md)
**Output:** cleaned data, error log, Excel report and charts in `output/`

Send these prompts one at a time, in order. Review and test each step before moving to the next. The project rules live in `CLAUDE.md`, so the prompts can stay short.

## Prompt 1: Validation

```text
Read schema.md and tests/fixtures/README.md. Then write src/validate.py.

It should load a CSV that is supposed to follow schema.md, clean what can be safely cleaned (trim spaces, convert MM/DD/YYYY dates, strip $ signs, map values outside the allowed lists to Other or Unknown), and check every rule in the schema, including the subtotal + tax + tip = total check.

It returns the clean rows and a list of issues. Each issue has receipt_id, row number, column, problem and severity (error or warning), following the severity rules in CLAUDE.md.

Then write tests/test_validate.py using pytest and tests/fixtures/expenses_broken.csv, checking every expected result in the fixture README. Run the tests and fix any failures.
```

## Prompt 2: Report

```text
Write src/report.py. Using the clean rows from validate.py, create output/food_report.xlsx with these sheets:

1. Summary: number of receipts, total spent, average per visit, average tip percentage (only receipts with a tip), and the number of rows excluded and flagged.
2. By Restaurant Type: visits, total spent and average per visit for each type.
3. By Cuisine: the same breakdown by cuisine.
4. By Year: visits and total spent per year.
5. Receipts: every clean row.
6. Needs Review: every error and warning from validation.

Format money as currency, bold the header rows and set sensible column widths.
```

## Prompt 3: Charts

```text
Write src/charts.py. Using the clean rows, save these PNG charts to output/charts/:

1. spend_by_restaurant_type.png: horizontal bar chart of total spent per type
2. spend_by_cuisine.png: horizontal bar chart of total spent per cuisine
3. spend_by_year.png: bar chart of total spent per year
4. avg_cost_per_visit.png: average total per visit by restaurant type
5. tip_percentage.png: tip as a percentage of subtotal for each receipt with a tip, labeled by merchant

Give every chart a title, axis labels with $ where relevant, and value labels on the bars. Skip any chart without enough data and log why instead of crashing.
```

## Prompt 4: One-command pipeline

```text
Write src/run_pipeline.py that takes a CSV path, runs validation, the report and the charts in order, writes output/expenses_clean.csv and output/issues.csv, and prints a short summary: rows read, rows kept, rows excluded, warnings, and the paths of every file created.

Run it on data/expenses.csv and on tests/fixtures/expenses_broken.csv and show me both summaries. Then update requirements.txt.
```
