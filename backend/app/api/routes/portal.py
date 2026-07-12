import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.api.routes.management import invoice_out, invoice_query, receipt_out, receipt_query
from app.database.session import get_db
from app.models import (
    AuditLog, Certificate, Client, ClientServiceRequest, Document, Equipment,
    Invoice, Receipt, User,
)
from app.pdf.financial import generate_invoice_pdf, generate_receipt_pdf
from app.schemas.management import DocumentOut, InvoiceOut, ReceiptOut
from app.schemas.system import PortalBilling, PortalOverview, ServiceRequestCreate, ServiceRequestOut, ServiceRequestUpdate


router = APIRouter(prefix="/portal", tags=["Portal do Cliente"])


def portal_client(db: Session, user: User) -> Client:
    if user.account_type != "external":
        raise HTTPException(status_code=403, detail="Este recurso pertence ao portal externo")
    client = db.scalar(select(Client).where(
        Client.portal_company_id == user.company_id, Client.deleted_at.is_(None), Client.status == "active"
    ))
    if not client:
        raise HTTPException(status_code=404, detail="Empresa cliente não associada ao portal")
    return client


def service_request_query():
    return select(ClientServiceRequest).options(
        selectinload(ClientServiceRequest.client),
        selectinload(ClientServiceRequest.equipment).selectinload(Equipment.client),
        selectinload(ClientServiceRequest.equipment).selectinload(Equipment.type),
    )


def audit(db: Session, request: Request, user: User, action: str, record: ClientServiceRequest, description: str) -> None:
    db.add(AuditLog(
        company_id=record.company_id,
        user_id=user.id,
        action=action,
        entity_type="client_service_request",
        entity_id=record.id,
        entity_label=record.request_no,
        after_data=json.dumps({"status": record.status, "priority": record.priority}, ensure_ascii=False),
        ip_address=request.client.host if request.client else None,
        machine_name=(request.headers.get("x-machine-name") or request.headers.get("user-agent") or "")[:160],
        description=description,
        created_by=user.id,
    ))


@router.get("/overview", response_model=PortalOverview)
def overview(user: User = Depends(require_permission("client_portal.view")), db: Session = Depends(get_db)):
    client = portal_client(db, user)
    invoices = list(db.scalars(invoice_query().where(Invoice.client_id == client.id, Invoice.deleted_at.is_(None))))
    open_invoices = [invoice_out(item) for item in invoices if item.status not in {"paid", "cancelled"}]
    expiry_limit = date.today() + timedelta(days=60)
    latest = list(db.scalars(service_request_query().where(
        ClientServiceRequest.client_id == client.id, ClientServiceRequest.deleted_at.is_(None)
    ).order_by(ClientServiceRequest.created_at.desc()).limit(5)))
    return PortalOverview(
        client_name=client.name,
        equipment_total=db.scalar(select(func.count(Equipment.id)).where(Equipment.client_id == client.id, Equipment.deleted_at.is_(None))) or 0,
        certificates_valid=db.scalar(select(func.count(Certificate.id)).where(Certificate.client_id == client.id, Certificate.status == "issued", Certificate.expires_at >= date.today(), Certificate.deleted_at.is_(None))) or 0,
        certificates_expiring=db.scalar(select(func.count(Certificate.id)).where(Certificate.client_id == client.id, Certificate.status == "issued", Certificate.expires_at.between(date.today(), expiry_limit), Certificate.deleted_at.is_(None))) or 0,
        invoices_open=len(open_invoices),
        amount_due=sum(float(item.balance_due) for item in open_invoices),
        documents_available=db.scalar(select(func.count(Document.id)).where(Document.client_id == client.id, Document.approval_status == "approved", Document.deleted_at.is_(None))) or 0,
        requests_open=db.scalar(select(func.count(ClientServiceRequest.id)).where(ClientServiceRequest.client_id == client.id, ClientServiceRequest.status.in_(["submitted", "reviewing", "scheduled"]), ClientServiceRequest.deleted_at.is_(None))) or 0,
        latest_requests=latest,
    )


@router.get("/requests", response_model=list[ServiceRequestOut])
def list_requests(user: User = Depends(require_permission("client_portal.view")), db: Session = Depends(get_db)):
    client = portal_client(db, user)
    return list(db.scalars(service_request_query().where(
        ClientServiceRequest.client_id == client.id, ClientServiceRequest.deleted_at.is_(None)
    ).order_by(ClientServiceRequest.created_at.desc())))


