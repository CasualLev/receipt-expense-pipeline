# Stage 1 Prompt: Receipt Extraction

**Tool:** any vision-capable chat AI (tested with ChatGPT)
**Input:** receipt photos named `R001.jpg`, `R002.jpg`, ...
**Output:** CSV rows following [`schema.md`](../schema.md), saved to `data/expenses.csv`

## How to use

1. Rename photos to `R001.jpg`, `R002.jpg`, ... so each row can be traced to its photo.
2. Start a **new chat** for each run, so earlier conversations don't influence the output.
3. Upload up to 10 photos per message; smaller batches extract more accurately.
4. Paste the prompt below.
5. Copy the CSV from the reply into `data/expenses.csv`. For later batches, paste the rows without repeating the header line.

## Prompt

```text
You are a data extraction assistant. Extract data from each attached receipt photo into CSV rows that follow the schema below exactly. A program will parse your output, so any deviation from the format will break it.

DEFAULT_CURRENCY: USD

COLUMNS (in this order):
receipt_id,date,merchant,category,description,amount,currency,payment_method,confidence,notes

RULES:
- One row per photo, in the order the photos were attached.
- receipt_id: the photo's file name without extension (e.g. R001). If you cannot see file names, use R001, R002, ... in upload order.
- date: YYYY-MM-DD. These are US receipts, so printed dates are MM/DD/YYYY or MM/DD/YY (10/03/26 means 2026-10-03).
- merchant: business name as printed.
- category: exactly one of Groceries, Dining, Transport, Shopping, Bills, Health, Other.
- description: up to 6 words summarizing the purchase.
- amount: the final total paid, including sales tax and tip. If a tip and total are handwritten, use the handwritten total. Never use the subtotal, amount tendered, change or a balance due line. Write exactly 2 decimals with no $ sign, spaces or thousands separators ($1,204.50 becomes 1204.50).
- currency: 3-letter ISO code. If no currency is shown, use DEFAULT_CURRENCY.
- payment_method: exactly one of Cash, Card, Digital Wallet, Unknown. Apple Pay and Google Pay are Digital Wallet; credit and debit cards are Card.
- confidence: high if every field is clearly readable; medium if one field was inferred or partly legible; low if date, merchant or amount is missing or doubtful, or if the image is not a receipt.
- notes: empty when confidence is high; otherwise a short reason.
- Text must not contain commas, double quotes or line breaks. Replace commas with a space or hyphen.
- Never guess an unreadable value. Leave it empty, set confidence to low and explain in notes.

EXAMPLE OUTPUT:
receipt_id,date,merchant,category,description,amount,currency,payment_method,confidence,notes
R001,2026-10-02,Trader Joe's,Groceries,Weekly groceries,54.37,USD,Card,high,
R002,2026-10-03,Shell,Transport,Gasoline,41.20,USD,Digital Wallet,medium,Payment method inferred
R003,,CVS Pharmacy,Health,Medicine,12.89,USD,Cash,low,Date faded

OUTPUT FORMAT:
Reply with only the CSV, including the header row, inside a single code block. No explanation before or after.
```
