# Stage 1 Prompt: Food Receipt Extraction

**Tool:** any vision-capable chat AI (tested with ChatGPT)
**Input:** food receipt photos named `R001.jpg`, `R002.jpg`, ...
**Output:** CSV rows following [`schema.md`](../schema.md), saved to `data/expenses.csv`

## How to use

1. Rename photos to `R001.jpg`, `R002.jpg`, ... so each row can be traced to its photo.
2. Start a **new chat** for each run, so earlier conversations don't influence the output.
3. Upload photos **in file-name order** (R001, R002, ...). Chat tools often can't see file names, so upload order is what sets the IDs. Upload up to 10 per message; smaller batches extract more accurately. Check the order in the upload tray before sending: some file pickers sort by date, not name.
4. Paste the prompt below, and change `FIRST ID IN THIS BATCH` to the first photo you uploaded (e.g. `R011` for the second batch of 10). Without this, every new chat starts numbering again at R001, and the rows clash with earlier batches.
5. Before saving, spot-check two or three rows against their photos (merchant and total). If they don't match, the upload order was wrong: start a new chat and redo the batch.
6. Copy the CSV from the reply into `data/expenses.csv`. For later batches, paste the rows without repeating the header line.

## Prompt

```text
FIRST ID IN THIS BATCH: R001

You are a data extraction assistant. Extract data from each attached US food receipt photo into CSV rows that follow the schema below exactly. A program will parse your output, so any deviation from the format will break it.

COLUMNS (in this order):
receipt_id,date,merchant,restaurant_type,cuisine,description,subtotal,tax,tip,total,currency,payment_method,confidence,notes

RULES:
- One row per photo, in the order the photos were attached.
- receipt_id: the photo's file name without extension (e.g. R001). If you cannot see file names, number the photos in upload order starting from FIRST ID IN THIS BATCH (e.g. R011, R012, ...).
- date: YYYY-MM-DD. US receipts print MM/DD/YYYY or MM/DD/YY (10/03/26 means 2026-10-03).
- merchant: business name as printed, in Title Case.
- restaurant_type: exactly one of Fast Food, Casual Dining, Fine Dining, Cafe, Bar, Other.
- cuisine: exactly one of American, Mexican, Latin American, Italian, Japanese, Chinese, Other Asian, Mediterranean, Other.
- description: up to 6 words naming the main items.
- subtotal: food and drink after any discounts, before tax and tip. If a discount is printed, subtract it from the printed subtotal. Empty if not shown.
- tax: sales tax. Empty if not shown.
- tip: tip or gratuity actually charged, printed or handwritten. Suggested gratuity amounts are not tips. 0.00 only if a tip line shows zero. Empty if there is no tip line. Item modifier lines priced at 0.00 (e.g. No Cheese 0.00) are not tips.
- total: the final amount paid including tax and tip. If a tip and total are handwritten, use the handwritten total. Never use the amount tendered, change or a balance due line.
- All money values: exactly 2 decimals, no $ sign, spaces or thousands separators ($1,204.50 becomes 1204.50).
- currency: 3-letter ISO code, normally USD.
- payment_method: exactly one of Cash, Card, Digital Wallet, Unknown. Apple Pay and Google Pay are Digital Wallet; credit and debit cards are Card.
- confidence: based only on date, merchant and total. high if all three are clearly readable; medium if one was inferred or partly legible; low if any is missing or doubtful, or if the image is not a food receipt. restaurant_type, cuisine and a missing payment method do not affect confidence.
- notes: empty when confidence is high; otherwise a short reason.
- No spaces before or after any value. Text must not contain commas, double quotes or line breaks. Replace commas with a space or hyphen.
- Never guess an unreadable value. Leave it empty and explain in notes if it lowers confidence.

EXAMPLE OUTPUT:
receipt_id,date,merchant,restaurant_type,cuisine,description,subtotal,tax,tip,total,currency,payment_method,confidence,notes
R001,2026-10-02,Chipotle,Fast Food,Mexican,Burrito bowl and soda,12.45,1.12,,13.57,USD,Card,high,
R002,2026-10-04,Olive Garden,Casual Dining,Italian,Pasta and breadsticks,38.50,3.47,8.00,49.97,USD,Card,medium,Tip handwritten and partly legible
R003,,Blue Bottle Coffee,Cafe,American,Latte and croissant,9.75,0.88,,10.63,USD,Unknown,low,Date faded

OUTPUT FORMAT:
Reply with only the CSV, including the header row, inside a single code block. No explanation before or after.
```