@router.post("/requests", response_model=ServiceRequestOut, status_code=201)
def create_request(payload: ServiceRequestCreate, request: Request,
                   user: User = Depends(require_permission("client_portal.view")), db: Session = Depends(get_db)):
    client = portal_client(db, user)
    equipment = None
    if payload.equipment_id:
        equipment = db.scalar(select(Equipment).where(
            Equipment.id == payload.equipment_id, Equipment.client_id == client.id, Equipment.deleted_at.is_(None)
        ))
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado na sua empresa")
    sequence = (db.scalar(select(func.count(ClientServiceRequest.id)).where(ClientServiceRequest.company_id == client.company_id)) or 0) + 1
    record = ClientServiceRequest(
        company_id=client.company_id,
        client_id=client.id,
        equipment_id=equipment.id if equipment else None,
        request_no=f"FNL-SRV-{date.today().year}-{sequence:04d}",
        service_type=payload.service_type,
        requested_date=date.today(),
        preferred_date=payload.preferred_date,
        location=payload.location,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        priority=payload.priority,
        notes=payload.notes,
        status="submitted",
        created_by=user.id,
    )
    db.add(record)
    db.flush()
    audit(db, request, user, "create", record, "Solicitação submetida pelo portal do cliente")
    db.commit()
    return db.scalar(service_request_query().where(ClientServiceRequest.id == record.id))


@router.get("/billing", response_model=PortalBilling)
def billing(user: User = Depends(require_permission("client_portal.view")), db: Session = Depends(get_db)):
    client = portal_client(db, user)
    invoices = list(db.scalars(invoice_query().where(Invoice.client_id == client.id, Invoice.deleted_at.is_(None)).order_by(Invoice.issue_date.desc())))
    receipts = list(db.scalars(receipt_query().where(Receipt.client_id == client.id, Receipt.deleted_at.is_(None)).order_by(Receipt.issued_at.desc())))
    return PortalBilling(invoices=[invoice_out(item) for item in invoices], receipts=[receipt_out(item) for item in receipts])


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: str, user: User = Depends(require_permission("client_portal.view")), db: Session = Depends(get_db)):
    client = portal_client(db, user)
    record = db.scalar(invoice_query().where(Invoice.id == invoice_id, Invoice.client_id == client.id, Invoice.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    path = generate_invoice_pdf(record)
    if record.pdf_path != str(path):
        record.pdf_path = str(path)
        db.commit()
    return FileResponse(path, filename=f"{record.invoice_no}.pdf", media_type="application/pdf")


@router.get("/receipts/{receipt_id}/pdf")
def receipt_pdf(receipt_id: str, user: User = Depends(require_permission("client_portal.view")), db: Session = Depends(get_db)):
    client = portal_client(db, user)
    record = db.scalar(receipt_query().where(Receipt.id == receipt_id, Receipt.client_id == client.id, Receipt.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Recibo não encontrado")
    path = generate_receipt_pdf(record)
    if record.pdf_path != str(path):
        record.pdf_path = str(path)
        db.commit()
    return FileResponse(path, filename=f"{record.receipt_no}.pdf", media_type="application/pdf")


@router.get("/requests-admin", response_model=list[ServiceRequestOut])
def list_all_requests(user: User = Depends(require_permission("inspections.view")), db: Session = Depends(get_db)):
    if user.account_type == "external":
        raise HTTPException(status_code=403, detail="Acesso reservado aos colaboradores")
    return list(db.scalars(service_request_query().where(
        ClientServiceRequest.company_id == user.company_id, ClientServiceRequest.deleted_at.is_(None)
    ).order_by(ClientServiceRequest.created_at.desc())))


@router.patch("/requests-admin/{request_id}", response_model=ServiceRequestOut)
def update_request(request_id: str, payload: ServiceRequestUpdate, request: Request,
                   user: User = Depends(require_permission("inspections.manage")), db: Session = Depends(get_db)):
    if user.account_type == "external":
        raise HTTPException(status_code=403, detail="Acesso reservado aos colaboradores")
    record = db.scalar(service_request_query().where(
        ClientServiceRequest.id == request_id, ClientServiceRequest.company_id == user.company_id,
        ClientServiceRequest.deleted_at.is_(None),
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    record.status = payload.status
    record.response_notes = payload.response_notes
    record.handled_by = user.id
    record.handled_at = datetime.now(timezone.utc)
    record.updated_by = user.id
    audit(db, request, user, "update", record, "Solicitação atualizada pela equipa FNLIFTING")
    db.commit()
    return db.scalar(service_request_query().where(ClientServiceRequest.id == record.id))
