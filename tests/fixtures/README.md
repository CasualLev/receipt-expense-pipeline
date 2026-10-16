# Test fixtures

`expenses_broken.csv` is a deliberately messy CSV used to test that the pipeline handles bad Stage 1 output. It uses Windows (CRLF) line endings on purpose. Each row tests one problem:

| Row | Problem | Expected result |
|-----|---------|-----------------|
| T001 | None (clean row) | Kept, no log entry |
| T002 (first) | Spaces around merchant and restaurant_type | Auto-cleaned, kept, warning |
| T003 | Date in `MM/DD/YYYY` instead of `YYYY-MM-DD` | Converted, kept, warning |
| T004 | `$` in total | Auto-cleaned, kept, warning |
| T005 | `Restaurant` and `Vietnamese` not in allowed lists | Mapped to `Other`, kept, warning |
| T006 | Subtotal + tax + tip doesn't equal total (missing discount) | Kept, warning |
| T007 | Total missing but confidence `high` | Excluded, error |
| T008 | Impossible date (February 30) | Excluded, error |
| T002 (second) | Duplicate receipt_id; `Apple Pay` instead of `Digital Wallet` | Excluded, error |
| T010 | Total is text, not a number | Excluded, error |
| T011 | Date empty (unreadable), confidence `low`, valid total | Kept, warning; left out of anything grouped by year |

Expected totals: 11 rows read, 7 kept, 4 excluded.
