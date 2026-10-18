"""Validate and clean the Stage 1 food expense CSV.

The rules come from schema.md and the severity rules from CLAUDE.md:

- error: the row can't be used, so it is excluded from the clean rows.
- warning: the row is kept but needs a human look.

Use validate_file(path) to get (clean_rows, issues). It never raises on bad data.
"""

import csv
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime

import pandas as pd

COLUMNS = [
    "receipt_id",
    "date",
    "merchant",
    "restaurant_type",
    "cuisine",
    "description",
    "subtotal",
    "tax",
    "tip",
    "total",
    "currency",
    "payment_method",
    "confidence",
    "notes",
]
TEXT_COLUMNS = ["merchant", "description", "notes"]
MONEY_COLUMNS = ["subtotal", "tax", "tip", "total"]

RESTAURANT_TYPES = ["Fast Food", "Casual Dining", "Fine Dining", "Cafe", "Bar", "Other"]
CUISINES = [
    "American",
    "Mexican",
    "Latin American",
    "Italian",
    "Japanese",
    "Chinese",
    "Other Asian",
    "Mediterranean",
    "Other",
]
PAYMENT_METHODS = ["Cash", "Card", "Digital Wallet", "Unknown"]
CONFIDENCE_LEVELS = ["high", "medium", "low"]

# Payment names that schema.md maps to an allowed value.
PAYMENT_SYNONYMS = {
    "apple pay": "Digital Wallet",
    "google pay": "Digital Wallet",
    "credit": "Card",
    "credit card": "Card",
    "debit": "Card",
    "debit card": "Card",
}

REPORT_CURRENCY = "USD"
SUM_TOLERANCE = 0.05
MAX_DESCRIPTION_WORDS = 6

ERROR = "error"
WARNING = "warning"
ISSUE_FIELDS = ["receipt_id", "row", "column", "problem", "severity"]


@dataclass
class Issue:
    """One problem found in the CSV."""

    receipt_id: str
    row: int
    column: str
    problem: str
    severity: str


class RowLog:
    """Collects the issues found in one row."""

    def __init__(self, receipt_id, row):
        self.receipt_id = receipt_id
        self.row = row
        self.issues = []

    def warning(self, column, problem):
        """Record a warning: the row is kept."""
        self.issues.append(Issue(self.receipt_id, self.row, column, problem, WARNING))

    def error(self, column, problem):
        """Record an error: the row will be excluded."""
        self.issues.append(Issue(self.receipt_id, self.row, column, problem, ERROR))

    def has_error(self):
        """Return True if any error was recorded for this row."""
        for issue in self.issues:
            if issue.severity == ERROR:
                return True
        return False


# ---------------------------------------------------------------------------
# Reading the file
# ---------------------------------------------------------------------------


def read_csv_rows(path, issues):
    """Read the CSV into a list of (row_number, dict) pairs.

    Row numbers match a spreadsheet: the header is row 1, the first data row is 2.
    File and header problems are added to issues instead of raising.
    """
    try:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as file:
            all_rows = list(csv.reader(file))
    except (OSError, csv.Error) as problem:
        issues.append(Issue("", 0, "", f"Could not read file: {problem}", ERROR))
        return []

    if len(all_rows) == 0:
        issues.append(Issue("", 0, "", "File is empty", ERROR))
        return []

    header = []
    for name in all_rows[0]:
        header.append(name.strip())
    check_header(header, issues)

    records = []
    for index, values in enumerate(all_rows[1:]):
        row_number = index + 2
        if len(values) == 0:
            continue  # blank line
        if len(values) != len(header):
            receipt_id = values[0].strip()
            problem = f"Expected {len(header)} values but found {len(values)}"
            issues.append(Issue(receipt_id, row_number, "", problem, ERROR))
            continue
        records.append((row_number, dict(zip(header, values))))
    return records


def check_header(header, issues):
    """Log missing, extra or reordered columns in the header row."""
    for column in COLUMNS:
        if column not in header:
            problem = f"Column '{column}' is missing from the header"
            issues.append(Issue("", 1, column, problem, ERROR))
    for column in header:
        if column not in COLUMNS:
            problem = f"Unexpected column '{column}' was ignored"
            issues.append(Issue("", 1, column, problem, WARNING))
    if set(header) == set(COLUMNS) and header != COLUMNS:
        issues.append(Issue("", 1, "", "Columns are not in the schema order", WARNING))


# ---------------------------------------------------------------------------
# Cleaning single values
# ---------------------------------------------------------------------------


def trim_value(value, column, log):
    """Remove leading and trailing spaces, with a warning if any were found."""
    if value is None:
        return ""
    value = str(value)
    trimmed = value.strip()
    if trimmed != value:
        log.warning(column, f"Removed extra spaces from '{value}'")
    return trimmed


