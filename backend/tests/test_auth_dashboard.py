import base64
import os
import unittest
from pathlib import Path


TEST_DB = Path(__file__).resolve().parents[1] / "data" / "test_fnlifting.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-with-more-than-thirty-two-chars"

from fastapi.testclient import TestClient
from app.database.base import Base
from app.database.session import engine
from app.main import app
from seed import seed_database


class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        seed_database()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if TEST_DB.exists():
            TEST_DB.unlink()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        ready = self.client.get("/ready")
        self.assertEqual(ready.status_code, 200, ready.text)
        self.assertEqual(ready.json()["status"], "ready")

    def login_headers(self, identifier="admin@fnlifting.com", password="Admin@12345", portal="staff"):
        response = self.client.post("/api/v1/auth/login", json={
            "identifier": identifier, "password": password, "portal": portal,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_admin_login_and_dashboard(self):
        login = self.client.post("/api/v1/auth/login", json={
            "identifier": "admin@fnlifting.com",
            "password": "Admin@12345",
            "portal": "staff",
            "remember_me": False,
        })
        self.assertEqual(login.status_code, 200, login.text)
        payload = login.json()
        self.assertEqual(payload["user"]["roles"][0]["name"], "administrator")
        headers = {"Authorization": f"Bearer {payload['access_token']}"}
        dashboard = self.client.get("/api/v1/dashboard/overview", headers=headers)
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        self.assertEqual(dashboard.json()["scope"], "enterprise")
        self.assertEqual(len(dashboard.json()["metrics"]), 8)

    def test_portal_isolation_and_wrong_portal(self):
        wrong = self.client.post("/api/v1/auth/login", json={
            "identifier": "cliente@sonangol.co.ao",
            "password": "Cliente@12345",
            "portal": "staff",
        })
        self.assertEqual(wrong.status_code, 401)
        login = self.client.post("/api/v1/auth/login", json={
            "identifier": "cliente@sonangol.co.ao",
            "password": "Cliente@12345",
            "portal": "client",
        })
        self.assertEqual(login.status_code, 200, login.text)
        token = login.json()["access_token"]
        dashboard = self.client.get("/api/v1/dashboard/overview", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["scope"], "client")
        headers = {"Authorization": f"Bearer {token}"}
        equipment = self.client.get("/api/v1/operations/equipment", headers=headers)
        self.assertEqual(equipment.status_code, 200, equipment.text)
        self.assertEqual(len(equipment.json()), 2)
        self.assertTrue(all(item["client"]["name"] == "Sonangol EP" for item in equipment.json()))
        certificates = self.client.get("/api/v1/operations/certificates", headers=headers)
        self.assertEqual(certificates.status_code, 200, certificates.text)
        self.assertEqual(len(certificates.json()), 1)
        self.assertTrue(all(item["client"]["name"] == "Sonangol EP" for item in certificates.json()))
        self.assertEqual(self.client.get("/api/v1/operations/clients", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/v1/operations/inspections", headers=headers).status_code, 403)

    def test_operations_inspection_certificate_and_pdf(self):
        headers = self.login_headers()
        summary = self.client.get("/api/v1/operations/summary", headers=headers)
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(summary.json()["active_clients"], 5)
        self.assertEqual(summary.json()["equipment_total"], 10)
        signatories = self.client.get("/api/v1/operations/signatories", headers=headers)
        self.assertEqual(signatories.status_code, 200, signatories.text)
        self.assertEqual(len(signatories.json()), 2)
        self.assertTrue(all(item["signature_available"] and item["stamp_available"] for item in signatories.json()))

        client = self.client.post("/api/v1/operations/clients", headers=headers, json={
            "name": "Cliente Industrial QA", "nif": "5410099999",
            "email": "qa@cliente-industrial.co.ao", "phone": "+244 222 999 999",
            "address": "Luanda", "contact_person": "Gestor QA", "status": "active",
        })
        self.assertEqual(client.status_code, 201, client.text)
        client_id = client.json()["id"]
        types = self.client.get("/api/v1/operations/equipment-types", headers=headers)
        self.assertEqual(types.status_code, 200, types.text)
        equipment_type_id = types.json()[0]["id"]

        equipment = self.client.post("/api/v1/operations/equipment", headers=headers, json={
            "client_id": client_id, "equipment_type_id": equipment_type_id,
            "code": "EQP-QA-001", "name": "Equipamento de Teste QA",
            "manufacturer": "FNL Test", "model": "QA-100", "serial_number": "SERIAL-QA-001",
            "capacity": "10 t", "manufacture_year": 2025, "location": "Luanda", "status": "approved",
        })
        self.assertEqual(equipment.status_code, 201, equipment.text)
        equipment_id = equipment.json()["id"]

        inspection = self.client.post("/api/v1/operations/inspections", headers=headers, json={
            "equipment_id": equipment_id, "inspection_date": "2026-07-03",
            "next_inspection_date": "2027-07-03", "location": "Base QA",
            "conclusion": "Equipamento aprovado nos ensaios funcionais.", "status": "approved",
            "checklist_items": [
                {"item_code": "VIS", "item_label": "Inspeção visual", "expected_result": "Sem danos", "result": "pass"},
                {"item_code": "FUN", "item_label": "Teste funcional", "expected_result": "Normal", "result": "pass"},
            ],
        })
        self.assertEqual(inspection.status_code, 201, inspection.text)
        self.assertEqual(inspection.json()["inspection_no"], "INS-2026-0007")
        inspection_id = inspection.json()["id"]

        certificate = self.client.post("/api/v1/operations/certificates", headers=headers, json={
            "inspection_id": inspection_id,
            "document_type": "Certificate of Thorough Examination",
        })
        self.assertEqual(certificate.status_code, 201, certificate.text)
        self.assertEqual(certificate.json()["certificate_no"], "FNL-CTE-2026-006")
        certificate_id = certificate.json()["id"]
        draft_pdf = self.client.get(f"/api/v1/operations/certificates/{certificate_id}/pdf", headers=headers)
        self.assertEqual(draft_pdf.status_code, 200, draft_pdf.text)
        self.assertTrue(draft_pdf.content.startswith(b"%PDF"))
        revised_certificate = self.client.patch(f"/api/v1/operations/certificates/{certificate_id}", headers=headers, json={
            "colour_code": "Blue/Green",
            "safe_to_use": True,
        })
        self.assertEqual(revised_certificate.status_code, 200, revised_certificate.text)
        self.assertEqual(revised_certificate.json()["colour_code"], "Blue/Green")
        issued = self.client.post(f"/api/v1/operations/certificates/{certificate_id}/issue", headers=headers)
        self.assertEqual(issued.status_code, 200, issued.text)
        self.assertEqual(issued.json()["status"], "issued")
        self.assertTrue(issued.json()["pdf_available"])

        pdf = self.client.get(f"/api/v1/operations/certificates/{certificate_id}/pdf", headers=headers)
        self.assertEqual(pdf.status_code, 200, pdf.text)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertGreater(len(pdf.content), 5000)

        verification = self.client.get(f"/api/v1/public/certificates/{issued.json()['qr_token']}")
        self.assertEqual(verification.status_code, 200, verification.text)
        self.assertTrue(verification.json()["valid"])
        self.assertEqual(verification.json()["client_name"], "Cliente Industrial QA")

    def test_fleet_trip_and_gps_workflow(self):
        headers = self.login_headers()
        summary = self.client.get("/api/v1/fleet/summary", headers=headers)
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(summary.json()["drivers_total"], 5)
        self.assertEqual(summary.json()["trucks_total"], 5)
        self.assertEqual(summary.json()["trips_active"], 3)
        self.assertEqual(summary.json()["gps_online"], 3)

        driver = self.client.post("/api/v1/fleet/drivers", headers=headers, json={
            "driver_code": "DRV-QA-001", "full_name": "Motorista QA",
            "license_number": "AO-QA-001", "license_category": "D",
            "license_expires_at": "2030-12-31", "phone": "+244 900 000 001",
            "rating": 4.8, "status": "available",
        })
        self.assertEqual(driver.status_code, 201, driver.text)
        driver_id = driver.json()["id"]

        truck = self.client.post("/api/v1/fleet/trucks", headers=headers, json={
            "driver_id": driver_id, "plate": "LD-QA-01-AA", "brand": "Volvo",
            "model": "FH QA", "manufacture_year": 2026, "truck_type": "fuel_tanker",
            "tank_capacity_liters": 42000, "chassis_number": "CHASSIS-QA-001",
            "insurance_expires_at": "2030-01-01", "license_expires_at": "2030-01-01",
            "inspection_expires_at": "2030-01-01", "status": "available",
        })
        self.assertEqual(truck.status_code, 201, truck.text)
        truck_id = truck.json()["id"]

        client_id = self.client.get("/api/v1/operations/clients", headers=headers).json()[0]["id"]
        trip = self.client.post("/api/v1/fleet/trips", headers=headers, json={
            "truck_id": truck_id, "driver_id": driver_id, "client_id": client_id,
            "origin": "Luanda", "destination": "Benguela", "province": "Benguela",
            "city": "Lobito", "fuel_type": "Gasóleo", "quantity_liters": 30000,
            "status": "in_progress",
        })
        self.assertEqual(trip.status_code, 201, trip.text)
        trip_id = trip.json()["id"]

        position = self.client.post("/api/v1/fleet/gps/positions", headers=headers, json={
            "truck_id": truck_id, "trip_id": trip_id, "latitude": -9.2,
            "longitude": 13.7, "speed_kmh": 64, "heading": 145,
            "vehicle_state": "moving", "fuel_level_percent": 82,
        })
        self.assertEqual(position.status_code, 201, position.text)
        self.assertEqual(position.json()["truck"]["plate"], "LD-QA-01-AA")
        delivered = self.client.patch(f"/api/v1/fleet/trips/{trip_id}", headers=headers, json={"status": "delivered"})
        self.assertEqual(delivered.status_code, 200, delivered.text)
        self.assertEqual(delivered.json()["status"], "delivered")

    def test_phase5_management_finance_documents_and_audit(self):
        headers = self.login_headers()
        asset_summary = self.client.get("/api/v1/management/assets/summary", headers=headers)
        self.assertEqual(asset_summary.status_code, 200, asset_summary.text)
        self.assertEqual(asset_summary.json()["total_assets"], 5)
        employees = self.client.get("/api/v1/hr/employees", headers=headers).json()
        asset = self.client.post("/api/v1/management/assets", headers=headers, json={
            "asset_code": "PAT-QA-001", "name": "Ativo de Qualidade QA",
            "category": "Equipamentos de inspeção", "brand": "FNL Test",
            "model": "QA-500", "serial_number": "PAT-SERIAL-QA-001",
            "acquisition_date": "2026-07-05", "acquisition_value": 1500000,
            "current_value": 1450000, "depreciation_rate": 10,
            "location": "Laboratório QA", "responsible_id": employees[0]["id"],
            "status": "active",
        })
        self.assertEqual(asset.status_code, 201, asset.text)
        asset_id = asset.json()["id"]
        maintenance = self.client.post(f"/api/v1/management/assets/{asset_id}/maintenance", headers=headers, json={
            "maintenance_type": "preventive", "scheduled_date": "2026-08-01",
            "provider": "FNL QA", "cost": 75000, "description": "Calibração preventiva",
            "next_maintenance_date": "2027-08-01", "status": "scheduled",
        })
        self.assertEqual(maintenance.status_code, 201, maintenance.text)
        transfer = self.client.post(f"/api/v1/management/assets/{asset_id}/transfers", headers=headers, json={
            "to_responsible_id": employees[1]["id"], "to_location": "Base Operacional QA",
            "transfer_date": "2026-07-06", "reason": "Afetação ao inspetor QA",
        })
        self.assertEqual(transfer.status_code, 201, transfer.text)

        clients = self.client.get("/api/v1/operations/clients", headers=headers).json()
        invoice = self.client.post("/api/v1/management/finance/invoices", headers=headers, json={
            "client_id": clients[0]["id"], "issue_date": "2026-07-05", "due_date": "2026-08-05",
            "currency": "AOA", "notes": "Fatura de integração QA", "status": "issued",
            "items": [{"description": "Inspeção técnica QA", "quantity": 2, "unit_price": 250000, "tax_rate": 14}],
        })
        self.assertEqual(invoice.status_code, 201, invoice.text)
        self.assertEqual(float(invoice.json()["total_amount"]), 570000.0)
        invoice_id = invoice.json()["id"]
        invoice_pdf = self.client.get(f"/api/v1/management/finance/invoices/{invoice_id}/pdf", headers=headers)
        self.assertEqual(invoice_pdf.status_code, 200, invoice_pdf.text)
        self.assertTrue(invoice_pdf.content.startswith(b"%PDF"))
        payment = self.client.post(f"/api/v1/management/finance/invoices/{invoice_id}/payments", headers=headers, json={
            "payment_date": "2026-07-05", "amount": 570000, "method": "Transferência bancária",
            "reference": "PAY-QA-001", "notes": "Liquidação integral",
        })
        self.assertEqual(payment.status_code, 201, payment.text)
        self.assertEqual(payment.json()["invoice"]["status"], "paid")
        receipt_pdf = self.client.get(f"/api/v1/management/finance/receipts/{payment.json()['id']}/pdf", headers=headers)
        self.assertEqual(receipt_pdf.status_code, 200, receipt_pdf.text)
        self.assertTrue(receipt_pdf.content.startswith(b"%PDF"))

        payload = base64.b64encode(b"FNLIFTING phase 5 document QA").decode()
        document = self.client.post("/api/v1/management/documents", headers=headers, json={
            "title": "Documento QA Fase 5", "category": "Relatórios técnicos",
            "description": "Documento criado pelos testes", "valid_until": "2027-07-05",
            "approval_status": "pending", "file_name": "phase5-qa.txt",
            "file_data_url": f"data:text/plain;base64,{payload}", "change_notes": "Versão inicial QA",
        })
        self.assertEqual(document.status_code, 201, document.text)
        document_id = document.json()["id"]
        edited = self.client.patch(f"/api/v1/management/documents/{document_id}", headers=headers, json={
            "title": "Documento QA Fase 5 Revisto",
            "category": "Relatórios RH",
        })
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["approval_status"], "pending")
        rejected = self.client.post(f"/api/v1/management/documents/{document_id}/review", headers=headers, json={
            "action": "reject",
            "notes": "Rejeitado pelo teste para validar fluxo de revisão",
        })
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["approval_status"], "rejected")
        approved = self.client.post(f"/api/v1/management/documents/{document_id}/review", headers=headers, json={
            "action": "approve",
            "notes": "Aprovado após revisão",
        })
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["approval_status"], "approved")
        downloaded = self.client.get(f"/api/v1/management/documents/{document_id}/download", headers=headers)
        self.assertEqual(downloaded.status_code, 200, downloaded.text)
        self.assertEqual(downloaded.content, b"FNLIFTING phase 5 document QA")

        audit = self.client.get("/api/v1/management/audit/logs", headers=headers)
        self.assertEqual(audit.status_code, 200, audit.text)
        self.assertTrue(any(item["entity_type"] == "invoice" and item["action"] == "payment" for item in audit.json()))

    def test_phase6_backup_sync_portal_and_advanced_reports(self):
        headers = self.login_headers()

        report = self.client.get(
            "/api/v1/system/reports/advanced?report_type=executive&date_from=2025-01-01&date_to=2026-12-31",
            headers=headers,
        )
        self.assertEqual(report.status_code, 200, report.text)
        self.assertGreaterEqual(len(report.json()["metrics"]), 8)
        for file_format, signature in [("pdf", b"%PDF"), ("xlsx", b"PK"), ("csv", b"\xef\xbb\xbf")]:
            exported = self.client.get(
                f"/api/v1/system/reports/export?format={file_format}&report_type=executive&date_from=2025-01-01&date_to=2026-12-31",
                headers=headers,
            )
            self.assertEqual(exported.status_code, 200, exported.text)
            self.assertTrue(exported.content.startswith(signature))

        sync = self.client.get("/api/v1/system/sync/summary", headers=headers)
        self.assertEqual(sync.status_code, 200, sync.text)
        self.assertGreater(sync.json()["pending"], 0)
        synchronized = self.client.post("/api/v1/system/sync/run", headers=headers, json={"limit": 500})
        self.assertEqual(synchronized.status_code, 200, synchronized.text)
        self.assertGreater(synchronized.json()["pushed_count"], 0)

        backup = self.client.post("/api/v1/system/backups", headers=headers, json={
            "password": "BackupQA@2026", "include_files": False, "notes": "Backup do teste integrado",
        })
        self.assertEqual(backup.status_code, 201, backup.text)
        backup_id = backup.json()["id"]
        downloaded = self.client.get(f"/api/v1/system/backups/{backup_id}/download", headers=headers)
        self.assertEqual(downloaded.status_code, 200, downloaded.text)
        self.assertTrue(downloaded.content.startswith(b"FNLIFTING-BACKUP-V1"))
        verified = self.client.post(f"/api/v1/system/backups/{backup_id}/verify", headers=headers, json={
            "password": "BackupQA@2026", "confirm": False,
        })
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertTrue(verified.json()["valid"])

        settings = self.client.get("/api/v1/system/settings", headers=headers)
        self.assertEqual(settings.status_code, 200, settings.text)
        self.assertGreaterEqual(len(settings.json()), 8)
        readiness = self.client.get("/api/v1/system/ops/readiness", headers=headers)
        self.assertEqual(readiness.status_code, 200, readiness.text)
        self.assertIn(readiness.json()["status"], {"ready", "not_ready"})
        self.assertGreaterEqual(len(readiness.json()["checks"]), 8)
        interval = next(item for item in settings.json() if item["key"] == "sync.interval_minutes")
        updated = self.client.patch(f"/api/v1/system/settings/{interval['id']}", headers=headers, json={"value": "20"})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["value"], "20")

        portal_headers = self.login_headers("cliente@sonangol.co.ao", "Cliente@12345", "client")
        overview = self.client.get("/api/v1/portal/overview", headers=portal_headers)
        self.assertEqual(overview.status_code, 200, overview.text)
        self.assertEqual(overview.json()["client_name"], "Sonangol EP")
        self.assertEqual(overview.json()["equipment_total"], 2)
        billing = self.client.get("/api/v1/portal/billing", headers=portal_headers)
        self.assertEqual(billing.status_code, 200, billing.text)
        self.assertTrue(all(item["client"]["name"] == "Sonangol EP" for item in billing.json()["invoices"]))
        equipment = self.client.get("/api/v1/operations/equipment", headers=portal_headers).json()
        request = self.client.post("/api/v1/portal/requests", headers=portal_headers, json={
            "equipment_id": equipment[0]["id"], "service_type": "inspection",
            "preferred_date": "2026-08-20", "location": "Base Sonils, Luanda",
            "contact_name": "Ana Cassoma", "contact_phone": "+244 923 000 001",
            "priority": "high", "notes": "Inspeção periódica solicitada pelo portal QA.",
        })
        self.assertEqual(request.status_code, 201, request.text)
        self.assertEqual(request.json()["client"]["name"], "Sonangol EP")
        self.assertEqual(self.client.get("/api/v1/portal/overview", headers=headers).status_code, 403)

    def test_registration_requires_approval(self):
        response = self.client.post("/api/v1/auth/register", json={
            "full_name": "Novo Colaborador",
            "email": "novo@fnlifting.com",
            "username": "novo.colaborador",
            "password": "SenhaForte123",
            "requested_role": "technician",
            "account_type": "internal",
        })
        self.assertEqual(response.status_code, 201, response.text)
        login = self.client.post("/api/v1/auth/login", json={
            "identifier": "novo@fnlifting.com",
            "password": "SenhaForte123",
            "portal": "staff",
        })
        self.assertEqual(login.status_code, 403)

    def test_hr_crud_and_workflows(self):
        headers = self.login_headers()
        summary = self.client.get("/api/v1/hr/summary", headers=headers)
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(summary.json()["active_employees"], 10)
        self.assertEqual(summary.json()["departments"], 11)

        department = self.client.post("/api/v1/hr/departments", headers=headers, json={
            "code": "QAT", "name": "Qualidade e Testes", "description": "Departamento criado pelos testes",
            "manager_name": "Responsável QA", "status": "active",
        })
        self.assertEqual(department.status_code, 201, department.text)
        department_id = department.json()["id"]

        employee = self.client.post("/api/v1/hr/employees", headers=headers, json={
            "department_id": department_id,
            "employee_no": "FNL-TST-001",
            "full_name": "Trabalhador de Teste",
            "job_title": "Analista QA",
            "admission_date": "2026-07-01",
            "contract_type": "permanent",
            "contract_status": "active",
            "status": "active",
            "email": "qa.test@fnlifting.com",
        })
        self.assertEqual(employee.status_code, 201, employee.text)
        employee_id = employee.json()["id"]

        report = self.client.post("/api/v1/hr/daily-reports", headers=headers, json={
            "employee_id": employee_id,
            "department_id": department_id,
            "report_date": "2030-01-15",
            "summary": "Validação da Fase 2",
            "tasks_performed": "Testes de integração do fluxo de relatórios diários.",
            "start_time": "08:00:00",
            "end_time": "17:00:00",
            "work_status": "completed",
        })
        self.assertEqual(report.status_code, 201, report.text)
        report_id = report.json()["id"]
        approved = self.client.post(f"/api/v1/hr/daily-reports/{report_id}/review", headers=headers, json={
            "action": "approve", "notes": "Relatório validado pelo teste.",
        })
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "approved")

        performance = self.client.post("/api/v1/hr/performance", headers=headers, json={
            "employee_id": employee_id, "period": "2030-01", "punctuality": 4,
            "productivity": 4, "work_quality": 4, "task_completion": 4,
            "reports_score": 4, "supervisor_score": 4, "status": "published",
        })
        self.assertEqual(performance.status_code, 201, performance.text)
        self.assertEqual(float(performance.json()["overall_score"]), 80.0)

        archived = self.client.delete(f"/api/v1/hr/employees/{employee_id}", headers=headers)
        self.assertEqual(archived.status_code, 200, archived.text)
        removed_department = self.client.delete(f"/api/v1/hr/departments/{department_id}", headers=headers)
        self.assertEqual(removed_department.status_code, 200, removed_department.text)

    def test_technician_can_only_access_own_reports(self):
        headers = self.login_headers("tecnico@fnlifting.com", "Tecnico@12345")
        denied = self.client.get("/api/v1/hr/employees", headers=headers)
        self.assertEqual(denied.status_code, 403)
        own_employee = self.client.get("/api/v1/hr/employees/me", headers=headers)
        self.assertEqual(own_employee.status_code, 200, own_employee.text)
        employee_id = own_employee.json()["id"]
        reports = self.client.get("/api/v1/hr/daily-reports", headers=headers)
        self.assertEqual(reports.status_code, 200, reports.text)
        self.assertTrue(all(item["employee_id"] == employee_id for item in reports.json()))


if __name__ == "__main__":
    unittest.main()
