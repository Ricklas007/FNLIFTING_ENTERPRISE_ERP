import base64
import hashlib
import binascii
import json
import secrets
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.core.config import BACKEND_DIR
from app.database.session import get_db
from app.models import (
    Certificate, Client, Employee, Equipment, EquipmentType, Inspection,
    InspectionChecklistItem, TechnicalSignatory, User,
)
from app.pdf.certificate import generate_certificate_pdf
from app.schemas.auth import MessageResponse
from app.schemas.operations import (
    CertificateCreate, CertificateOut, CertificateUpdate, ClientCreate, ClientOut, ClientUpdate,
    EquipmentCreate, EquipmentOut, EquipmentTypeOut, EquipmentUpdate,
    InspectionCreate, InspectionOut, InspectionUpdate, OperationsSummary,
    PublicCertificateOut, TechnicalSignatoryCreate, TechnicalSignatoryOut,
    TechnicalSignatoryUpdate,
)


router = APIRouter(prefix="/operations", tags=["Operações e Inspeções"])
public_router = APIRouter(prefix="/public", tags=["Validação pública"])


SIGNATURE_DIR = BACKEND_DIR / "data" / "signatures"
SIGNATURE_DIR.mkdir(parents=True, exist_ok=True)


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


def portal_client_id(db: Session, user: User) -> str | None:
    if user.account_type != "external":
        return None
    return db.scalar(select(Client.id).where(
        Client.portal_company_id == user.company_id,
        Client.deleted_at.is_(None),
    ))


def client_out(db: Session, client: Client) -> ClientOut:
    result = ClientOut.model_validate(client)
    result.equipment_count = db.scalar(select(func.count(Equipment.id)).where(
        Equipment.client_id == client.id, Equipment.deleted_at.is_(None)
    )) or 0
    result.certificate_count = db.scalar(select(func.count(Certificate.id)).where(
        Certificate.client_id == client.id, Certificate.deleted_at.is_(None), Certificate.status == "issued"
    )) or 0
    return result