def clean_text(value, column, log):
    """Replace commas, double quotes and line breaks, which schema.md forbids."""
    cleaned = value
    for bad_character in [",", '"', "\r", "\n"]:
        cleaned = cleaned.replace(bad_character, " ")
    cleaned = " ".join(cleaned.split())
    if cleaned != value:
        log.warning(column, f"Removed commas, quotes or line breaks from '{value}'")
    return cleaned


def clean_receipt_id(value, seen_ids, log):
    """Check the receipt_id is present and not used by an earlier row."""
    if value == "":
        log.error("receipt_id", "receipt_id is missing")
    elif value in seen_ids:
        log.error("receipt_id", f"Duplicate receipt_id '{value}'; the first row with it is kept")
    else:
        seen_ids.add(value)
    return value


def clean_date(value, log):
    """Return the date as YYYY-MM-DD, converting MM/DD/YYYY and MM/DD/YY.

    An empty date is only a warning: the row is kept but has no year.
    A date that can't be parsed, or doesn't exist, is an error.
    """
    if value == "":
        log.warning("date", "Date is missing, so this row is left out of anything grouped by year")
        return ""

    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value):
        date_format = "%Y-%m-%d"
    elif re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
        date_format = "%m/%d/%Y"
    elif re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2}", value):
        date_format = "%m/%d/%y"
    else:
        log.error("date", f"Date '{value}' is not in a recognised format")
        return value

    try:
        parsed = datetime.strptime(value, date_format)
    except ValueError:
        log.error("date", f"Date '{value}' is not a real date")
        return value

    iso_date = parsed.strftime("%Y-%m-%d")
    if iso_date != value:
        log.warning("date", f"Converted date '{value}' to '{iso_date}'")
    return iso_date


def clean_money(value, column, log):
    """Return a money value as a float rounded to 2 decimals, or None if empty.

    A missing or non-numeric total is an error. Other money columns that
    aren't numbers are cleared with a warning.
    """
    if value == "":
        if column == "total":
            log.error("total", "Total is missing")
        return None

    cleaned = value.replace("$", "").replace(",", "").replace(" ", "")
    number = parse_number(cleaned)
    if number is None:
        if column == "total":
            log.error("total", f"Total '{value}' is not a number")
        else:
            log.warning(column, f"'{value}' is not a number, so it was cleared")
        return None

    if cleaned != value:
        log.warning(column, f"Removed '$', spaces or commas from '{value}'")

    if not re.fullmatch(r"-?\d+\.\d{2}", cleaned):
        log.warning(column, f"'{cleaned}' should have exactly 2 decimals")
    return round(number, 2)


def parse_number(text):
    """Convert text to a float, or return None if it isn't a normal number."""
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def clean_enum(value, allowed, fallback, column, log):
    """Return value if it is allowed, fixing capitalisation or using fallback."""
    if value in allowed:
        return value
    for option in allowed:
        if value.lower() == option.lower():
            log.warning(column, f"Changed '{value}' to '{option}'")
            return option
    log.warning(column, f"'{value}' is not an allowed value, so it was changed to '{fallback}'")
    return fallback


def clean_payment_method(value, log):
    """Map payment names such as Apple Pay to an allowed payment_method."""
    synonym = PAYMENT_SYNONYMS.get(value.lower())
    if synonym is not None:
        log.warning("payment_method", f"Changed '{value}' to '{synonym}'")
        return synonym
    return clean_enum(value, PAYMENT_METHODS, "Unknown", "payment_method", log)


def clean_currency(value, log):
    """Upper-case the currency. Only USD rows can be added to the dollar totals."""
    upper = value.upper()
    if upper != value:
        log.warning("currency", f"Changed '{value}' to '{upper}'")
    if upper == "":
        log.error("currency", "Currency is missing, so the amounts can't be added to the USD totals")
    elif upper != REPORT_CURRENCY:
        log.error("currency", f"Currency '{upper}' is not USD, so the amounts can't be added to the USD totals")
    return upper


# ---------------------------------------------------------------------------
# Checks across several columns
# ---------------------------------------------------------------------------


def check_sum(record, log):
    """Warn when subtotal + tax + tip differs from total by more than 0.05.

    An empty tip means there was no tip line, so it counts as 0.
    """
    subtotal = record["subtotal"]
    tax = record["tax"]
    tip = record["tip"]
    total = record["total"]
    if subtotal is None or tax is None or total is None:
        return
    if tip is None:
        tip = 0.0

    expected = subtotal + tax + tip
    difference = round(abs(expected - total), 2)
    if difference > SUM_TOLERANCE:
        problem = (
            f"subtotal + tax + tip = {expected:.2f} but total is {total:.2f} "
            f"(off by {difference:.2f})"
        )
        log.warning("total", problem)


def check_merchant(merchant, log):
    """Warn when the merchant is missing or clearly not in Title Case."""
    if merchant == "":
        log.warning("merchant", "Merchant is missing")
    elif merchant == merchant.lower():
        log.warning("merchant", f"Merchant '{merchant}' should be in Title Case")


