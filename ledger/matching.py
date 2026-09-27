from .storage import invoice_by_key


def find_invoice(db, payment):
    invoice = invoice_by_key(db, payment['customer_id'], payment['invoice_number'])
    return invoice['id'] if invoice else None
