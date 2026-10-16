# Project context for Claude Code

This repo is Stage 2 of a two-stage AI workflow that tracks food spending.

- **Stage 1 (Chat AI):** reads US food receipt photos in `receipts/` and writes `data/expenses.csv`.
- **Stage 2 (you):** validates that CSV, then produces a spending report and charts.

## Rules

- `schema.md` is the source of truth for the CSV format. Read it before writing any code, and never assume anything it doesn't say.
- The CSV comes from an AI and may be messy: extra spaces, wrong date formats, `$` signs in numbers, values outside the allowed lists, arithmetic that doesn't add up, Windows line endings. The pipeline must **never crash on bad data**. It fixes what it safely can, and logs everything else.
- Two severities:
  - **error**: the row can't be used (missing or non-numeric `total`, unparseable or impossible date (an empty date is only a warning), duplicate `receipt_id`). Exclude it from the report and log it.
  - **warning**: the row is usable but needs a human look (`subtotal + tax + tip` differs from `total` by more than 0.05, `low` or `medium` confidence, a value that was auto-cleaned). Keep it in the report and log it.
- Don't modify `data/expenses.csv`. Write cleaned data and all generated files to `output/`.
- Code goes in `src/`, tests in `tests/`.
- Python 3 with pandas, matplotlib, openpyxl and pytest. Keep dependencies in `requirements.txt`.
- Run everything with one command: `python src/run_pipeline.py data/expenses.csv`.
- Keep the code readable for a student: small functions, short docstrings, no clever one-liners.
