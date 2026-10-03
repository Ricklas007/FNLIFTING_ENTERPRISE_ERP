import base64
import binascii
import hashlib
import json
import secrets
from io import BytesIO
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_permission
from app.core.config import ATTACHMENT_DIR, UPLOAD_DIR
from app.database.session import get_db
from app.models import (
    Asset, AssetMaintenance, AssetTransfer, AuditLog, Client, Department, Document,
    DocumentVersion, Employee, Equipment, Expense, Inspection, Invoice, InvoiceItem,
    MediaAttachment, Payment, Receipt, Revenue, Truck, User,
)
from app.pdf.financial import generate_invoice_pdf, generate_receipt_pdf
from app.schemas.auth import MessageResponse
from app.schemas.management import (
    AssetCreate, AssetOut, AssetSummary, AssetUpdate, AuditLogOut, AuditSummary,
    DocumentCreate, DocumentOut, DocumentReview, DocumentUpdate, DocumentVersionCreate, ExpenseCreate, ExpenseOut,
    FinanceSummary, InvoiceCreate, InvoiceOut, MaintenanceCreate, MaintenanceOut,
    MediaAttachmentCreate, MediaAttachmentOut, PaymentCreate, ReceiptOut, RevenueCreate, RevenueOut, TransferCreate, TransferOut,
)


router = APIRouter(prefix="/management", tags=["Património, Financeiro, Documentos e Auditoria"])
DOCUMENT_DIR = UPLOAD_DIR / "documents"
MEDIA_DIR = ATTACHMENT_DIR / "media"
DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


MEDIA_ENTITIES = {
    "employee": (Employee, "employees.view", "employees.manage"),
    "worker": (Employee, "employees.view", "employees.manage"),
    "equipment": (Equipment, "equipment.view", "equipment.manage"),
    "truck": (Truck, "fleet.view", "fleet.manage"),
    "vehicle": (Truck, "fleet.view", "fleet.manage"),
    "asset": (Asset, "assets.view", "assets.manage"),
    "client": (Client, "clients.view", "clients.manage"),
    "inspection": (Inspection, "inspections.view", "inspections.manage"),
    "document": (Document, "documents.view", "documents.manage"),
}
MEDIA_ALLOWED_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
MEDIA_MAX_BYTES = 10_000_000


def commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


def audit(db: Session, request: Request, user: User, action: str, entity_type: str, entity_id: str | None,
          label: str | None, before=None, after=None, description: str | None = None) -> None:
    def encode(value):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, default=str)
    db.add(AuditLog(
        company_id=user.company_id, user_id=user.id, action=action, entity_type=entity_type,
        entity_id=entity_id, entity_label=label, before_data=encode(before), after_data=encode(after),
        ip_address=request.client.host if request.client else None,
        machine_name=request.headers.get("x-machine-name") or request.headers.get("user-agent", "")[:160],
        description=description, created_by=user.id,
    ))


def has_permission(user: User, permission: str) -> bool:
    codes = user.permission_codes
    return "*" in codes or permission in codes


def canonical_media_entity(entity_type: str) -> str:
    key = entity_type.strip().lower().replace("-", "_")
    aliases = {"workers": "worker", "employees": "employee", "vehicles": "vehicle", "trucks": "truck", "assets": "asset", "equipment_items": "equipment"}
    key = aliases.get(key, key)
    if key not in MEDIA_ENTITIES:
        raise HTTPException(status_code=422, detail="Tipo de entidade não suportado para anexos")
    return key


def ensure_media_entity_access(db: Session, user: User, entity_type: str, entity_id: str, action: str) -> str:
    canonical = canonical_media_entity(entity_type)
    model, view_permission, manage_permission = MEDIA_ENTITIES[canonical]
    required = manage_permission if action == "manage" else view_permission
    if not has_permission(user, required):
        raise HTTPException(status_code=403, detail="Não possui permissão para os anexos desta entidade")
    exists = db.scalar(select(model.id).where(
        model.id == entity_id,
        model.company_id == user.company_id,
        model.deleted_at.is_(None),
    ))
    if not exists:
        raise HTTPException(status_code=404, detail="Entidade associada ao anexo não encontrada")
    return "employee" if canonical == "worker" else "truck" if canonical == "vehicle" else canonical


def media_out(record: MediaAttachment) -> MediaAttachmentOut:
    result = MediaAttachmentOut.model_validate(record)
    result.thumbnail_available = bool(record.thumbnail_path and Path(record.thumbnail_path).exists())
    return result


def safe_media_name(file_name: str, fallback_extension: str) -> str:
    base_name = Path(file_name or f"attachment.{fallback_extension}").name
    safe = "".join(character for character in base_name if character.isalnum() or character in ".-_ ")[:120].strip(" .")
    return safe or f"attachment.{fallback_extension}"


