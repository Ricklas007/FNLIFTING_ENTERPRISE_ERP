import argparse
import hashlib
import json
import secrets
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.config import UPLOAD_DIR
from app.core.security import hash_password
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import (
    Asset,
    AssetMaintenance,
    AssetTransfer,
    AuditLog,
    ClientServiceRequest,
    Certificate,
    Client,
    Company,
    DailyReport,
    Department,
    Document,
    DocumentVersion,
    Driver,
    Employee,
    Equipment,
    EquipmentType,
    Expense,
    FleetIncident,
    FuelRecord,
    GPSPosition,
    Inspection,
    InspectionChecklistItem,
    Invoice,
    InvoiceItem,
    Notification,
    Permission,
    PerformanceReview,
    Payment,
    Receipt,
    Revenue,
    Role,
    SyncQueue,
    SyncRun,
    SystemSetting,
    TechnicalSignatory,
    Trip,
    Truck,
    User,
)
from app.sync.backup import create_backup


PERMISSIONS = {
    "dashboard.view": ("Ver dashboard", "dashboard"),
    "users.manage": ("Gerir utilizadores", "users"),
    "users.approve": ("Aprovar utilizadores", "users"),
    "hr.view": ("Consultar RH", "hr"),
    "hr.manage": ("Gerir RH", "hr"),
    "departments.view": ("Consultar departamentos", "hr"),
    "departments.manage": ("Gerir departamentos", "hr"),
    "employees.view": ("Consultar trabalhadores", "hr"),
    "employees.manage": ("Gerir trabalhadores", "hr"),
    "daily_reports.view": ("Consultar relatórios diários", "hr"),
    "daily_reports.submit": ("Submeter relatórios diários", "hr"),
    "daily_reports.review": ("Rever relatórios diários", "hr"),
    "performance.view": ("Consultar desempenho", "hr"),
    "performance.manage": ("Gerir avaliações de desempenho", "hr"),
    "clients.view": ("Consultar clientes", "clients"),
    "clients.manage": ("Gerir clientes", "clients"),
    "equipment.view": ("Consultar equipamentos", "equipment"),
    "equipment.manage": ("Gerir equipamentos", "equipment"),
    "inspections.view": ("Consultar inspeções", "inspections"),
    "inspections.manage": ("Gerir inspeções", "inspections"),
    "certificates.view": ("Consultar certificados", "certificates"),
    "certificates.manage": ("Gerir certificados", "certificates"),
    "fleet.view": ("Consultar frota e viagens", "fleet"),
    "fleet.manage": ("Gerir frota e viagens", "fleet"),
    "assets.view": ("Consultar património", "assets"),
    "assets.manage": ("Gerir património", "assets"),
    "finance.view": ("Consultar finanças", "finance"),
    "finance.manage": ("Gerir finanças", "finance"),
    "documents.view": ("Consultar documentos", "documents"),
    "documents.manage": ("Gerir documentos", "documents"),
    "reports.view": ("Consultar relatórios", "reports"),
    "audit.view": ("Consultar auditoria", "audit"),
    "sync.manage": ("Gerir backup e sincronização", "sync"),
    "settings.manage": ("Gerir configurações", "settings"),
    "client_portal.view": ("Aceder ao portal do cliente", "client_portal"),
}

ROLE_PERMISSIONS = {
    "administrator": list(PERMISSIONS),
    "general_director": [code for code in PERMISSIONS if code.endswith(".view") or code in {"reports.view", "audit.view"}],
    "hr": ["dashboard.view", "hr.view", "hr.manage", "departments.view", "departments.manage", "employees.view", "employees.manage", "daily_reports.view", "daily_reports.submit", "daily_reports.review", "performance.view", "performance.manage", "users.manage", "users.approve", "reports.view", "documents.view"],
    "supervisor": ["dashboard.view", "hr.view", "departments.view", "employees.view", "daily_reports.view", "daily_reports.submit", "daily_reports.review", "performance.view", "performance.manage", "clients.view", "equipment.view", "equipment.manage", "inspections.view", "inspections.manage", "certificates.view", "certificates.manage", "reports.view"],
    "inspector": ["dashboard.view", "daily_reports.view", "daily_reports.submit", "clients.view", "equipment.view", "equipment.manage", "inspections.view", "inspections.manage", "certificates.view", "certificates.manage", "reports.view", "documents.view"],
    "technician": ["dashboard.view", "daily_reports.view", "daily_reports.submit", "equipment.view", "inspections.view", "reports.view", "documents.view"],
    "driver": ["dashboard.view", "daily_reports.view", "daily_reports.submit", "fleet.view", "reports.view", "documents.view"],
    "finance": ["dashboard.view", "finance.view", "finance.manage", "reports.view", "documents.view", "documents.manage"],
    "operations": ["dashboard.view", "hr.view", "employees.view", "daily_reports.view", "daily_reports.review", "performance.view", "clients.view", "clients.manage", "equipment.view", "equipment.manage", "inspections.view", "inspections.manage", "certificates.view", "fleet.view", "fleet.manage", "reports.view"],
    "logistics": ["dashboard.view", "fleet.view", "fleet.manage", "assets.view", "documents.view"],
    "client_external": ["dashboard.view", "client_portal.view", "equipment.view", "certificates.view", "documents.view"],
    "asset_manager": ["dashboard.view", "assets.view", "assets.manage", "documents.view", "documents.manage", "reports.view"],
    "security": ["dashboard.view", "fleet.view", "assets.view", "documents.view"],
    "auditor": ["dashboard.view", "audit.view", "reports.view", "documents.view", "finance.view"],
    "visitor": ["dashboard.view"],
}