def check_description(description, log):
    """Warn when the description is longer than 6 words."""
    word_count = len(description.split())
    if word_count > MAX_DESCRIPTION_WORDS:
        log.warning("description", f"Description has {word_count} words; the limit is 6")


def check_confidence(record, missing_fields, log):
    """Apply the confidence and notes rules from schema.md."""
    confidence = record["confidence"]
    notes = record["notes"]

    if confidence != "high":
        reason = notes if notes else "no reason given"
        log.warning("confidence", f"Confidence is {confidence}: {reason}")

    if len(missing_fields) > 0 and confidence != "low":
        missing = ", ".join(missing_fields)
        log.warning("confidence", f"{missing} missing, so confidence should be low, not {confidence}")

    if confidence == "high" and notes != "":
        log.warning("notes", "Notes should be empty when confidence is high")
    if confidence != "high" and notes == "":
        log.warning("notes", "Notes should give a reason when confidence is not high")


# ---------------------------------------------------------------------------
# Whole rows and whole files
# ---------------------------------------------------------------------------


def find_missing_fields(record):
    """Return which of date, merchant and total are empty."""
    missing = []
    for column in ["date", "merchant", "total"]:
        if record[column] == "":
            missing.append(column)
    return missing


def clean_row(raw, row_number, seen_ids):
    """Clean and check one row. Returns (record, issues)."""
    receipt_id = str(raw.get("receipt_id") or "").strip()
    log = RowLog(receipt_id, row_number)

    record = {}
    for column in COLUMNS:
        record[column] = trim_value(raw.get(column, ""), column, log)
    missing_fields = find_missing_fields(record)

    record["receipt_id"] = clean_receipt_id(record["receipt_id"], seen_ids, log)
    record["date"] = clean_date(record["date"], log)
    for column in TEXT_COLUMNS:
        record[column] = clean_text(record[column], column, log)
    record["restaurant_type"] = clean_enum(
        record["restaurant_type"], RESTAURANT_TYPES, "Other", "restaurant_type", log
    )
    record["cuisine"] = clean_enum(record["cuisine"], CUISINES, "Other", "cuisine", log)
    record["payment_method"] = clean_payment_method(record["payment_method"], log)
    record["confidence"] = clean_enum(
        record["confidence"], CONFIDENCE_LEVELS, "low", "confidence", log
    )
    record["currency"] = clean_currency(record["currency"], log)
    for column in MONEY_COLUMNS:
        record[column] = clean_money(record[column], column, log)

    check_sum(record, log)
    check_merchant(record["merchant"], log)
    check_description(record["description"], log)
    check_confidence(record, missing_fields, log)

    record["row"] = row_number
    return record, log


def year_from_date(date):
    """Return the year of a YYYY-MM-DD date, or None if the date is empty."""
    if date == "":
        return None
    return int(date[:4])


def build_dataframe(records):
    """Turn the clean records into a DataFrame with money as numbers.

    The extra year column is empty (<NA>) when the date is missing.
    groupby("year") skips those rows by default, so yearly totals leave them out.
    """
    frame = pd.DataFrame(records, columns=COLUMNS + ["row"])
    for column in MONEY_COLUMNS:
        frame[column] = pd.to_numeric(frame[column])

    years = []
    for date in frame["date"]:
        years.append(year_from_date(date))
    frame["year"] = pd.array(years, dtype="Int64")
    return frame


def validate_rows(rows, row_numbers=None):
    """Validate a list of row dicts. Returns (clean_rows, issues).

    row_numbers gives the spreadsheet row of each dict; by default the
    first dict is row 2, just below the header.
    """
    seen_ids = set()
    clean_records = []
    issues = []
    for index, raw in enumerate(rows):
        if row_numbers is None:
            row_number = index + 2
        else:
            row_number = row_numbers[index]
        record, log = clean_row(raw, row_number, seen_ids)
        issues.extend(log.issues)
        if not log.has_error():
            clean_records.append(record)
    return build_dataframe(clean_records), issues


def validate_file(path):
    """Read and validate a CSV file. Returns (clean_rows, issues)."""
    issues = []
    numbered_rows = read_csv_rows(path, issues)

    row_numbers = []
    rows = []
    for row_number, row in numbered_rows:
        row_numbers.append(row_number)
        rows.append(row)

    clean_rows, row_issues = validate_rows(rows, row_numbers)
    issues.extend(row_issues)
    return clean_rows, issues


def excluded_rows(issues):
    """Return the sorted row numbers of data rows that had an error."""
    rows = set()
    for issue in issues:
        if issue.severity == ERROR and issue.row >= 2:
            rows.add(issue.row)
    return sorted(rows)


def issues_to_dataframe(issues):
    """Turn a list of Issue objects into a DataFrame."""
    records = []
    for issue in issues:
        records.append(asdict(issue))
    return pd.DataFrame(records, columns=ISSUE_FIELDS)
