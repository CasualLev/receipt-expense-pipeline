# Food Expense CSV Schema

This file is the contract between the two stages of the workflow. Stage 1 (Chat AI) must produce a CSV that follows it, and Stage 2 (IDE AI) may assume nothing beyond it.

- **Location:** `data/expenses.csv`
- **Encoding:** UTF-8
- **Delimiter:** comma
- **Header row:** required, with columns in the order below
- **Granularity:** one row per receipt photo
- **Scope:** US food and drink receipts (restaurants, fast food, cafes, bars)

## Columns

| # | Column | Type | Rules |
|---|--------|------|-------|
| 1 | `receipt_id` | text | The photo's file name without extension (e.g. `R001` for `R001.jpg`). If file names aren't visible, number in upload order, so photos must be uploaded in file-name order. Must be unique. |
| 2 | `date` | date | `YYYY-MM-DD`. US receipts print `MM/DD/YYYY` or `MM/DD/YY`; convert them. Empty if unreadable. |
| 3 | `merchant` | text | Business name as printed, in Title Case (e.g. `Grand Lux Cafe`). Empty if unreadable. |
| 4 | `restaurant_type` | enum | Exactly one of: `Fast Food`, `Casual Dining`, `Fine Dining`, `Cafe`, `Bar`, `Other`. |
| 5 | `cuisine` | enum | Exactly one of: `American`, `Mexican`, `Latin American`, `Italian`, `Japanese`, `Chinese`, `Other Asian`, `Mediterranean`, `Other`. |
| 6 | `description` | text | Up to 6 words naming the main items (e.g. `Burrito bowl and soda`). |
| 7 | `subtotal` | number | Food and drink after any discounts, before tax and tip. If a discount is printed, subtract it from the printed subtotal. Empty if not shown. |
| 8 | `tax` | number | Sales tax. Empty if not shown. |
| 9 | `tip` | number | Tip or gratuity actually charged, printed or handwritten. Suggested gratuity amounts are not tips. `0.00` only if a tip line shows zero; empty if there is no tip line. Item modifier lines priced at 0.00 are not tips. |
| 10 | `total` | number | Final amount paid, including tax and tip. If a tip and total are handwritten, use the handwritten total. Never use the amount tendered, change or a balance due line. Empty if unreadable. |
| 11 | `currency` | enum | 3-letter ISO code, normally `USD`. |
| 12 | `payment_method` | enum | Exactly one of: `Cash`, `Card`, `Digital Wallet`, `Unknown`. Apple Pay and Google Pay are `Digital Wallet`; credit and debit cards are `Card`. |
| 13 | `confidence` | enum | Based only on `date`, `merchant` and `total`. `high` = all three clearly read; `medium` = one inferred or partly legible; `low` = any missing or doubtful, or the image is not a food receipt. |
| 14 | `notes` | text | Empty when confidence is `high`. Otherwise a short reason. |

## Number rules

All money columns use exactly 2 decimals (e.g. `54.37`), with no `$`, spaces or thousands separators.

When `subtotal`, `tax`, `tip` and `total` are all present, `subtotal + tax + tip` should equal `total` within 0.05. Discounts or service charges can break this; Stage 2 flags mismatches for review rather than rejecting them.

## Inferred fields

`restaurant_type` and `cuisine` are classifications inferred from the merchant name and items, not read from the receipt. They do not affect `confidence`. A payment method that isn't shown is recorded as `Unknown` and does not affect `confidence` either.

## Text rules

Values must have no leading or trailing spaces. Text fields must not contain commas, double quotes or line breaks; replace commas with a space or hyphen.

## Missing data

Unreadable values are left **empty**, never guessed or filled with placeholders like `N/A` or `0`. A row with an empty `date`, `merchant` or `total` must have `confidence` set to `low` and a reason in `notes`.

## Example

```csv
receipt_id,date,merchant,restaurant_type,cuisine,description,subtotal,tax,tip,total,currency,payment_method,confidence,notes
R001,2026-10-02,Chipotle,Fast Food,Mexican,Burrito bowl and soda,12.45,1.12,,13.57,USD,Card,high,
R002,2026-10-04,Olive Garden,Casual Dining,Italian,Pasta and breadsticks,38.50,3.47,8.00,49.97,USD,Card,medium,Tip handwritten and partly legible
R003,,Blue Bottle Coffee,Cafe,American,Latte and croissant,9.75,0.88,,10.63,USD,Unknown,low,Date faded
```
