import tempfile
import unittest
from pathlib import Path
from ledger import storage, reporting, importing


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self.tmp.name) / 'demo.sqlite3')
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_invoice_retry_is_skipped_and_conflicting_identity_is_rejected(self):
        csv = 'customer_id,invoice_number,amount,due_date\nHARBOR,INV-100,1250.00,2026-09-01\n'
        self.assertEqual(importing.import_csv(self.db, csv, 'invoices')['skipped'], 1)
        conflict = 'customer_id,invoice_number,amount,due_date\nHARBOR,INV-100,1300.00,2026-09-01\n'
        result = importing.import_csv(self.db, conflict, 'invoices')
        self.assertEqual(result['rejected'], 1)
        self.assertEqual(len(reporting.invoices(self.db)), 6)

    def test_payment_matches_identity_not_amount(self):
        csv = 'payment_id,customer_id,invoice_number,amount\nP-X,HARBOR,INV-100,1250.00\n'
        self.assertEqual(importing.import_csv(self.db, csv, 'payments')['imported'], 1)
        rows = {r['invoice_number']: r for r in reporting.invoices(self.db)}
        self.assertEqual(rows['INV-100']['paid'], 1250.00)
        self.assertEqual(rows['INV-200']['paid'], 0)

    def test_bad_row_does_not_block_valid_rows(self):
        csv = ('customer_id,invoice_number,amount,due_date\n'
               'HARBOR,NEW-1,10.00,2026-09-20\n'
               'BAD,NEW-2,20.00,2026-09-20\n'
               'HARBOR,NEW-3,30.00,2026-09-20\n')
        result = importing.import_csv(self.db, csv, 'invoices')
        self.assertEqual((result['imported'], result['rejected']), (2, 1))
        self.assertEqual(result['errors'][0]['line'], 3)

    def test_status_filters_are_disjoint(self):
        self.assertEqual(len(reporting.invoices(self.db, 'open')), 5)
        self.assertEqual(len(reporting.invoices(self.db, 'paid')), 1)

    def test_export_preserves_cents(self):
        exported = reporting.export_csv(self.db)
        row = next(line for line in exported.splitlines() if ',INV-300,' in line)
        self.assertIn(',19.99,10.00,9.99,open', row)

    def test_unmatched_payment_stays_unmatched(self):
        csv = 'payment_id,customer_id,invoice_number,amount\nP-U,HARBOR,MISSING-9,25.00\n'
        self.assertEqual(importing.import_csv(self.db, csv, 'payments')['imported'], 1)
        unmatched = reporting.overview(self.db)['unmatched_payments']
        self.assertTrue(any(p['payment_id'] == 'P-U' for p in unmatched))

    def test_integrity_check_reports_clean_register(self):
        self.assertEqual(storage.integrity_report(self.db), {
            'duplicate_invoice_identities': 0,
            'bad_payment_allocations': 0,
            'orphaned_payment_allocations': 0,
        })

    def test_changed_input_case_overpayment_is_paid_without_offsetting_other_invoice(self):
        csv = 'payment_id,customer_id,invoice_number,amount\nP-O,NORTH,INV-301,150.00\n'
        self.assertEqual(importing.import_csv(self.db, csv, 'payments')['imported'], 1)
        rows = {r['invoice_number']: r for r in reporting.invoices(self.db)}
        self.assertEqual(rows['INV-301']['balance'], -50.00)
        self.assertEqual(reporting.overview(self.db)['summary']['outstanding'], 3109.99)


if __name__ == '__main__':
    unittest.main()