ROLE_LABELS = {
    "administrator": "Administrador",
    "general_director": "Diretor Geral",
    "hr": "Recursos Humanos",
    "supervisor": "Supervisor",
    "inspector": "Inspetor",
    "technician": "Técnico",
    "driver": "Motorista",
    "finance": "Financeiro",
    "operations": "Operações",
    "logistics": "Logística",
    "client_external": "Cliente Externo",
    "asset_manager": "Gestor de Património",
    "security": "Segurança",
    "auditor": "Auditor",
    "visitor": "Visitante",
}


def seed_database(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.info["skip_sync_queue"] = True
    try:
        if db.scalar(select(Company).where(Company.company_type == "owner")):
            print("A base de dados já contém dados. Use --reset para recriar.")
            return

        fnlifting = Company(
            name="FNLIFTING ANGOLA",
            legal_name="FNLIFTING ANGOLA - Inspeção, Elevação e Transporte, Lda.",
            nif="5001234567",
            company_type="owner",
            status="active",
        )
        portal_companies = [
            Company(name="Sonangol EP", legal_name="Sociedade Nacional de Combustíveis de Angola", nif="5410000010", company_type="client"),
            Company(name="TotalEnergies Angola", nif="5410000029", company_type="client"),
            Company(name="Azule Energy", nif="5410000037", company_type="client"),
            Company(name="Sonils Lda", nif="5410000045", company_type="client"),
            Company(name="Angola LNG", nif="5410000053", company_type="client"),
        ]
        db.add_all([fnlifting, *portal_companies])
        db.flush()

        permission_objects = {
            code: Permission(code=code, name=name, module=module)
            for code, (name, module) in PERMISSIONS.items()
        }
        db.add_all(permission_objects.values())
        db.flush()
        roles: dict[str, Role] = {}
        for role_name, permission_codes in ROLE_PERMISSIONS.items():
            role = Role(
                name=role_name,
                display_name=ROLE_LABELS[role_name],
                description=f"Perfil de acesso: {ROLE_LABELS[role_name]}",
                permissions=[permission_objects[code] for code in permission_codes],
            )
            roles[role_name] = role
            db.add(role)
        db.flush()

        demo_users = [
            (fnlifting, "admin@fnlifting.com", "admin", "Administrador FNLIFTING", "Admin@12345", "administrator", "internal", True),
            (fnlifting, "rh@fnlifting.com", "rh", "Helena Joaquim", "RH@12345", "hr", "internal", False),
            (fnlifting, "inspetor@fnlifting.com", "inspetor", "Manuel Domingos", "Inspetor@12345", "inspector", "internal", False),
            (fnlifting, "motorista@fnlifting.com", "motorista", "José António", "Motorista@12345", "driver", "internal", False),
            (fnlifting, "tecnico@fnlifting.com", "tecnico", "Mateus Pedro", "Tecnico@12345", "technician", "internal", False),
            (portal_companies[0], "cliente@sonangol.co.ao", "cliente.sonangol", "Ana Cassoma", "Cliente@12345", "client_external", "external", False),
        ]
        users_by_email: dict[str, User] = {}
        for company, email, username, full_name, password, role_name, account_type, superuser in demo_users:
            account = User(
                company_id=company.id,
                email=email,
                username=username,
                full_name=full_name,
                password_hash=hash_password(password),
                status="active",
                account_type=account_type,
                requested_role=role_name,
                is_superuser=superuser,
                roles=[roles[role_name]],
            )
            users_by_email[email] = account
            db.add(account)
        db.add(User(
            company_id=fnlifting.id,
            email="candidato@fnlifting.com",
            username="candidato.demo",
            full_name="Candidato Demonstração",
            password_hash=hash_password("Candidato@12345"),
            status="pending",
            account_type="internal",
            requested_role="technician",
            is_superuser=False,
        ))

        clients = []
        for index, portal in enumerate(portal_companies, start=1):
            client = Client(
                company_id=fnlifting.id,
                portal_company_id=portal.id,
                name=portal.name,
                nif=portal.nif,
                email=f"operacoes@{portal.name.lower().replace(' ', '')}.co.ao",
                phone=f"+244 222 000 10{index}",
                address=f"Luanda, Angola · Zona Industrial {index}",
                contact_person=["Ana Cassoma", "Miguel Costa", "Rui Baptista", "Carla Neto", "Paulo André"][index - 1],
                service_notes="Cliente estratégico com contrato de inspeção e certificação.",
                status="active",
            )
            clients.append(client)
            db.add(client)
        db.flush()

        db.flush()

        department_specs = [
            ("ADM", "Administração", "Direção e serviços administrativos", "Administrador FNLIFTING"),
            ("RH", "Recursos Humanos", "Gestão de pessoas e cultura", "Helena Joaquim"),
            ("FIN", "Financeiro", "Tesouraria, faturação e controlo", "Paulo Miguel"),
            ("OPE", "Operações", "Coordenação das operações de campo", "António Manuel"),
            ("INS", "Inspeção", "Inspeção técnica e certificação", "Carla Domingos"),
            ("TRA", "Transporte", "Frota e transporte industrial", "Mateus Pedro"),
            ("LOG", "Logística", "Planeamento logístico e materiais", "Rosa Ambrósio"),
            ("MNT", "Manutenção", "Manutenção preventiva e corretiva", "João Francisco"),
            ("SEG", "Segurança", "HSE e segurança operacional", "Marta José"),
            ("COM", "Comercial", "Clientes, propostas e contratos", "Luzia Alberto"),
            ("TI", "Tecnologia da Informação", "Sistemas e infraestrutura digital", "David Simão"),
        ]
        departments: dict[str, Department] = {}
        for code, name, description, manager in department_specs:
            department = Department(
                company_id=fnlifting.id,
                code=code,
                name=name,
                description=description,
                manager_name=manager,
                status="active",
            )
            departments[code] = department
            db.add(department)
        db.flush()

        employee_specs = [
            ("Cândido Námbua", "OPE", "Supervisor Técnico", None),
            ("Bilombo Alexandre", "INS", "Inspetor de Equipamentos de Elevação", "inspetor@fnlifting.com"),
            ("José António", "TRA", "Motorista", "motorista@fnlifting.com"),
            ("Helena Joaquim", "RH", "Técnica de RH", "rh@fnlifting.com"),
            ("Paulo Miguel", "FIN", "Contabilista", None),
            ("Rosa Ambrósio", "LOG", "Coordenadora", None),
            ("Mateus Pedro", "MNT", "Técnico de Manutenção", "tecnico@fnlifting.com"),
            ("João Francisco", "MNT", "Mecânico", None),
            ("David Simão", "TI", "Administrador de Sistemas", None),
            ("Marta José", "SEG", "Técnica HSE", None),
        ]
        employees = []
        for index, (full_name, department_code, job_title, user_email) in enumerate(employee_specs, start=1):
            employee = Employee(
                company_id=fnlifting.id,
                department_id=departments[department_code].id,
                user_id=users_by_email[user_email].id if user_email else None,
                employee_no=f"FNL-{index:04d}",
                full_name=full_name,
                job_title=job_title,
                birth_date=date(1982 + index, (index % 12) + 1, min(index + 5, 28)),
                bi=f"00{index:07d}LA04{index % 9}",
                nif=f"500200{index:04d}",
                phone=f"+244 923 100 {index:03d}",
                email=f"{full_name.lower().replace(' ', '.').replace('ó', 'o').replace('ã', 'a').replace('é', 'e').replace('í', 'i')}@fnlifting.com",
                address=f"Luanda, Município de Talatona, Zona {index}",
                admission_date=date(2019 + (index % 6), (index % 12) + 1, 1),
                contract_type="permanent" if index < 8 else "temporary",
                salary=Decimal(420000 + index * 65000),
                contract_status="active",
                status="active",
            )
            employees.append(employee)
            db.add(employee)
        db.flush()

        pdf_asset_dir = Path(__file__).resolve().parent / "app" / "pdf" / "assets"
        approver_profile = TechnicalSignatory(
            company_id=fnlifting.id,
            employee_id=employees[0].id,
            inspector_code="AUTH-CN-001",
            qualifications="Supervisor técnico autorizado a autenticar relatórios e certificados de exame minucioso.",
            employer_name="FNLIFTING ANGOLA",
            employer_address="Centralidade do Sequele, Bloco 1, Rua 2, Edifício 18A, Aptº 002",
            signature_path=str(pdf_asset_dir / "candido-signature-stamp.png"),
            stamp_path=str(pdf_asset_dir / "candido-signature-stamp.png"),
            can_inspect=False,
            can_approve=True,
            status="active",
        )
        inspector_profile = TechnicalSignatory(
            company_id=fnlifting.id,
            employee_id=employees[1].id,
            inspector_code="PO",
            qualifications="Lifting Appliances & Accessories; Magnetic Particle Testing Level II; Penetrant Testing Level I.",
            employer_name="FNLIFTING ANGOLA",
            employer_address="Centralidade do Sequele, Bloco 1, Rua 2, Edifício 18A, Aptº 002",
            signature_path=str(pdf_asset_dir / "bilombo-signature-stamp.png"),
            stamp_path=str(pdf_asset_dir / "bilombo-signature-stamp.png"),
            can_inspect=True,
            can_approve=False,
            status="active",
        )
        db.add_all([approver_profile, inspector_profile])
        db.flush()

        equipment_type_specs = [
            ("CRN", "Guindaste móvel", 12), ("FLT", "Empilhador", 12),
            ("SHK", "Manilha", 6), ("SLG", "Cinta de elevação", 6),
            ("OHC", "Ponte rolante", 12),
        ]
        checklist_template = json.dumps([
            {"item_code": "VIS", "item_label": "Inspeção visual geral", "expected_result": "Sem danos visíveis", "result": "pass", "notes": None},
            {"item_code": "IDN", "item_label": "Identificação e marcação", "expected_result": "Legível e rastreável", "result": "pass", "notes": None},
            {"item_code": "FUN", "item_label": "Teste funcional", "expected_result": "Operação normal", "result": "pass", "notes": None},
            {"item_code": "SAF", "item_label": "Dispositivos de segurança", "expected_result": "Operacionais", "result": "pass", "notes": None},
        ], ensure_ascii=False)
        equipment_types: list[EquipmentType] = []
        for code, name, interval in equipment_type_specs:
            equipment_type = EquipmentType(
                company_id=fnlifting.id, code=code, name=name,
                inspection_interval_months=interval, checklist_template=checklist_template, status="active",
            )
            equipment_types.append(equipment_type)
            db.add(equipment_type)
        db.flush()
        equipment = []
        for index in range(10):
            item = Equipment(
                company_id=fnlifting.id,
                client_id=clients[index % 5].id,
                equipment_type_id=equipment_types[index % 5].id,
                code=f"EQP-2026-{index + 1:03d}",
                name=f"{equipment_types[index % 5].name} #{index + 1:02d}",
                manufacturer=["Liebherr", "Toyota", "Crosby", "Gunnebo", "Konecranes"][index % 5],
                model=f"MDL-{220 + index}",
                serial_number=f"SN-FNL-{2026001 + index}",
                capacity=["100 t", "5 t", "8.5 t", "10 t", "25 t"][index % 5],
                manufacture_year=2018 + (index % 7),
                location=["Luanda", "Soyo", "Lobito", "Cabinda", "Benguela"][index % 5],
                status="approved" if index != 8 else "with_defect",
            )
            equipment.append(item)
            db.add(item)
        db.flush()

        inspections = []
        for index, item in enumerate(equipment[:6]):
            inspection = Inspection(
                company_id=fnlifting.id,
                client_id=item.client_id,
                equipment_id=item.id,
                inspector_id=employees[1].id,
                inspection_no=f"INS-2026-{index + 1:04d}",
                inspection_date=date.today() if index < 4 else date.today() - timedelta(days=index),
                next_inspection_date=date.today() + timedelta(days=20 if index < 3 else 180 + index * 15),
                location=item.location,
                defects=None if index < 5 else "Desgaste superficial identificado.",
                recommendations="Manter o plano de manutenção preventiva e inspeção periódica.",
                conclusion="Equipamento examinado e considerado apto para operação dentro da capacidade nominal." if index < 5 else "Aguardar correção do defeito antes da operação.",
                status="approved" if index < 5 else "with_defect",
            )
            inspections.append(inspection)
            db.add(inspection)
            db.flush()
            for template in json.loads(checklist_template):
                db.add(InspectionChecklistItem(
                    company_id=fnlifting.id, inspection_id=inspection.id,
                    item_code=template["item_code"], item_label=template["item_label"],
                    expected_result=template["expected_result"],
                    result="pass" if index < 5 else ("fail" if template["item_code"] == "VIS" else "pass"),
                    notes=None if index < 5 else "Necessita correção e nova verificação.",
                ))

        for index, (item, inspection) in enumerate(zip(equipment[:5], inspections[:5], strict=True)):
            db.add(Certificate(
                company_id=fnlifting.id,
                client_id=item.client_id,
                equipment_id=item.id,
                inspection_id=inspection.id,
                certificate_no=f"FNL-CTE-2026-{index + 1:03d}",
                document_type="Certificate of Thorough Examination",
                issued_at=date.today() - timedelta(days=30 * (index + 1)),
                expires_at=inspection.next_inspection_date,
                revision=1,
                qr_token=f"demo-certificate-{index + 1}-{secrets.token_urlsafe(8)}",
                approver_signatory_id=approver_profile.id,
                service_order_no=f"SERVICE ORDER-{index + 1:03d}",
                report_no=f"FNL/{date.today():%m%y}-WBS-{index + 1:03d}",
                identification_no=item.serial_number or item.code,
                standard_reference="BS EN 1492-1:2000+A1:2008",
                colour_code="Blue/Black",
                reason_code="C",
                safe_to_use=True,
                status="issued",
            ))

        driver_specs = [
            ("José António", "AO-LIC-001", "D", "+244 923 300 001"),
            ("Mateus Kilamba", "AO-LIC-002", "D", "+244 923 300 002"),
            ("Pedro Manuel", "AO-LIC-003", "D", "+244 923 300 003"),
            ("Adriano Paulo", "AO-LIC-004", "CE", "+244 923 300 004"),
            ("Domingos Afonso", "AO-LIC-005", "D", "+244 923 300 005"),
        ]
        drivers = []
        for index, (name, license_no, category, phone) in enumerate(driver_specs):
            driver = Driver(
                company_id=fnlifting.id,
                employee_id=employees[2].id if index == 0 else None,
                driver_code=f"DRV-2026-{index + 1:03d}",
                full_name=name,
                license_number=license_no,
                license_category=category,
                license_expires_at=date.today() + timedelta(days=180 + index * 90),
                phone=phone,
                rating=round(4.2 + index * 0.15, 2),
                status="on_trip" if index < 3 else "available",
            )
            drivers.append(driver)
            db.add(driver)
        db.flush()

        trucks = []
        for index, plate in enumerate(["LD-45-67-AA", "LD-23-91-BB", "LD-78-02-CC", "LD-11-58-DD", "LD-90-34-EE"]):
            truck = Truck(
                company_id=fnlifting.id,
                driver_id=drivers[index].id,
                plate=plate,
                brand="Volvo",
                model=f"FH{420 + index * 20}",
                manufacture_year=2019 + index,
                truck_type="fuel_tanker",
                tank_capacity_liters=36000 + index * 2000,
                chassis_number=f"YV2RT40A{202600000 + index}",
                insurance_expires_at=date.today() + timedelta(days=95 + index * 30),
                license_expires_at=date.today() + timedelta(days=120 + index * 25),
                inspection_expires_at=date.today() + timedelta(days=65 + index * 20),
                status="in_route" if index < 3 else "available",
            )
            trucks.append(truck)
            db.add(truck)
        db.flush()
        routes = [("Luanda", "Benguela", "Benguela"), ("Luanda", "Soyo", "Zaire"), ("Lobito", "Huambo", "Huambo"), ("Luanda", "Cabinda", "Cabinda"), ("Luanda", "Malanje", "Malanje")]
        trips = []
        for index, (origin, destination, province) in enumerate(routes):
            trip = Trip(
                company_id=fnlifting.id,
                truck_id=trucks[index].id,
                driver_id=drivers[index].id,
                client_id=clients[index % len(clients)].id,
                trip_code=f"TRP-2026-{index + 1:03d}",
                origin=origin,
                destination=destination,
                province=province,
                city=destination,
                fuel_type="Gasóleo" if index % 2 == 0 else "Gasolina",
                quantity_liters=28000 + index * 1500,
                departure_at=datetime.now(timezone.utc) - timedelta(hours=4 - index) if index < 3 else datetime.now(timezone.utc) + timedelta(days=index),
                expected_arrival_at=datetime.now(timezone.utc) + timedelta(hours=5 + index),
                actual_arrival_at=datetime.now(timezone.utc) - timedelta(hours=2) if index == 4 else None,
                notes="Transporte de combustível com monitorização operacional.",
                status="in_progress" if index < 3 else ("planned" if index == 3 else "delivered"),
            )
            trips.append(trip)
            db.add(trip)
        db.flush()

        route_points = [
            [(-8.8383, 13.2344), (-9.38, 13.92), (-10.05, 14.25)],
            [(-8.8383, 13.2344), (-7.95, 12.95), (-6.75, 12.37)],
            [(-12.35, 13.55), (-12.55, 14.25), (-12.78, 15.73)],
        ]
        for trip_index, points in enumerate(route_points):
            for point_index, (latitude, longitude) in enumerate(points):
                db.add(GPSPosition(
                    company_id=fnlifting.id,
                    truck_id=trucks[trip_index].id,
                    trip_id=trips[trip_index].id,
                    latitude=latitude,
                    longitude=longitude,
                    speed_kmh=58 + trip_index * 6 + point_index,
                    heading=110 + trip_index * 35,
                    vehicle_state="moving",
                    fuel_level_percent=86 - point_index * 8,
                    recorded_at=datetime.now(timezone.utc) - timedelta(minutes=(2 - point_index) * 18),
                ))
        db.add(FuelRecord(
            company_id=fnlifting.id,
            trip_id=trips[0].id,
            driver_id=drivers[0].id,
            quantity_liters=420,
            amount=Decimal("168000.00"),
            location="Luanda",
            recorded_at=datetime.now(timezone.utc) - timedelta(hours=3),
        ))
        db.add(FleetIncident(
            company_id=fnlifting.id,
            trip_id=trips[1].id,
            driver_id=drivers[1].id,
            incident_type="delay",
            occurred_at=datetime.now(timezone.utc) - timedelta(hours=1),
            location="Estrada Nacional 100",
            description="Paragem prolongada por controlo rodoviário; operação retomada.",
            status="monitoring",
        ))

        for index, employee in enumerate(employees):
            db.add(DailyReport(
                company_id=fnlifting.id,
                employee_id=employee.id,
                department_id=employee.department_id,
                report_date=date.today() - timedelta(days=index % 3),
                summary=f"Resumo das atividades operacionais #{index + 1}",
                tasks_performed=f"Verificação de equipamentos, atualização de registos e reunião de segurança operacional #{index + 1}.",
                start_time=time(8, 0),
                end_time=time(17, 0),
                work_location="Base FNLIFTING - Luanda" if index % 2 else "Instalações do cliente",
                difficulties="Sem dificuldades relevantes." if index % 3 else "Atraso na disponibilização do equipamento pelo cliente.",
                results_achieved="Atividades concluídas conforme o plano diário.",
                observations="Cumpridos os procedimentos HSE.",
                work_status="completed",
                status="pending" if index < 4 else "approved",
            ))

        score_sets = [
            (4.8, 4.9, 4.7, 4.8, 5.0, 4.9), (4.6, 4.7, 4.8, 4.5, 4.7, 4.8),
            (4.3, 4.5, 4.4, 4.6, 4.2, 4.5), (4.9, 4.6, 4.8, 4.7, 4.9, 4.8),
            (4.2, 4.4, 4.3, 4.1, 4.5, 4.3), (4.7, 4.8, 4.6, 4.7, 4.6, 4.8),
            (4.1, 4.3, 4.5, 4.2, 4.0, 4.4), (4.5, 4.6, 4.7, 4.5, 4.4, 4.7),
            (4.8, 4.7, 4.9, 4.8, 4.6, 4.9), (4.4, 4.5, 4.6, 4.3, 4.5, 4.6),
        ]
        for employee, raw_scores in zip(employees, score_sets, strict=True):
            scores = [Decimal(str(score)) for score in raw_scores]
            overall = (sum(scores) / Decimal(6) * Decimal(20)).quantize(Decimal("0.01"))
            db.add(PerformanceReview(
                company_id=fnlifting.id,
                employee_id=employee.id,
                period=date.today().strftime("%Y-%m"),
                punctuality=scores[0],
                productivity=scores[1],
                work_quality=scores[2],
                task_completion=scores[3],
                reports_score=scores[4],
                supervisor_score=scores[5],
                overall_score=overall,
                supervisor_notes="Bom desempenho e compromisso com os objetivos da equipa.",
                status="published",
            ))

        categories = ["Combustível", "Manutenção", "Logística", "Material", "Comunicações"]
        for index in range(10):
            db.add(Expense(
                company_id=fnlifting.id,
                department_id=employees[index % len(employees)].department_id,
                responsible_id=employees[index % len(employees)].id,
                category=categories[index % 5],
                amount=Decimal(180000 + index * 27500),
                transaction_date=date.today() - timedelta(days=index * 7),
                description=f"Despesa operacional DEMO #{index + 1}",
                vendor=["Sonangol", "Auto Peças Luanda", "Unitel", "Casa dos Equipamentos", "Logística Sul"][index % 5],
                due_date=date.today() + timedelta(days=5 + index),
                payment_method="Transferência" if index >= 6 else None,
                approved_by=users_by_email["admin@fnlifting.com"].id if index >= 6 else None,
                approved_at=datetime.now(timezone.utc) if index >= 6 else None,
                status="pending" if index < 6 else "approved",
            ))
            db.add(Revenue(
                company_id=fnlifting.id,
                client_id=clients[index % 5].id,
                amount=Decimal(520000 + index * 85000),
                transaction_date=date.today() - timedelta(days=index * 6),
                description=f"Serviço de inspeção DEMO #{index + 1}",
                service="Inspeção e certificação técnica",
                payment_method="Transferência bancária",
                reference=f"TRX-DEMO-{index + 1:04d}",
                paid_at=datetime.now(timezone.utc) - timedelta(days=index * 6),
                status="paid",
            ))

        invoices = []
        for index, client in enumerate(clients):
            subtotal = Decimal(750000 + index * 125000)
            tax = (subtotal * Decimal("0.14")).quantize(Decimal("0.01"))
            invoice = Invoice(
                company_id=fnlifting.id, client_id=client.id,
                invoice_no=f"FNL-FT-2026-{index + 1:04d}",
                issue_date=date.today() - timedelta(days=25 - index * 3),
                due_date=date.today() + timedelta(days=5 + index * 7),
                currency="AOA", subtotal=subtotal, tax_amount=tax, total_amount=subtotal + tax,
                notes="Serviços técnicos prestados conforme ordem de serviço.",
                status="paid" if index < 2 else ("partial" if index == 2 else "issued"),
            )
            db.add(invoice); db.flush(); invoices.append(invoice)
            db.add(InvoiceItem(
                company_id=fnlifting.id, invoice_id=invoice.id,
                description="Inspeção e certificação de equipamentos de elevação",
                quantity=Decimal(1), unit_price=subtotal, tax_rate=Decimal(14), line_total=subtotal,
            ))
            if index < 3:
                payment_amount = invoice.total_amount if index < 2 else (invoice.total_amount / Decimal(2)).quantize(Decimal("0.01"))
                payment = Payment(
                    company_id=fnlifting.id, invoice_id=invoice.id,
                    payment_date=date.today() - timedelta(days=10 - index), amount=payment_amount,
                    method="Transferência bancária", reference=f"PAY-DEMO-{index + 1:03d}", status="confirmed",
                )
                db.add(payment); db.flush()
                db.add(Receipt(
                    company_id=fnlifting.id, client_id=client.id, invoice_id=invoice.id, payment_id=payment.id,
                    receipt_no=f"FNL-RC-2026-{index + 1:04d}", issued_at=payment.payment_date,
                    amount=payment.amount, status="issued",
                ))

        asset_data = [
            ("PAT-001", "Servidor local Dell PowerEdge", "TI", 4_800_000),
            ("PAT-002", "Kit ultrassom industrial", "Inspeção", 7_250_000),
            ("PAT-003", "Gerador Caterpillar", "Geradores", 5_900_000),
            ("PAT-004", "Estação total Leica", "Inspeção", 3_650_000),
            ("PAT-005", "Viatura de apoio Toyota Hilux", "Viaturas", 28_500_000),
        ]
        assets = []
        for index, (code, name, category, value) in enumerate(asset_data):
            asset = Asset(
                company_id=fnlifting.id, asset_code=code, name=name, category=category,
                description=f"Bem patrimonial operacional: {name}.", brand=["Dell", "Olympus", "Caterpillar", "Leica", "Toyota"][index],
                model=f"MODEL-{index + 1:03d}", serial_number=f"SER-PAT-{index + 1:04d}",
                acquisition_date=date(2021 + index % 4, index + 1, 10), acquisition_value=Decimal(value),
                current_value=(Decimal(value) * Decimal("0.78")).quantize(Decimal("0.01")), depreciation_rate=Decimal("10.00"),
                location=["Datacenter", "Laboratório", "Base Luanda", "Inspeção", "Garagem"][index],
                responsible_id=employees[index].id, notes="Inventário físico confirmado.",
                status="maintenance" if index == 2 else "active",
            )
            assets.append(asset); db.add(asset)
        db.flush()
        for index, asset in enumerate(assets):
            db.add(AssetMaintenance(
                company_id=fnlifting.id, asset_id=asset.id,
                maintenance_type="preventive" if index != 2 else "corrective",
                scheduled_date=date.today() + timedelta(days=10 + index * 20),
                completed_date=None, provider="FNLIFTING Manutenção",
                cost=Decimal(95000 + index * 35000), description="Manutenção programada do ativo.",
                next_maintenance_date=date.today() + timedelta(days=190 + index * 20), status="in_progress" if index == 2 else "scheduled",
            ))
        db.add(AssetTransfer(
            company_id=fnlifting.id, asset_id=assets[1].id,
            from_responsible_id=employees[0].id, to_responsible_id=employees[1].id,
            from_location="Armazém", to_location="Laboratório", transfer_date=date.today() - timedelta(days=15),
            reason="Afetação ao departamento de inspeção.",
        ))

        document_dir = UPLOAD_DIR / "documents" / "seed"
        document_dir.mkdir(parents=True, exist_ok=True)
        for index, (title, category) in enumerate([
            ("Manual de Segurança Operacional", "HSE"),
            ("Contrato de Prestação de Serviços", "Contratos"),
            ("Licença de Operação", "Licenças"),
        ]):
            document = Document(
                company_id=fnlifting.id, client_id=clients[index].id if index < 2 else None,
                document_no=f"DOC-2026-{index + 1:05d}", title=title, category=category,
                description=f"Documento de demonstração: {title}.", current_version=1,
                valid_until=date.today() + timedelta(days=120 + index * 90),
                approval_status="approved" if index < 2 else "pending",
                approved_by=users_by_email["admin@fnlifting.com"].id if index < 2 else None,
                approved_at=datetime.now(timezone.utc) if index < 2 else None, status="active",
            )
            db.add(document); db.flush()
            content=f"FNLIFTING ANGOLA\n{title}\nDocumento de demonstração gerado pelo Enterprise ERP.\n".encode("utf-8")
            file_path=document_dir / f"document-{index + 1}.txt"; file_path.write_bytes(content)
            db.add(DocumentVersion(
                company_id=fnlifting.id, document_id=document.id, version_no=1,
                file_name=f"{title}.txt", file_path=str(file_path), mime_type="text/plain",
                file_size=len(content), checksum_sha256=hashlib.sha256(content).hexdigest(),
                change_notes="Versão inicial", uploaded_by=users_by_email["admin@fnlifting.com"].id,
            ))

        for index in range(10):
            db.add(AuditLog(
                company_id=fnlifting.id, user_id=users_by_email["admin@fnlifting.com"].id,
                action=["create", "update", "approve", "payment", "transfer"][index % 5],
                entity_type=["asset", "invoice", "document", "expense", "employee"][index % 5],
                entity_id=assets[index % len(assets)].id, entity_label=f"DEMO-{index + 1:03d}",
                after_data=json.dumps({"demo": True, "sequence": index + 1}),
                ip_address="127.0.0.1", machine_name="FNL-DEMO", description="Evento de auditoria de demonstração.",
            ))

        service_requests = []
        for index, request_status in enumerate(["submitted", "reviewing", "scheduled", "completed"]):
            service_request = ClientServiceRequest(
                company_id=fnlifting.id,
                client_id=clients[index % len(clients)].id,
                equipment_id=equipment[index].id,
                request_no=f"FNL-SRV-2026-{index + 1:04d}",
                service_type="inspection" if index != 3 else "certification",
                requested_date=date.today() - timedelta(days=index * 3),
                preferred_date=date.today() + timedelta(days=7 + index * 5),
                location=equipment[index].location or "Luanda",
                contact_name=clients[index].contact_person or "Responsável operacional",
                contact_phone=clients[index].phone,
                priority=["high", "normal", "urgent", "normal"][index],
                notes="Solicitação de demonstração submetida pelo portal externo.",
                status=request_status,
                response_notes="Agendamento confirmado pela equipa técnica." if request_status in {"scheduled", "completed"} else None,
                handled_by=users_by_email["admin@fnlifting.com"].id if request_status != "submitted" else None,
                handled_at=datetime.now(timezone.utc) if request_status != "submitted" else None,
                created_by=users_by_email["cliente@sonangol.co.ao"].id if index == 0 else users_by_email["admin@fnlifting.com"].id,
            )
            db.add(service_request)
            service_requests.append(service_request)
        db.flush()

        sync_entries = [
            ("assets", assets[0].id, "update", "pending", None),
            ("client_service_requests", service_requests[0].id, "create", "pending", None),
            ("invoices", invoices[3].id, "update", "pending", None),
            ("client_service_requests", service_requests[0].id, "create", "pending", None),
            ("assets", assets[1].id, "update", "synced", None),
            ("invoices", invoices[0].id, "update", "synced", None),
            ("client_service_requests", service_requests[1].id, "update", "conflict", json.dumps({"status": "scheduled"})),
            ("assets", assets[2].id, "update", "failed", None),
        ]
        for index, (entity_type, entity_id, operation, sync_state, conflict_payload) in enumerate(sync_entries):
            db.add(SyncQueue(
                company_id=fnlifting.id, entity_type=entity_type, entity_id=entity_id,
                operation=operation, payload=json.dumps({"demo": True, "sequence": index + 1}),
                status=sync_state, retry_count=1 if sync_state == "failed" else 0,
                error_message="Endpoint remoto temporariamente indisponível" if sync_state == "failed" else None,
                conflict_payload=conflict_payload,
                queued_at=datetime.now(timezone.utc) - timedelta(minutes=45 - index * 4),
                processed_at=datetime.now(timezone.utc) - timedelta(minutes=20) if sync_state == "synced" else None,
                created_by=users_by_email["admin@fnlifting.com"].id,
            ))
        db.add(SyncRun(
            company_id=fnlifting.id, direction="bidirectional", mode="local_checkpoint",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            completed_at=datetime.now(timezone.utc) - timedelta(hours=2, minutes=-1),
            pushed_count=2, pulled_count=0, conflict_count=1, failed_count=1,
            status="partial", message="Checkpoint local de demonstração concluído.",
            created_by=users_by_email["admin@fnlifting.com"].id,
        ))

        settings_data = [
            ("company.display_name", "Nome empresarial", "FNLIFTING ANGOLA", "string", "general", False, "Nome apresentado nos documentos e relatórios."),
            ("company.default_currency", "Moeda padrão", "AOA", "string", "finance", False, "Moeda usada nos lançamentos financeiros."),
            ("backup.auto_enabled", "Backup automático", "true", "boolean", "backup", False, "Ativa a política de backup automático."),
            ("backup.retention_days", "Retenção dos backups", "30", "integer", "backup", False, "Número de dias de retenção local."),
            ("sync.auto_enabled", "Sincronização automática", "true", "boolean", "sync", False, "Processa a fila quando existir ligação configurada."),
            ("sync.interval_minutes", "Intervalo de sincronização", "15", "integer", "sync", False, "Intervalo mínimo entre sincronizações automáticas."),
            ("reports.monthly_enabled", "Relatório mensal automático", "true", "boolean", "reports", False, "Prepara o resumo executivo no fecho mensal."),
            ("security.session_minutes", "Duração da sessão", "60", "integer", "security", False, "Duração padrão da sessão de acesso."),
        ]
        for key, label, value, value_type, category, is_secret, description in settings_data:
            db.add(SystemSetting(
                company_id=fnlifting.id, key=key, label=label, value=value,
                value_type=value_type, category=category, is_secret=is_secret,
                description=description, created_by=users_by_email["admin@fnlifting.com"].id,
            ))

        db.add_all([
            Notification(company_id=fnlifting.id, title="Certificados a vencer", message="3 certificados vencem nos próximos 30 dias.", level="warning"),
            Notification(company_id=fnlifting.id, title="GPS sem sinal", message="O camião LD-45-67-AA está sem sinal há 38 minutos.", level="critical"),
            Notification(company_id=fnlifting.id, title="Relatórios recebidos", message="4 relatórios diários aguardam validação.", level="info"),
        ])
        db.commit()
        demo_backup = create_backup(
            db, fnlifting.id, users_by_email["admin@fnlifting.com"].id,
            "DemoBackup@2026", True, "Backup inicial cifrado criado pelos dados de demonstração.",
        )
        db.add(demo_backup)
        db.commit()
        print("Seed concluído: FNLIFTING, RBAC, 7 utilizadores e dados de demonstração criados.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializa dados de demonstração do FNLIFTING ERP")
    parser.add_argument("--reset", action="store_true", help="Apaga e recria toda a base local")
    args = parser.parse_args()
    seed_database(reset=args.reset)
