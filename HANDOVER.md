# Handover

- Name: Visuvanathan K
- Email used for this application: vishwak2468@gmail.com
- Chosen track: Track A — Repair the register
- Why this track: It is a focused engineering task where correctness, data integrity and regression testing can be demonstrated directly.
- Approximate total time, including setup and handover: about 3.5 hours

## Run and verify

Prerequisite: Python 3.10+; no third-party dependencies.

```text
python -m unittest discover -s tests -v
python restore_fixture.py --replace
python app.py check
python app.py
```

Open `http://127.0.0.1:8787` in a browser. The `check` command is an added preflight integrity check; a clean register reports zero duplicate invoice identities, bad payment allocations and orphaned allocations.

## What I delivered

I repaired six seeded failure areas: invoice retry/idempotency, payment matching by amount instead of identity, row-level import validation, `open`/`paid` filtering, cent-accurate export, and browser handling of failed/partial import responses. Invoice identity is now enforced by `(customer_id, invoice_number)` and the existing register is preserved. I also added a small preflight integrity check (`python app.py check`) for the owner to run before a busy period.

Regression coverage is in `tests/test_repair.py`; the existing smoke tests remain unchanged.

## Evidence and limits

- Before repair, an identical invoice import created a second invoice; a payment for HARBOR/INV-100 could attach to MAPLE/INV-200 when the amounts matched; a mixed valid/invalid CSV raised before processing valid rows; `open` returned paid records; and exporting 19.99 - 10.00 produced 9.98 because of binary-float truncation.
- After repair: `13/13` tests pass.
- Changed-input case: a 150.00 payment against NORTH/INV-301 (100.00 invoice) produces a -50.00 balance and does not reduce another invoice's outstanding balance.
- Existing-register check: restored fixture reported 9 invoices, 5 payments, 7 open invoices and INR 3,698.19 outstanding; after importing a new invoice/payment, the records survived close/reopen with INR 3,768.19 outstanding.
- HTTP check: invalid headers return 400 with an error; mixed rows return actual imported/rejected counts and line numbers.

Known limit: the repair does not add concurrency handling because simultaneous writers are explicitly outside scope. In a production system I would next test concurrent imports and database locking/transaction behaviour.

## Tools and judgment

- AI code suggestions -> I kept only changes matching `BUSINESS_RULES.md` and verified them with targeted tests and HTTP checks.
- Decimal-based money handling was suggested -> I used it only at calculation/export boundaries and checked the 19.99/10.00 case.
- A database uniqueness constraint was considered -> I added a unique index after checking the supplied fixture for duplicate identities, then verified the restored register and restart path.
