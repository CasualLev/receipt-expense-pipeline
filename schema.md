# Expense CSV Schema

This file is the contract between the two stages of the workflow. Stage 1 (Chat AI) must produce a CSV that follows it, and Stage 2 (IDE AI) may assume nothing beyond it.

- **Location:** `data/expenses.csv`
- **Encoding:** UTF-8
- **Delimiter:** comma
- **Header row:** required, with columns in the order below
- **Granularity:** one row per receipt photo

## Columns

| # | Column | Type | Rules |
|---|--------|------|-------|
| 1 | `receipt_id` | text | The photo's file name without extension (e.g. `R001` for `R001.jpg`). If file names aren't visible, number in upload order: `R001`, `R002`, ... Must be unique. |
| 2 | `date` | date | `YYYY-MM-DD`. US receipts print dates as `MM/DD/YYYY` or `MM/DD/YY`; convert them. Empty if unreadable. |
| 3 | `merchant` | text | Business name as printed. Empty if unreadable. |
| 4 | `category` | enum | Exactly one of: `Groceries`, `Dining`, `Transport`, `Shopping`, `Bills`, `Health`, `Other`. |
| 5 | `description` | text | Up to 6 words summarizing the purchase (e.g. `Weekly groceries`). |
| 6 | `amount` | number | Final total paid, including sales tax and tip. If a tip and total are handwritten, use the handwritten total. Never use the subtotal, amount tendered or change. Digits with a `.` and exactly 2 decimals (e.g. `54.37`). No `$`, spaces or thousands separators. Empty if unreadable. |
| 7 | `currency` | enum | 3-letter ISO code (normally `USD`). If none is shown, use the default currency given in the prompt. |
| 8 | `payment_method` | enum | Exactly one of: `Cash`, `Card`, `Digital Wallet`, `Unknown`. `Digital Wallet` covers Apple Pay, Google Pay and similar; `Card` covers credit and debit cards. |
| 9 | `confidence` | enum | `high` = every field clearly read; `medium` = one field inferred or partly legible; `low` = date, merchant or amount missing or doubtful, or the image is not a receipt. |
| 10 | `notes` | text | Empty when confidence is `high`. Otherwise a short reason (e.g. `Total partly faded`). |

## Text rules

Text fields must not contain commas, double quotes or line breaks. Replace commas with a space or a hyphen. This keeps the CSV parseable without quoting.

## Missing data

Unreadable values are left **empty**, never guessed or filled with placeholders like `N/A` or `0`. Every row with an empty `date`, `merchant` or `amount` must have `confidence` set to `low` and a reason in `notes`.

## Example

```csv
receipt_id,date,merchant,category,description,amount,currency,payment_method,confidence,notes
R001,2026-10-02,Trader Joe's,Groceries,Weekly groceries,54.37,USD,Card,high,
R002,2026-10-03,Shell,Transport,Gasoline,41.20,USD,Digital Wallet,medium,Payment method inferred
R003,,CVS Pharmacy,Health,Medicine,12.89,USD,Cash,low,Date faded
```