def create_media_thumbnail(content: bytes, mime_type: str, destination: Path) -> str | None:
    if not mime_type.startswith("image/"):
        return None
    try:
        from PIL import Image  # type: ignore
        image = Image.open(BytesIO(content))
        image.thumbnail((360, 360))
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        image.save(destination)
    except Exception:
        destination.write_bytes(content)
    return str(destination)


def decode_media_payload(data_url: str) -> tuple[str, bytes, str]:
    try:
        header, encoded = data_url.split(",", 1)
        mime_type = header.split(";")[0].removeprefix("data:").lower()
        extension = MEDIA_ALLOWED_TYPES[mime_type]
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, KeyError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail="Anexo inválido; utilize PNG, JPEG, WEBP, PDF, TXT ou DOCX") from exc
    if len(content) > MEDIA_MAX_BYTES:
        raise HTTPException(status_code=422, detail="O anexo excede 10 MB")
    if not content:
        raise HTTPException(status_code=422, detail="O anexo está vazio")
    return mime_type, content, extension


def get_media_attachment(db: Session, attachment_id: str, user: User, action: str = "view") -> MediaAttachment:
    record = db.scalar(select(MediaAttachment).where(
        MediaAttachment.id == attachment_id,
        MediaAttachment.company_id == user.company_id,
        MediaAttachment.deleted_at.is_(None),
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    ensure_media_entity_access(db, user, record.entity_type, record.entity_id, action)
    return record


def media_file_response(path_value: str, mime_type: str, filename: str) -> FileResponse:
    path = Path(path_value).resolve()
    root = MEDIA_DIR.resolve()
    if root not in path.parents and path != root:
        raise HTTPException(status_code=403, detail="Caminho de anexo inválido")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Ficheiro do anexo não encontrado")
    return FileResponse(path, media_type=mime_type, filename=filename)


def portal_client_id(db: Session, user: User) -> str | None:
    if user.account_type != "external":
        return None
    return db.scalar(select(Client.id).where(Client.portal_company_id == user.company_id, Client.deleted_at.is_(None)))


@router.get("/media/entities/{entity_type}/{entity_id}", response_model=list[MediaAttachmentOut])
def list_media_attachments(
    entity_type: str,
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    canonical = ensure_media_entity_access(db, user, entity_type, entity_id, "view")
    records = db.scalars(select(MediaAttachment).where(
        MediaAttachment.company_id == user.company_id,
        MediaAttachment.entity_type == canonical,
        MediaAttachment.entity_id == entity_id,
        MediaAttachment.status == "active",
        MediaAttachment.deleted_at.is_(None),
    ).order_by(MediaAttachment.created_at.desc())).all()
    return [media_out(record) for record in records]


@router.post("/media/entities/{entity_type}/{entity_id}", response_model=MediaAttachmentOut, status_code=status.HTTP_201_CREATED)
def create_media_attachment(
    entity_type: str,
    entity_id: str,
    payload: MediaAttachmentCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    canonical = ensure_media_entity_access(db, user, entity_type, entity_id, "manage")
    mime_type, content, extension = decode_media_payload(payload.file_data_url)
    checksum = hashlib.sha256(content).hexdigest()
    safe_name = safe_media_name(payload.file_name, extension)
    folder = MEDIA_DIR / canonical / entity_id
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(6)}-{safe_name}"
    file_path = folder / stored_name
    file_path.write_bytes(content)
    thumb_path = create_media_thumbnail(content, mime_type, folder / f"thumb-{stored_name}")
    record = MediaAttachment(
        company_id=user.company_id,
        entity_type=canonical,
        entity_id=entity_id,
        title=payload.title,
        category=payload.category,
        caption=payload.caption,
        file_name=safe_name,
        file_path=str(file_path),
        mime_type=mime_type,
        file_size=len(content),
        checksum_sha256=checksum,
        thumbnail_path=thumb_path,
        uploaded_by=user.id,
        created_by=user.id,
    )
    db.add(record)
    db.flush()
    audit(db, request, user, "upload", "media_attachment", record.id, f"{canonical}:{entity_id}", after={
        "entity_type": canonical,
        "entity_id": entity_id,
        "file_name": safe_name,
        "checksum": checksum,
    })
    db.commit()
    db.refresh(record)
    return media_out(record)


@router.get("/media/{attachment_id}/download")
def download_media_attachment(
    attachment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_media_attachment(db, attachment_id, user)
    return media_file_response(record.file_path, record.mime_type, record.file_name)


@router.get("/media/{attachment_id}/thumbnail")
def thumbnail_media_attachment(
    attachment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_media_attachment(db, attachment_id, user)
    if not record.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail não disponível para este anexo")
    extension = MEDIA_ALLOWED_TYPES.get(record.mime_type, "bin")
    return media_file_response(record.thumbnail_path, record.mime_type, f"thumb-{Path(record.file_name).stem}.{extension}")


@router.delete("/media/{attachment_id}", response_model=MessageResponse)
def archive_media_attachment(
    attachment_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_media_attachment(db, attachment_id, user, "manage")
    before = {"status": record.status}
    record.status = "archived"
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = user.id
    audit(db, request, user, "archive", "media_attachment", record.id, record.file_name, before=before, after={"status": record.status})
    db.commit()
    return MessageResponse(message="Anexo arquivado")


def employee_exists(db: Session, employee_id: str | None, company_id: str) -> None:
    if employee_id and not db.scalar(select(Employee.id).where(Employee.id == employee_id, Employee.company_id == company_id, Employee.deleted_at.is_(None))):
        raise HTTPException(status_code=404, detail="Trabalhador não encontrado")


def asset_query():
    return select(Asset).options(selectinload(Asset.responsible))


def get_asset(db: Session, asset_id: str, company_id: str) -> Asset:
    record = db.scalar(asset_query().where(Asset.id == asset_id, Asset.company_id == company_id, Asset.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Património não encontrado")
    return record


def asset_out(db: Session, record: Asset) -> AssetOut:
    result = AssetOut.model_validate(record)
    result.maintenance_count = db.scalar(select(func.count(AssetMaintenance.id)).where(AssetMaintenance.asset_id == record.id, AssetMaintenance.deleted_at.is_(None))) or 0
    result.transfer_count = db.scalar(select(func.count(AssetTransfer.id)).where(AssetTransfer.asset_id == record.id, AssetTransfer.deleted_at.is_(None))) or 0
    return result


@router.get("/assets/summary", response_model=AssetSummary)
def asset_summary(user: User = Depends(require_permission("assets.view")), db: Session = Depends(get_db)):
    today = date.today()
    categories = db.execute(select(Asset.category, func.count(Asset.id)).where(
        Asset.company_id == user.company_id, Asset.deleted_at.is_(None)
    ).group_by(Asset.category)).all()
    return AssetSummary(
        total_assets=db.scalar(select(func.count(Asset.id)).where(Asset.company_id == user.company_id, Asset.deleted_at.is_(None))) or 0,
        active_assets=db.scalar(select(func.count(Asset.id)).where(Asset.company_id == user.company_id, Asset.status == "active", Asset.deleted_at.is_(None))) or 0,
        in_maintenance=db.scalar(select(func.count(Asset.id)).where(Asset.company_id == user.company_id, Asset.status == "maintenance", Asset.deleted_at.is_(None))) or 0,
        maintenance_due=db.scalar(select(func.count(AssetMaintenance.id)).where(AssetMaintenance.company_id == user.company_id, AssetMaintenance.status == "scheduled", AssetMaintenance.scheduled_date <= today + timedelta(days=30), AssetMaintenance.deleted_at.is_(None))) or 0,
        acquisition_value=db.scalar(select(func.coalesce(func.sum(Asset.acquisition_value), 0)).where(Asset.company_id == user.company_id, Asset.deleted_at.is_(None))) or Decimal(0),
        current_value=db.scalar(select(func.coalesce(func.sum(Asset.current_value), 0)).where(Asset.company_id == user.company_id, Asset.deleted_at.is_(None))) or Decimal(0),
        by_category=[{"name": name, "value": value} for name, value in categories],
    )


@router.get("/assets", response_model=list[AssetOut])
def list_assets(search: str | None = Query(default=None, max_length=100), user: User = Depends(require_permission("assets.view")), db: Session = Depends(get_db)):
    query = asset_query().where(Asset.company_id == user.company_id, Asset.deleted_at.is_(None))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Asset.name.ilike(term), Asset.asset_code.ilike(term), Asset.serial_number.ilike(term), Asset.category.ilike(term)))
    return [asset_out(db, item) for item in db.scalars(query.order_by(Asset.asset_code)).all()]


@router.post("/assets", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, request: Request, user: User = Depends(require_permission("assets.manage")), db: Session = Depends(get_db)):
    employee_exists(db, payload.responsible_id, user.company_id)
    values = payload.model_dump()
    if values["current_value"] is None:
        values["current_value"] = values["acquisition_value"]
    record = Asset(company_id=user.company_id, created_by=user.id, **values)
    db.add(record); db.flush()
    audit(db, request, user, "create", "asset", record.id, record.asset_code, after=values)
    commit_or_conflict(db, "Código ou número de série já utilizado")
    return asset_out(db, get_asset(db, record.id, user.company_id))


@router.patch("/assets/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: str, payload: AssetUpdate, request: Request, user: User = Depends(require_permission("assets.manage")), db: Session = Depends(get_db)):
    record = get_asset(db, asset_id, user.company_id)
    changes = payload.model_dump(exclude_unset=True)
    employee_exists(db, changes.get("responsible_id"), user.company_id)
    before = {field: getattr(record, field) for field in changes}
    for field, value in changes.items(): setattr(record, field, value)
    record.updated_by = user.id
    audit(db, request, user, "update", "asset", record.id, record.asset_code, before=before, after=changes)
    commit_or_conflict(db, "Número de série já utilizado")
    return asset_out(db, get_asset(db, record.id, user.company_id))


@router.post("/assets/{asset_id}/maintenance", response_model=MaintenanceOut, status_code=status.HTTP_201_CREATED)
def create_maintenance(asset_id: str, payload: MaintenanceCreate, request: Request, user: User = Depends(require_permission("assets.manage")), db: Session = Depends(get_db)):
    asset = get_asset(db, asset_id, user.company_id)
    record = AssetMaintenance(company_id=user.company_id, asset_id=asset.id, created_by=user.id, **payload.model_dump())
    if record.status in {"scheduled", "in_progress"}: asset.status = "maintenance"
    if record.status == "completed": asset.status = "active"
    db.add(record); db.flush()
    audit(db, request, user, "create", "asset_maintenance", record.id, asset.asset_code, after=payload.model_dump())
    db.commit(); db.refresh(record)
    return record


@router.get("/assets/{asset_id}/maintenance", response_model=list[MaintenanceOut])
def list_maintenance(asset_id: str, user: User = Depends(require_permission("assets.view")), db: Session = Depends(get_db)):
    get_asset(db, asset_id, user.company_id)
    return list(db.scalars(select(AssetMaintenance).where(AssetMaintenance.asset_id == asset_id, AssetMaintenance.deleted_at.is_(None)).order_by(AssetMaintenance.scheduled_date.desc())).all())


@router.post("/assets/{asset_id}/transfers", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def create_transfer(asset_id: str, payload: TransferCreate, request: Request, user: User = Depends(require_permission("assets.manage")), db: Session = Depends(get_db)):
    asset = get_asset(db, asset_id, user.company_id)
    employee_exists(db, payload.to_responsible_id, user.company_id)
    record = AssetTransfer(
        company_id=user.company_id, asset_id=asset.id, from_responsible_id=asset.responsible_id,
        to_responsible_id=payload.to_responsible_id, from_location=asset.location,
        to_location=payload.to_location, transfer_date=payload.transfer_date, reason=payload.reason, created_by=user.id,
    )
    before = {"responsible_id": asset.responsible_id, "location": asset.location}
    asset.responsible_id = payload.to_responsible_id; asset.location = payload.to_location; asset.status = "active"
    db.add(record); db.flush()
    audit(db, request, user, "transfer", "asset", asset.id, asset.asset_code, before=before, after={"responsible_id": asset.responsible_id, "location": asset.location})
    db.commit()
    return db.scalar(select(AssetTransfer).options(selectinload(AssetTransfer.from_responsible), selectinload(AssetTransfer.to_responsible)).where(AssetTransfer.id == record.id))


def expense_out(record: Expense) -> ExpenseOut:
    result = ExpenseOut.model_validate(record)
    result.department_name = record.department.name if record.department else None
    result.responsible_name = record.responsible.full_name if record.responsible else None
    return result


def invoice_query():
    return select(Invoice).options(selectinload(Invoice.client), selectinload(Invoice.items), selectinload(Invoice.payments))


def get_invoice(db: Session, invoice_id: str, company_id: str) -> Invoice:
    record = db.scalar(invoice_query().where(Invoice.id == invoice_id, Invoice.company_id == company_id, Invoice.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    return record


def invoice_out(record: Invoice) -> InvoiceOut:
    result = InvoiceOut.model_validate(record)
    paid = sum((payment.amount for payment in record.payments if payment.status == "confirmed"), Decimal(0))
    result.paid_amount = paid
    result.balance_due = max(Decimal(0), record.total_amount - paid)
    result.pdf_available = bool(record.pdf_path and Path(record.pdf_path).exists())
    return result


def receipt_query():
    return select(Receipt).options(
        selectinload(Receipt.client), selectinload(Receipt.payment),
        selectinload(Receipt.invoice).selectinload(Invoice.client),
        selectinload(Receipt.invoice).selectinload(Invoice.items),
        selectinload(Receipt.invoice).selectinload(Invoice.payments),
    )


def receipt_out(record: Receipt) -> ReceiptOut:
    result = ReceiptOut.model_validate(record)
    result.invoice = invoice_out(record.invoice)
    result.pdf_available = bool(record.pdf_path and Path(record.pdf_path).exists())
    return result


@router.get("/finance/summary", response_model=FinanceSummary)
def finance_summary(user: User = Depends(require_permission("finance.view")), db: Session = Depends(get_db)):
    company_id = user.company_id
    revenue = db.scalar(select(func.coalesce(func.sum(Revenue.amount), 0)).where(Revenue.company_id == company_id, Revenue.status == "paid", Revenue.deleted_at.is_(None))) or Decimal(0)
    expenses = db.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.company_id == company_id, Expense.status.in_(["approved", "paid"]), Expense.deleted_at.is_(None))) or Decimal(0)
    invoice_total = db.scalar(select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.company_id == company_id, Invoice.status.in_(["issued", "partial", "overdue"]), Invoice.deleted_at.is_(None))) or Decimal(0)
    paid_total = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.company_id == company_id, Payment.status == "confirmed", Payment.deleted_at.is_(None))) or Decimal(0)
    categories = db.execute(select(Expense.category, func.sum(Expense.amount)).where(Expense.company_id == company_id, Expense.deleted_at.is_(None)).group_by(Expense.category)).all()
    cash_flow = []
    for offset in range(5, -1, -1):
        month = (date.today().replace(day=1) - timedelta(days=offset * 30)).strftime("%Y-%m")
        cash_flow.append({"period": month, "revenue": float(revenue) / 6, "expense": float(expenses) / 6})
    return FinanceSummary(
        revenue_total=revenue, expense_total=expenses, profit=revenue - expenses,
        receivables=max(Decimal(0), invoice_total - paid_total),
        payables=db.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.company_id == company_id, Expense.status == "pending", Expense.deleted_at.is_(None))) or Decimal(0),
        invoices_open=db.scalar(select(func.count(Invoice.id)).where(Invoice.company_id == company_id, Invoice.status.in_(["issued", "partial", "overdue"]), Invoice.deleted_at.is_(None))) or 0,
        expenses_pending=db.scalar(select(func.count(Expense.id)).where(Expense.company_id == company_id, Expense.status == "pending", Expense.deleted_at.is_(None))) or 0,
        cash_flow=cash_flow,
        expenses_by_category=[{"name": name, "value": float(value)} for name, value in categories],
    )


@router.get("/finance/expenses", response_model=list[ExpenseOut])
def list_expenses(user: User = Depends(require_permission("finance.view")), db: Session = Depends(get_db)):
    records = db.scalars(select(Expense).options(selectinload(Expense.department), selectinload(Expense.responsible)).where(Expense.company_id == user.company_id, Expense.deleted_at.is_(None)).order_by(Expense.transaction_date.desc())).all()
    return [expense_out(record) for record in records]


@router.post("/finance/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, request: Request, user: User = Depends(require_permission("finance.manage")), db: Session = Depends(get_db)):
    employee_exists(db, payload.responsible_id, user.company_id)
    record = Expense(company_id=user.company_id, created_by=user.id, **payload.model_dump())
    db.add(record); db.flush(); audit(db, request, user, "create", "expense", record.id, record.description, after=payload.model_dump()); db.commit()
    return expense_out(db.scalar(select(Expense).options(selectinload(Expense.department), selectinload(Expense.responsible)).where(Expense.id == record.id)))


@router.post("/finance/expenses/{expense_id}/approve", response_model=ExpenseOut)
def approve_expense(expense_id: str, request: Request, user: User = Depends(require_permission("finance.manage")), db: Session = Depends(get_db)):
    record = db.scalar(select(Expense).options(selectinload(Expense.department), selectinload(Expense.responsible)).where(Expense.id == expense_id, Expense.company_id == user.company_id, Expense.deleted_at.is_(None)))
    if not record: raise HTTPException(status_code=404, detail="Despesa não encontrada")
    before = {"status": record.status}; record.status = "approved"; record.approved_by = user.id; record.approved_at = datetime.now(timezone.utc)
    audit(db, request, user, "approve", "expense", record.id, record.description, before=before, after={"status": record.status}); db.commit()
    return expense_out(record)


@router.get("/finance/revenues", response_model=list[RevenueOut])
def list_revenues(user: User = Depends(require_permission("finance.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(Revenue).options(selectinload(Revenue.client)).where(Revenue.company_id == user.company_id, Revenue.deleted_at.is_(None)).order_by(Revenue.transaction_date.desc())).all())


@router.post("/finance/revenues", response_model=RevenueOut, status_code=status.HTTP_201_CREATED)
def create_revenue(payload: RevenueCreate, request: Request, user: User = Depends(require_permission("finance.manage")), db: Session = Depends(get_db)):
    client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.company_id == user.company_id, Client.deleted_at.is_(None)))
    if not client: raise HTTPException(status_code=404, detail="Cliente não encontrado")
    values = payload.model_dump(); record = Revenue(company_id=user.company_id, paid_at=datetime.now(timezone.utc) if payload.status == "paid" else None, created_by=user.id, **values)
    db.add(record); db.flush(); audit(db, request, user, "create", "revenue", record.id, record.description, after=values); db.commit()
    return db.scalar(select(Revenue).options(selectinload(Revenue.client)).where(Revenue.id == record.id))


@router.get("/finance/invoices", response_model=list[InvoiceOut])
def list_invoices(user: User = Depends(require_permission("finance.view")), db: Session = Depends(get_db)):
    query = invoice_query().where(Invoice.deleted_at.is_(None))
    scope = portal_client_id(db, user)
    query = query.where(Invoice.client_id == scope) if user.account_type == "external" else query.where(Invoice.company_id == user.company_id)
    return [invoice_out(record) for record in db.scalars(query.order_by(Invoice.issue_date.desc())).unique().all()]


@router.post("/finance/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, request: Request, user: User = Depends(require_permission("finance.manage")), db: Session = Depends(get_db)):
    client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.company_id == user.company_id, Client.deleted_at.is_(None)))
    if not client: raise HTTPException(status_code=404, detail="Cliente não encontrado")
    count = db.scalar(select(func.count(Invoice.id)).where(Invoice.company_id == user.company_id)) or 0
    subtotal = sum((item.quantity * item.unit_price for item in payload.items), Decimal(0))
    tax = sum((item.quantity * item.unit_price * item.tax_rate / Decimal(100) for item in payload.items), Decimal(0))
    values = payload.model_dump(exclude={"items"})
    record = Invoice(company_id=user.company_id, invoice_no=f"FNL-FT-{date.today().year}-{count + 1:04d}", subtotal=subtotal, tax_amount=tax, total_amount=subtotal + tax, created_by=user.id, **values)
    db.add(record); db.flush()
    for item in payload.items:
        db.add(InvoiceItem(company_id=user.company_id, invoice_id=record.id, line_total=item.quantity * item.unit_price, created_by=user.id, **item.model_dump()))
    audit(db, request, user, "create", "invoice", record.id, record.invoice_no, after={"client": client.name, "total": record.total_amount}); db.commit()
    record = get_invoice(db, record.id, user.company_id); path = generate_invoice_pdf(record); record.pdf_path = str(path); db.commit()
    return invoice_out(record)


@router.post("/finance/invoices/{invoice_id}/payments", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
def register_payment(invoice_id: str, payload: PaymentCreate, request: Request, user: User = Depends(require_permission("finance.manage")), db: Session = Depends(get_db)):
    invoice = get_invoice(db, invoice_id, user.company_id); current = invoice_out(invoice)
    if payload.amount > current.balance_due: raise HTTPException(status_code=422, detail="O pagamento excede o saldo da fatura")
    payment = Payment(company_id=user.company_id, invoice_id=invoice.id, created_by=user.id, **payload.model_dump())
    db.add(payment); db.flush()
    count = db.scalar(select(func.count(Receipt.id)).where(Receipt.company_id == user.company_id)) or 0
    receipt = Receipt(company_id=user.company_id, client_id=invoice.client_id, invoice_id=invoice.id, payment_id=payment.id, receipt_no=f"FNL-RC-{date.today().year}-{count + 1:04d}", issued_at=payload.payment_date, amount=payload.amount, created_by=user.id)
    db.add(receipt); db.flush()
    paid = current.paid_amount + payload.amount; invoice.status = "paid" if paid >= invoice.total_amount else "partial"
    revenue = Revenue(company_id=user.company_id, client_id=invoice.client_id, invoice_id=invoice.id, amount=payload.amount, transaction_date=payload.payment_date, description=f"Pagamento {invoice.invoice_no}", service="Fatura", payment_method=payload.method, reference=payload.reference, paid_at=datetime.now(timezone.utc), status="paid", created_by=user.id)
    db.add(revenue); audit(db, request, user, "payment", "invoice", invoice.id, invoice.invoice_no, after={"amount": payload.amount, "status": invoice.status}); db.commit()
    record = db.scalar(receipt_query().where(Receipt.id == receipt.id)); path = generate_receipt_pdf(record); record.pdf_path = str(path); db.commit()
    return receipt_out(record)


@router.get("/finance/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: str, user: User = Depends(require_permission("finance.view")), db: Session = Depends(get_db)):
    invoice = get_invoice(db, invoice_id, user.company_id) if user.account_type != "external" else db.scalar(invoice_query().where(Invoice.id == invoice_id, Invoice.client_id == portal_client_id(db, user)))
    if not invoice: raise HTTPException(status_code=404, detail="Fatura não encontrada")
    path = Path(invoice.pdf_path) if invoice.pdf_path and Path(invoice.pdf_path).exists() else generate_invoice_pdf(invoice)
    return FileResponse(path, media_type="application/pdf", filename=f"{invoice.invoice_no}.pdf")


@router.get("/finance/receipts", response_model=list[ReceiptOut])
def list_receipts(user: User = Depends(require_permission("finance.view")), db: Session = Depends(get_db)):
    query = receipt_query().where(Receipt.deleted_at.is_(None))
    scope = portal_client_id(db, user); query = query.where(Receipt.client_id == scope) if user.account_type == "external" else query.where(Receipt.company_id == user.company_id)
    return [receipt_out(record) for record in db.scalars(query.order_by(Receipt.issued_at.desc())).unique().all()]


@router.get("/finance/receipts/{receipt_id}/pdf")
def receipt_pdf(receipt_id: str, user: User = Depends(require_permission("finance.view")), db: Session = Depends(get_db)):
    query = receipt_query().where(Receipt.id == receipt_id, Receipt.deleted_at.is_(None)); scope = portal_client_id(db, user)
    query = query.where(Receipt.client_id == scope) if user.account_type == "external" else query.where(Receipt.company_id == user.company_id)
    record = db.scalar(query)
    if not record: raise HTTPException(status_code=404, detail="Recibo não encontrado")
    path = Path(record.pdf_path) if record.pdf_path and Path(record.pdf_path).exists() else generate_receipt_pdf(record)
    return FileResponse(path, media_type="application/pdf", filename=f"{record.receipt_no}.pdf")


def save_document_file(data_url: str, document_id: str, version: int, file_name: str) -> tuple[str, str, int, str]:
    try:
        header, encoded = data_url.split(",", 1); mime = header.split(";")[0].removeprefix("data:")
        allowed = {"application/pdf", "image/png", "image/jpeg", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        if mime not in allowed: raise ValueError
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail="Ficheiro inválido; utilize PDF, PNG, JPEG, TXT ou DOCX") from exc
    if len(content) > 10_000_000: raise HTTPException(status_code=422, detail="O ficheiro excede 10 MB")
    safe_name = "".join(character for character in Path(file_name).name if character.isalnum() or character in ".-_ ")[:120]
    folder = DOCUMENT_DIR / document_id; folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"v{version}-{safe_name}"; path.write_bytes(content)
    return str(path), mime, len(content), hashlib.sha256(content).hexdigest()


def document_query():
    return select(Document).options(selectinload(Document.client), selectinload(Document.employee), selectinload(Document.versions))


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(search: str | None = Query(default=None, max_length=100), user: User = Depends(require_permission("documents.view")), db: Session = Depends(get_db)):
    query = document_query().where(Document.deleted_at.is_(None)); scope = portal_client_id(db, user)
    query = query.where(Document.client_id == scope, Document.approval_status == "approved") if user.account_type == "external" else query.where(Document.company_id == user.company_id)
    if search: query = query.where(or_(Document.title.ilike(f"%{search}%"), Document.document_no.ilike(f"%{search}%"), Document.category.ilike(f"%{search}%")))
    return list(db.scalars(query.order_by(Document.updated_at.desc())).unique().all())


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, request: Request, user: User = Depends(require_permission("documents.manage")), db: Session = Depends(get_db)):
    count = db.scalar(select(func.count(Document.id)).where(Document.company_id == user.company_id)) or 0
    values = payload.model_dump(exclude={"file_name", "file_data_url", "change_notes"})
    record = Document(company_id=user.company_id, document_no=f"DOC-{date.today().year}-{count + 1:05d}", created_by=user.id, **values)
    db.add(record); db.flush()
    path, mime, size, checksum = save_document_file(payload.file_data_url, record.id, 1, payload.file_name)
    db.add(DocumentVersion(company_id=user.company_id, document_id=record.id, version_no=1, file_name=payload.file_name, file_path=path, mime_type=mime, file_size=size, checksum_sha256=checksum, change_notes=payload.change_notes, uploaded_by=user.id, created_by=user.id))
    audit(db, request, user, "upload", "document", record.id, record.document_no, after={"title": record.title, "version": 1, "checksum": checksum}); db.commit()
    return db.scalar(document_query().where(Document.id == record.id))


@router.post("/documents/{document_id}/versions", response_model=DocumentOut)
def add_document_version(document_id: str, payload: DocumentVersionCreate, request: Request, user: User = Depends(require_permission("documents.manage")), db: Session = Depends(get_db)):
    record = db.scalar(document_query().where(Document.id == document_id, Document.company_id == user.company_id, Document.deleted_at.is_(None)))
    if not record: raise HTTPException(status_code=404, detail="Documento não encontrado")
    version = record.current_version + 1; path, mime, size, checksum = save_document_file(payload.file_data_url, record.id, version, payload.file_name)
    db.add(DocumentVersion(company_id=user.company_id, document_id=record.id, version_no=version, file_name=payload.file_name, file_path=path, mime_type=mime, file_size=size, checksum_sha256=checksum, change_notes=payload.change_notes, uploaded_by=user.id, created_by=user.id))
    record.current_version = version; record.approval_status = "pending"; record.updated_by = user.id
    audit(db, request, user, "version", "document", record.id, record.document_no, before={"version": version - 1}, after={"version": version, "checksum": checksum}); db.commit()
    return db.scalar(document_query().where(Document.id == record.id))


@router.patch("/documents/{document_id}", response_model=DocumentOut)
def update_document(document_id: str, payload: DocumentUpdate, request: Request, user: User = Depends(require_permission("documents.manage")), db: Session = Depends(get_db)):
    record = db.scalar(document_query().where(Document.id == document_id, Document.company_id == user.company_id, Document.deleted_at.is_(None)))
    if not record: raise HTTPException(status_code=404, detail="Documento não encontrado")
    before = {"title": record.title, "category": record.category, "valid_until": record.valid_until, "status": record.status}
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(record, field, value)
    if changes:
        record.approval_status = "pending"
        record.updated_by = user.id
    audit(db, request, user, "update", "document", record.id, record.document_no, before=before, after=changes); db.commit()
    return db.scalar(document_query().where(Document.id == record.id))


@router.post("/documents/{document_id}/approve", response_model=DocumentOut)
def approve_document(document_id: str, request: Request, user: User = Depends(require_permission("documents.manage")), db: Session = Depends(get_db)):
    record = db.scalar(document_query().where(Document.id == document_id, Document.company_id == user.company_id, Document.deleted_at.is_(None)))
    if not record: raise HTTPException(status_code=404, detail="Documento não encontrado")
    before = record.approval_status; record.approval_status = "approved"; record.approved_by = user.id; record.approved_at = datetime.now(timezone.utc)
    audit(db, request, user, "approve", "document", record.id, record.document_no, before={"status": before}, after={"status": "approved"}); db.commit()
    return record


@router.post("/documents/{document_id}/review", response_model=DocumentOut)
def review_document(document_id: str, payload: DocumentReview, request: Request, user: User = Depends(require_permission("documents.manage")), db: Session = Depends(get_db)):
    record = db.scalar(document_query().where(Document.id == document_id, Document.company_id == user.company_id, Document.deleted_at.is_(None)))
    if not record: raise HTTPException(status_code=404, detail="Documento não encontrado")
    before = record.approval_status
    record.approval_status = "approved" if payload.action == "approve" else "rejected"
    record.approved_by = user.id if payload.action == "approve" else None
    record.approved_at = datetime.now(timezone.utc) if payload.action == "approve" else None
    record.updated_by = user.id
    audit(db, request, user, payload.action, "document", record.id, record.document_no, before={"status": before}, after={"status": record.approval_status, "notes": payload.notes}); db.commit()
    return record


@router.get("/documents/{document_id}/download")
def download_document(document_id: str, version: int | None = None, user: User = Depends(require_permission("documents.view")), db: Session = Depends(get_db)):
    record = db.scalar(document_query().where(Document.id == document_id, Document.deleted_at.is_(None))); scope = portal_client_id(db, user)
    if not record or (user.account_type == "external" and (record.client_id != scope or record.approval_status != "approved")) or (user.account_type != "external" and record.company_id != user.company_id): raise HTTPException(status_code=404, detail="Documento não encontrado")
    number = version or record.current_version; item = next((entry for entry in record.versions if entry.version_no == number), None)
    if not item or not Path(item.file_path).exists(): raise HTTPException(status_code=404, detail="Versão do documento não encontrada")
    return FileResponse(item.file_path, media_type=item.mime_type, filename=item.file_name)


@router.get("/audit/summary", response_model=AuditSummary)
def audit_summary(user: User = Depends(require_permission("audit.view")), db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    actions = db.execute(select(AuditLog.action, func.count(AuditLog.id)).where(AuditLog.company_id == user.company_id).group_by(AuditLog.action)).all()
    return AuditSummary(
        total_events=db.scalar(select(func.count(AuditLog.id)).where(AuditLog.company_id == user.company_id)) or 0,
        events_today=db.scalar(select(func.count(AuditLog.id)).where(AuditLog.company_id == user.company_id, AuditLog.created_at >= today)) or 0,
        active_users=db.scalar(select(func.count(func.distinct(AuditLog.user_id))).where(AuditLog.company_id == user.company_id)) or 0,
        sensitive_actions=db.scalar(select(func.count(AuditLog.id)).where(AuditLog.company_id == user.company_id, AuditLog.action.in_(["approve", "payment", "delete", "transfer"]))) or 0,
        by_action=[{"name": name, "value": value} for name, value in actions],
    )


@router.get("/audit/logs", response_model=list[AuditLogOut])
def list_audit_logs(action: str | None = None, entity_type: str | None = None, user: User = Depends(require_permission("audit.view")), db: Session = Depends(get_db)):
    query = select(AuditLog).options(selectinload(AuditLog.user)).where(AuditLog.company_id == user.company_id)
    if action: query = query.where(AuditLog.action == action)
    if entity_type: query = query.where(AuditLog.entity_type == entity_type)
    records = db.scalars(query.order_by(AuditLog.created_at.desc()).limit(500)).all(); result = []
    for record in records:
        item = AuditLogOut.model_validate(record); item.user_name = record.user.full_name if record.user else "Sistema"; result.append(item)
    return result
