from datetime import date, timedelta
from uuid import uuid4

from tests.enterprise_test_utils import client, first_client_id, first_department_id, first_employee_id, login_headers


def test_finance_expense_invoice_payment_receipt_and_pdfs():
    api = client()
    headers = login_headers(api)
    suffix = uuid4().hex[:8]

    expense = api.post(
        "/api/v1/management/finance/expenses",
        headers=headers,
        json={
            "department_id": first_department_id(),
            "responsible_id": first_employee_id(),
            "category": "Operação QA",
            "amount": "12000",
            "transaction_date": date.today().isoformat(),
            "description": f"Despesa QA {suffix}",
            "vendor": "Fornecedor QA",
            "status": "pending",
        },
    )
    assert expense.status_code == 201, expense.text
    approved = api.post(f"/api/v1/management/finance/expenses/{expense.json()['id']}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    invoice = api.post(
        "/api/v1/management/finance/invoices",
        headers=headers,
        json={
            "client_id": first_client_id(),
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "currency": "AOA",
            "status": "issued",
            "items": [{"description": "Inspeção QA", "quantity": "1", "unit_price": "50000", "tax_rate": "14"}],
        },
    )
    assert invoice.status_code == 201, invoice.text
    invoice_payload = invoice.json()
    assert invoice_payload["pdf_available"] is True

    invoice_pdf = api.get(f"/api/v1/management/finance/invoices/{invoice_payload['id']}/pdf", headers=headers)
    assert invoice_pdf.status_code == 200, invoice_pdf.text
    assert invoice_pdf.headers["content-type"].startswith("application/pdf")

    receipt = api.post(
        f"/api/v1/management/finance/invoices/{invoice_payload['id']}/payments",
        headers=headers,
        json={"payment_date": date.today().isoformat(), "amount": invoice_payload["total_amount"], "method": "transferência", "reference": f"QA-{suffix}"},
    )
    assert receipt.status_code == 201, receipt.text
    receipt_payload = receipt.json()
    assert receipt_payload["pdf_available"] is True

    receipt_pdf = api.get(f"/api/v1/management/finance/receipts/{receipt_payload['id']}/pdf", headers=headers)
    assert receipt_pdf.status_code == 200, receipt_pdf.text
    assert receipt_pdf.headers["content-type"].startswith("application/pdf")
    api.close()