def get_client(db: Session, client_id: str, company_id: str) -> Client:
    record = db.scalar(select(Client).where(
        Client.id == client_id, Client.company_id == company_id, Client.deleted_at.is_(None)
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return record


def equipment_query():
    return select(Equipment).options(
        selectinload(Equipment.client), selectinload(Equipment.type)
    )


def get_equipment(db: Session, equipment_id: str, company_id: str) -> Equipment:
    item = db.scalar(equipment_query().where(
        Equipment.id == equipment_id, Equipment.company_id == company_id, Equipment.deleted_at.is_(None)
    ))
    if not item:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado")
    return item


def inspection_query():
    return select(Inspection).options(
        selectinload(Inspection.client),
        selectinload(Inspection.equipment).selectinload(Equipment.client),
        selectinload(Inspection.equipment).selectinload(Equipment.type),
        selectinload(Inspection.inspector),
        selectinload(Inspection.checklist_items),
    )


def get_inspection(db: Session, inspection_id: str, company_id: str) -> Inspection:
    record = db.scalar(inspection_query().where(
        Inspection.id == inspection_id, Inspection.company_id == company_id, Inspection.deleted_at.is_(None)
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Inspeção não encontrada")
    return record


def certificate_query():
    return select(Certificate).options(
        selectinload(Certificate.client),
        selectinload(Certificate.equipment).selectinload(Equipment.client),
        selectinload(Certificate.equipment).selectinload(Equipment.type),
        selectinload(Certificate.inspection).selectinload(Inspection.client),
        selectinload(Certificate.inspection).selectinload(Inspection.inspector).selectinload(Employee.technical_signatory),
        selectinload(Certificate.inspection).selectinload(Inspection.checklist_items),
        selectinload(Certificate.inspection).selectinload(Inspection.equipment).selectinload(Equipment.client),
        selectinload(Certificate.inspection).selectinload(Inspection.equipment).selectinload(Equipment.type),
        selectinload(Certificate.approver_signatory).selectinload(TechnicalSignatory.employee),
    )


def get_certificate(db: Session, certificate_id: str) -> Certificate:
    record = db.scalar(certificate_query().where(
        Certificate.id == certificate_id, Certificate.deleted_at.is_(None)
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    return record


def certificate_out(certificate: Certificate) -> CertificateOut:
    result = CertificateOut.model_validate(certificate)
    result.pdf_available = bool(certificate.pdf_path and Path(certificate.pdf_path).exists())
    return result


def signatory_out(record: TechnicalSignatory) -> TechnicalSignatoryOut:
    result = TechnicalSignatoryOut.model_validate(record)
    result.signature_available = bool(record.signature_path and Path(record.signature_path).exists())
    result.stamp_available = bool(record.stamp_path and Path(record.stamp_path).exists())
    return result


def save_signatory_asset(data_url: str, record_id: str, kind: str) -> str:
    try:
        header, encoded = data_url.split(",", 1)
        mime = header.split(";")[0].removeprefix("data:")
        extension = {"image/png": "png", "image/jpeg": "jpg"}[mime]
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, KeyError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail=f"Imagem de {kind} invÃ¡lida; utilize PNG ou JPEG") from exc
    if len(content) > 2_500_000:
        raise HTTPException(status_code=422, detail=f"A imagem de {kind} excede 2,5 MB")
    path = SIGNATURE_DIR / f"{record_id}-{kind}.{extension}"
    path.write_bytes(content)
    return str(path)


def get_signatory(db: Session, signatory_id: str, company_id: str) -> TechnicalSignatory:
    record = db.scalar(select(TechnicalSignatory).options(selectinload(TechnicalSignatory.employee)).where(
        TechnicalSignatory.id == signatory_id,
        TechnicalSignatory.company_id == company_id,
        TechnicalSignatory.deleted_at.is_(None),
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Inspetor autorizado nÃ£o encontrado")
    return record


@router.get("/summary", response_model=OperationsSummary)
def operations_summary(
    user: User = Depends(require_permission("clients.view")),
    db: Session = Depends(get_db),
):
    company_id = user.company_id
    today = date.today()
    expiring_limit = today + timedelta(days=45)
    statuses = db.execute(
        select(Equipment.status, func.count(Equipment.id))
        .where(Equipment.company_id == company_id, Equipment.deleted_at.is_(None))
        .group_by(Equipment.status)
    ).all()
    return OperationsSummary(
        active_clients=db.scalar(select(func.count(Client.id)).where(Client.company_id == company_id, Client.status == "active", Client.deleted_at.is_(None))) or 0,
        equipment_total=db.scalar(select(func.count(Equipment.id)).where(Equipment.company_id == company_id, Equipment.deleted_at.is_(None))) or 0,
        inspections_pending=db.scalar(select(func.count(Inspection.id)).where(Inspection.company_id == company_id, Inspection.status == "pending", Inspection.deleted_at.is_(None))) or 0,
        inspections_approved=db.scalar(select(func.count(Inspection.id)).where(Inspection.company_id == company_id, Inspection.status == "approved", Inspection.deleted_at.is_(None))) or 0,
        certificates_issued=db.scalar(select(func.count(Certificate.id)).where(Certificate.company_id == company_id, Certificate.status == "issued", Certificate.deleted_at.is_(None))) or 0,
        certificates_expiring=db.scalar(select(func.count(Certificate.id)).where(Certificate.company_id == company_id, Certificate.status == "issued", Certificate.expires_at.between(today, expiring_limit), Certificate.deleted_at.is_(None))) or 0,
        equipment_by_status=[{"name": name, "value": value} for name, value in statuses],
    )


@router.get("/clients", response_model=list[ClientOut])
def list_clients(
    search: str | None = Query(default=None, max_length=100),
    user: User = Depends(require_permission("clients.view")),
    db: Session = Depends(get_db),
):
    query = select(Client).where(Client.company_id == user.company_id, Client.deleted_at.is_(None))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Client.name.ilike(term), Client.nif.ilike(term), Client.contact_person.ilike(term)))
    records = db.scalars(query.order_by(Client.name)).all()
    return [client_out(db, record) for record in records]


@router.post("/clients", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    user: User = Depends(require_permission("clients.manage")),
    db: Session = Depends(get_db),
):
    record = Client(company_id=user.company_id, created_by=user.id, **payload.model_dump())
    db.add(record)
    commit_or_conflict(db, "Já existe um cliente com este NIF")
    db.refresh(record)
    return client_out(db, record)


@router.patch("/clients/{client_id}", response_model=ClientOut)
def update_client(
    client_id: str,
    payload: ClientUpdate,
    user: User = Depends(require_permission("clients.manage")),
    db: Session = Depends(get_db),
):
    record = get_client(db, client_id, user.company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_by = user.id
    commit_or_conflict(db, "Já existe um cliente com este NIF")
    return client_out(db, record)


@router.delete("/clients/{client_id}", response_model=MessageResponse)
def delete_client(
    client_id: str,
    user: User = Depends(require_permission("clients.manage")),
    db: Session = Depends(get_db),
):
    record = get_client(db, client_id, user.company_id)
    linked = db.scalar(select(func.count(Equipment.id)).where(Equipment.client_id == record.id, Equipment.deleted_at.is_(None))) or 0
    if linked:
        raise HTTPException(status_code=409, detail="O cliente possui equipamentos ativos e não pode ser eliminado")
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = user.id
    db.commit()
    return MessageResponse(message="Cliente arquivado")


@router.get("/equipment-types", response_model=list[EquipmentTypeOut])
def list_equipment_types(
    user: User = Depends(require_permission("equipment.view")),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(EquipmentType).where(
        EquipmentType.company_id == user.company_id, EquipmentType.status == "active", EquipmentType.deleted_at.is_(None)
    ).order_by(EquipmentType.name)).all())


@router.get("/equipment", response_model=list[EquipmentOut])
def list_equipment(
    search: str | None = Query(default=None, max_length=100),
    client_id: str | None = None,
    equipment_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(require_permission("equipment.view")),
    db: Session = Depends(get_db),
):
    query = equipment_query().where(Equipment.deleted_at.is_(None))
    scope = portal_client_id(db, user)
    if user.account_type == "external":
        if not scope:
            return []
        query = query.where(Equipment.client_id == scope)
    else:
        query = query.where(Equipment.company_id == user.company_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Equipment.name.ilike(term), Equipment.code.ilike(term), Equipment.serial_number.ilike(term)))
    if client_id:
        query = query.where(Equipment.client_id == client_id)
    if equipment_status:
        query = query.where(Equipment.status == equipment_status)
    return list(db.scalars(query.order_by(Equipment.name)).all())


@router.post("/equipment", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    user: User = Depends(require_permission("equipment.manage")),
    db: Session = Depends(get_db),
):
    get_client(db, payload.client_id, user.company_id)
    equipment_type = db.scalar(select(EquipmentType).where(
        EquipmentType.id == payload.equipment_type_id, EquipmentType.company_id == user.company_id, EquipmentType.deleted_at.is_(None)
    ))
    if not equipment_type:
        raise HTTPException(status_code=404, detail="Tipo de equipamento não encontrado")
    item = Equipment(company_id=user.company_id, created_by=user.id, **payload.model_dump())
    db.add(item)
    commit_or_conflict(db, "Código ou número de série já utilizado")
    return get_equipment(db, item.id, user.company_id)


@router.patch("/equipment/{equipment_id}", response_model=EquipmentOut)
def update_equipment(
    equipment_id: str,
    payload: EquipmentUpdate,
    user: User = Depends(require_permission("equipment.manage")),
    db: Session = Depends(get_db),
):
    item = get_equipment(db, equipment_id, user.company_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("client_id"):
        get_client(db, changes["client_id"], user.company_id)
    for field, value in changes.items():
        setattr(item, field, value)
    item.updated_by = user.id
    commit_or_conflict(db, "Código ou número de série já utilizado")
    return get_equipment(db, item.id, user.company_id)


@router.delete("/equipment/{equipment_id}", response_model=MessageResponse)
def delete_equipment(
    equipment_id: str,
    user: User = Depends(require_permission("equipment.manage")),
    db: Session = Depends(get_db),
):
    item = get_equipment(db, equipment_id, user.company_id)
    linked = db.scalar(select(func.count(Inspection.id)).where(Inspection.equipment_id == item.id, Inspection.deleted_at.is_(None))) or 0
    if linked:
        raise HTTPException(status_code=409, detail="O equipamento possui histórico de inspeções e não pode ser eliminado")
    item.deleted_at = datetime.now(timezone.utc)
    item.updated_by = user.id
    db.commit()
    return MessageResponse(message="Equipamento arquivado")


@router.get("/inspections", response_model=list[InspectionOut])
def list_inspections(
    inspection_status: str | None = Query(default=None, alias="status"),
    client_id: str | None = None,
    user: User = Depends(require_permission("inspections.view")),
    db: Session = Depends(get_db),
):
    query = inspection_query().where(Inspection.company_id == user.company_id, Inspection.deleted_at.is_(None))
    if inspection_status:
        query = query.where(Inspection.status == inspection_status)
    if client_id:
        query = query.where(Inspection.client_id == client_id)
    return list(db.scalars(query.order_by(Inspection.inspection_date.desc())).unique().all())


@router.post("/inspections", response_model=InspectionOut, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: InspectionCreate,
    user: User = Depends(require_permission("inspections.manage")),
    db: Session = Depends(get_db),
):
    equipment = get_equipment(db, payload.equipment_id, user.company_id)
    inspector_id = payload.inspector_id
    if not inspector_id:
        default_signatory = db.scalar(select(TechnicalSignatory).where(
            TechnicalSignatory.company_id == user.company_id,
            TechnicalSignatory.can_inspect.is_(True),
            TechnicalSignatory.status == "active",
            TechnicalSignatory.deleted_at.is_(None),
        ).order_by(TechnicalSignatory.created_at))
        inspector_id = default_signatory.employee_id if default_signatory else None
    if inspector_id:
        inspector = db.scalar(select(Employee).where(Employee.id == inspector_id, Employee.company_id == user.company_id, Employee.deleted_at.is_(None)))
        if not inspector:
            raise HTTPException(status_code=404, detail="Inspetor não encontrado")
    checklist_values = payload.checklist_items
    if payload.status == "approved" and any(item.result == "fail" for item in checklist_values):
        raise HTTPException(status_code=422, detail="Uma inspeção aprovada não pode conter itens reprovados")
    count = db.scalar(select(func.count(Inspection.id)).where(Inspection.company_id == user.company_id)) or 0
    next_date = payload.next_inspection_date or add_months(payload.inspection_date, equipment.type.inspection_interval_months)
    data = payload.model_dump(exclude={"checklist_items", "next_inspection_date", "inspector_id"})
    record = Inspection(
        company_id=user.company_id,
        client_id=equipment.client_id,
        inspection_no=f"INS-{payload.inspection_date.year}-{count + 1:04d}",
        inspector_id=inspector_id,
        next_inspection_date=next_date,
        created_by=user.id,
        **data,
    )
    db.add(record)
    db.flush()
    items = checklist_values
    if not items and equipment.type.checklist_template:
        items = [type("TemplateItem", (), item)() for item in json.loads(equipment.type.checklist_template)]
    for item in items:
        db.add(InspectionChecklistItem(
            company_id=user.company_id, inspection_id=record.id, created_by=user.id,
            item_code=item.item_code, item_label=item.item_label,
            expected_result=getattr(item, "expected_result", None), result=item.result,
            notes=getattr(item, "notes", None),
        ))
    db.commit()
    return get_inspection(db, record.id, user.company_id)


@router.patch("/inspections/{inspection_id}", response_model=InspectionOut)
def update_inspection(
    inspection_id: str,
    payload: InspectionUpdate,
    user: User = Depends(require_permission("inspections.manage")),
    db: Session = Depends(get_db),
):
    record = get_inspection(db, inspection_id, user.company_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"checklist_items"})
    checklist = payload.checklist_items
    final_status = changes.get("status", record.status)
    if final_status == "approved" and checklist and any(item.result == "fail" for item in checklist):
        raise HTTPException(status_code=422, detail="Uma inspeção aprovada não pode conter itens reprovados")
    for field, value in changes.items():
        setattr(record, field, value)
    if checklist is not None:
        record.checklist_items.clear()
        db.flush()
        for item in checklist:
            record.checklist_items.append(InspectionChecklistItem(company_id=user.company_id, created_by=user.id, **item.model_dump()))
    record.updated_by = user.id
    db.commit()
    return get_inspection(db, record.id, user.company_id)


@router.get("/signatories", response_model=list[TechnicalSignatoryOut])
def list_signatories(
    capability: str | None = Query(default=None, pattern="^(inspect|approve)$"),
    user: User = Depends(require_permission("certificates.view")),
    db: Session = Depends(get_db),
):
    query = select(TechnicalSignatory).options(selectinload(TechnicalSignatory.employee)).where(
        TechnicalSignatory.company_id == user.company_id,
        TechnicalSignatory.deleted_at.is_(None),
    )
    if capability == "inspect":
        query = query.where(TechnicalSignatory.can_inspect.is_(True), TechnicalSignatory.status == "active")
    if capability == "approve":
        query = query.where(TechnicalSignatory.can_approve.is_(True), TechnicalSignatory.status == "active")
    records = db.scalars(query.order_by(TechnicalSignatory.inspector_code)).all()
    return [signatory_out(record) for record in records]


@router.post("/signatories", response_model=TechnicalSignatoryOut, status_code=status.HTTP_201_CREATED)
def create_signatory(
    payload: TechnicalSignatoryCreate,
    user: User = Depends(require_permission("certificates.manage")),
    db: Session = Depends(get_db),
):
    employee = db.scalar(select(Employee).where(
        Employee.id == payload.employee_id,
        Employee.company_id == user.company_id,
        Employee.deleted_at.is_(None),
    ))
    if not employee:
        raise HTTPException(status_code=404, detail="Trabalhador nÃ£o encontrado")
    values = payload.model_dump(exclude={"signature_data_url", "stamp_data_url"})
    record = TechnicalSignatory(company_id=user.company_id, created_by=user.id, **values)
    db.add(record)
    try:
        db.flush()
        if payload.signature_data_url:
            record.signature_path = save_signatory_asset(payload.signature_data_url, record.id, "signature")
        if payload.stamp_data_url:
            record.stamp_path = save_signatory_asset(payload.stamp_data_url, record.id, "stamp")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="O trabalhador ou cÃ³digo jÃ¡ pertence a outro inspetor autorizado") from exc
    return signatory_out(get_signatory(db, record.id, user.company_id))


@router.patch("/signatories/{signatory_id}", response_model=TechnicalSignatoryOut)
def update_signatory(
    signatory_id: str,
    payload: TechnicalSignatoryUpdate,
    user: User = Depends(require_permission("certificates.manage")),
    db: Session = Depends(get_db),
):
    record = get_signatory(db, signatory_id, user.company_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"signature_data_url", "stamp_data_url"})
    for field, value in changes.items():
        setattr(record, field, value)
    if payload.signature_data_url:
        record.signature_path = save_signatory_asset(payload.signature_data_url, record.id, "signature")
    if payload.stamp_data_url:
        record.stamp_path = save_signatory_asset(payload.stamp_data_url, record.id, "stamp")
    record.updated_by = user.id
    commit_or_conflict(db, "O cÃ³digo do inspetor jÃ¡ estÃ¡ em uso")
    return signatory_out(get_signatory(db, record.id, user.company_id))


@router.get("/certificates", response_model=list[CertificateOut])
def list_certificates(
    certificate_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(require_permission("certificates.view")),
    db: Session = Depends(get_db),
):
    query = certificate_query().where(Certificate.deleted_at.is_(None))
    scope = portal_client_id(db, user)
    if user.account_type == "external":
        if not scope:
            return []
        query = query.where(Certificate.client_id == scope, Certificate.status == "issued")
    else:
        query = query.where(Certificate.company_id == user.company_id)
    if certificate_status:
        query = query.where(Certificate.status == certificate_status)
    records = db.scalars(query.order_by(Certificate.issued_at.desc())).unique().all()
    return [certificate_out(record) for record in records]


@router.post("/certificates", response_model=CertificateOut, status_code=status.HTTP_201_CREATED)
def create_certificate(
    payload: CertificateCreate,
    user: User = Depends(require_permission("certificates.manage")),
    db: Session = Depends(get_db),
):
    inspection = get_inspection(db, payload.inspection_id, user.company_id)
    if inspection.status != "approved":
        raise HTTPException(status_code=409, detail="A inspeção deve estar aprovada antes de criar o certificado")
    if inspection.certificate:
        raise HTTPException(status_code=409, detail="Esta inspeção já possui certificado")
    count = db.scalar(select(func.count(Certificate.id)).where(
        Certificate.company_id == user.company_id,
        func.extract("year", Certificate.issued_at) == date.today().year,
    )) or 0
    if payload.approver_signatory_id:
        approver = get_signatory(db, payload.approver_signatory_id, user.company_id)
        if not approver.can_approve or approver.status != "active":
            raise HTTPException(status_code=422, detail="O signatÃ¡rio selecionado nÃ£o pode aprovar certificados")
    else:
        approver = db.scalar(select(TechnicalSignatory).where(
            TechnicalSignatory.company_id == user.company_id,
            TechnicalSignatory.can_approve.is_(True),
            TechnicalSignatory.status == "active",
            TechnicalSignatory.deleted_at.is_(None),
        ).order_by(TechnicalSignatory.created_at))
    certificate_no = f"FNL-CTE-{date.today().year}-{count + 1:03d}"
    values = payload.model_dump(exclude={"inspection_id", "approver_signatory_id", "service_order_no", "report_no", "identification_no"})
    record = Certificate(
        company_id=user.company_id,
        client_id=inspection.client_id,
        equipment_id=inspection.equipment_id,
        inspection_id=inspection.id,
        certificate_no=certificate_no,
        approver_signatory_id=approver.id if approver else None,
        service_order_no=payload.service_order_no or f"SERVICE ORDER-{count + 1:03d}",
        report_no=payload.report_no or certificate_no,
        identification_no=payload.identification_no or inspection.equipment.serial_number or inspection.equipment.code,
        issued_at=date.today(),
        expires_at=inspection.next_inspection_date or add_months(inspection.inspection_date, inspection.equipment.type.inspection_interval_months),
        qr_token=secrets.token_urlsafe(24),
        status="draft",
        created_by=user.id,
        **values,
    )
    db.add(record)
    commit_or_conflict(db, "Esta inspeção já possui certificado")
    return certificate_out(get_certificate(db, record.id))


@router.patch("/certificates/{certificate_id}", response_model=CertificateOut)
def update_certificate(
    certificate_id: str,
    payload: CertificateUpdate,
    user: User = Depends(require_permission("certificates.manage")),
    db: Session = Depends(get_db),
):
    record = get_certificate(db, certificate_id)
    if record.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    if record.status != "draft":
        raise HTTPException(status_code=409, detail="Apenas certificados em rascunho podem ser editados")
    changes = payload.model_dump(exclude_unset=True)
    if "approver_signatory_id" in changes and changes["approver_signatory_id"]:
        approver = get_signatory(db, changes["approver_signatory_id"], user.company_id)
        if not approver.can_approve or approver.status != "active":
            raise HTTPException(status_code=422, detail="O signatário selecionado não pode aprovar certificados")
    for field, value in changes.items():
        setattr(record, field, value)
    record.pdf_path = None
    record.updated_by = user.id
    db.commit()
    return certificate_out(get_certificate(db, record.id))


@router.post("/certificates/{certificate_id}/issue", response_model=CertificateOut)
def issue_certificate(
    certificate_id: str,
    user: User = Depends(require_permission("certificates.manage")),
    db: Session = Depends(get_db),
):
    record = get_certificate(db, certificate_id)
    if record.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    if record.inspection.status != "approved":
        raise HTTPException(status_code=409, detail="A inspeção deixou de estar aprovada")
    inspector_profile = record.inspection.inspector.technical_signatory if record.inspection.inspector else None
    if not inspector_profile or inspector_profile.status != "active" or not inspector_profile.can_inspect:
        raise HTTPException(status_code=409, detail="A inspeÃ§Ã£o deve ter um inspetor autorizado ativo")
    if not inspector_profile.signature_path or not inspector_profile.stamp_path:
        raise HTTPException(status_code=409, detail="O inspetor deve possuir assinatura e carimbo registados")
    if not record.approver_signatory or record.approver_signatory.status != "active" or not record.approver_signatory.can_approve:
        raise HTTPException(status_code=409, detail="Selecione um supervisor autorizado para autenticar o certificado")
    if not record.approver_signatory.signature_path or not record.approver_signatory.stamp_path:
        raise HTTPException(status_code=409, detail="O supervisor deve possuir assinatura e carimbo registados")
    record.status = "issued"
    record.approved_by = user.id
    record.updated_by = user.id
    db.commit()
    record = get_certificate(db, certificate_id)
    path = generate_certificate_pdf(record)
    record.pdf_path = str(path)
    db.commit()
    return certificate_out(record)


@router.get("/certificates/{certificate_id}/pdf")
def download_certificate_pdf(
    certificate_id: str,
    user: User = Depends(require_permission("certificates.view")),
    db: Session = Depends(get_db),
):
    record = get_certificate(db, certificate_id)
    scope = portal_client_id(db, user)
    if user.account_type == "external" and record.client_id != scope:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    if user.account_type != "external" and record.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    if record.status != "issued" and user.account_type == "external":
        raise HTTPException(status_code=409, detail="O certificado ainda não foi emitido")
    if record.status not in {"draft", "issued"}:
        raise HTTPException(status_code=409, detail="O certificado não está disponível para visualização")
    path = Path(record.pdf_path) if record.pdf_path else generate_certificate_pdf(record)
    if not record.pdf_path:
        record.pdf_path = str(path)
        db.commit()
    return FileResponse(path, media_type="application/pdf", filename=f"{record.certificate_no}.pdf")


@public_router.get("/certificates/{qr_token}", response_model=PublicCertificateOut)
def verify_certificate(qr_token: str, db: Session = Depends(get_db)):
    record = db.scalar(certificate_query().where(Certificate.qr_token == qr_token, Certificate.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    is_valid = record.status == "issued" and record.expires_at >= date.today() and record.inspection.status == "approved"
    public_fingerprint = "|".join([
        record.certificate_no,
        str(record.issued_at),
        str(record.expires_at),
        record.status,
        record.qr_token,
    ])
    return PublicCertificateOut(
        certificate_no=record.certificate_no,
        document_type=record.document_type,
        client_name=record.client.name,
        equipment_code=record.equipment.code,
        equipment_name=record.equipment.name,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        inspection_status=record.inspection.status,
        certificate_status=record.status,
        valid=is_valid,
        validation_hash=hashlib.sha256(public_fingerprint.encode("utf-8")).hexdigest(),
    )
