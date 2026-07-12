from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import (
    Asset, Certificate, Client, DailyReport, Employee, Equipment, Expense,
    Inspection, Revenue, Trip, Truck, User,
)
from app.schemas.dashboard import DashboardResponse


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def count(db: Session, model, *filters) -> int:
    return db.scalar(select(func.count(model.id)).where(model.deleted_at.is_(None), *filters)) or 0


def money(value: Decimal | float | None) -> str:
    amount = float(value or 0)
    if amount >= 1_000_000:
        return f"Kz {amount / 1_000_000:.1f}M"
    return f"Kz {amount:,.0f}".replace(",", ".")


@router.get("/overview", response_model=DashboardResponse)
def overview(
    user: User = Depends(require_permission("dashboard.view")),
    db: Session = Depends(get_db),
):
    today = date.today()
    if user.account_type == "external":
        client = db.scalar(select(Client).where(Client.portal_company_id == user.company_id))
        client_id = client.id if client else "missing"
        certificates = count(db, Certificate, Certificate.client_id == client_id)
        equipment = count(db, Equipment, Equipment.client_id == client_id)
        expiring = count(
            db, Certificate, Certificate.client_id == client_id,
            Certificate.expires_at.between(today, today + timedelta(days=45)),
        )
        metrics = [
            {"key":"certificates","label":"Meus certificados","value":certificates,"display_value":str(certificates),"change":"Documentos emitidos","trend":"up","icon":"badge-check"},
            {"key":"equipment","label":"Equipamentos inspecionados","value":equipment,"display_value":str(equipment),"change":"No seu portal","trend":"up","icon":"package-check"},
            {"key":"expiring","label":"A vencer em 45 dias","value":expiring,"display_value":str(expiring),"change":"Requer atenção","trend":"warning","icon":"clock-alert"},
            {"key":"requests","label":"Pedidos em análise","value":2,"display_value":"2","change":"Última atualização hoje","trend":"neutral","icon":"clipboard-list"},
        ]
        return DashboardResponse(
            scope="client",
            greeting=f"Bem-vindo ao Portal do Cliente, {user.full_name.split()[0]}",
            metrics=metrics,
            finance_chart=[],
            operations_chart=[{"label":"Jan","inspections":1},{"label":"Fev","inspections":2},{"label":"Mar","inspections":1},{"label":"Abr","inspections":3},{"label":"Mai","inspections":2},{"label":"Jun","inspections":1}],
            alerts=[{"id":"ext-1","title":"Certificado próximo da validade","detail":"Verifique os documentos que vencem nos próximos 45 dias.","level":"warning","time":"Hoje"}],
            activities=[{"id":"ext-a1","title":"Certificado disponibilizado","detail":"FNL-CTE-2026-005 está disponível no portal","time":"Há 2 horas","type":"certificate"}],
            pending_approvals=0,
        )

    company_id = user.company_id
    revenue_total = db.scalar(select(func.sum(Revenue.amount)).where(Revenue.company_id == company_id)) or 0
    expense_total = db.scalar(select(func.sum(Expense.amount)).where(Expense.company_id == company_id)) or 0
    metrics = [
        {"key":"employees","label":"Trabalhadores ativos","value":count(db,Employee,Employee.company_id==company_id,Employee.status=="active"),"display_value":str(count(db,Employee,Employee.company_id==company_id,Employee.status=="active")),"change":"+2 este mês","trend":"up","icon":"users"},
        {"key":"reports","label":"Relatórios pendentes","value":count(db,DailyReport,DailyReport.company_id==company_id,DailyReport.status=="pending"),"display_value":str(count(db,DailyReport,DailyReport.company_id==company_id,DailyReport.status=="pending")),"change":"Requer revisão","trend":"warning","icon":"file-clock"},
        {"key":"inspections","label":"Inspeções hoje","value":count(db,Inspection,Inspection.company_id==company_id,Inspection.inspection_date==today),"display_value":str(count(db,Inspection,Inspection.company_id==company_id,Inspection.inspection_date==today)),"change":"3 concluídas","trend":"up","icon":"scan-search"},
        {"key":"certificates","label":"Certificados emitidos","value":count(db,Certificate,Certificate.company_id==company_id),"display_value":str(count(db,Certificate,Certificate.company_id==company_id)),"change":"+12% no período","trend":"up","icon":"badge-check"},
        {"key":"trips","label":"Camiões em rota","value":count(db,Trip,Trip.company_id==company_id,Trip.status=="in_progress"),"display_value":str(count(db,Trip,Trip.company_id==company_id,Trip.status=="in_progress")),"change":"GPS operacional","trend":"up","icon":"truck"},
        {"key":"revenue","label":"Receita acumulada","value":float(revenue_total),"display_value":money(revenue_total),"change":"+18,4% vs. anterior","trend":"up","icon":"trending-up"},
        {"key":"expenses","label":"Despesas acumuladas","value":float(expense_total),"display_value":money(expense_total),"change":"6 aguardam aprovação","trend":"warning","icon":"wallet-cards"},
        {"key":"assets","label":"Património ativo","value":count(db,Asset,Asset.company_id==company_id),"display_value":str(count(db,Asset,Asset.company_id==company_id)),"change":"Inventário atualizado","trend":"neutral","icon":"landmark"},
    ]
    finance = [
        {"label":"Jan","revenue":4.2,"expense":2.4},{"label":"Fev","revenue":4.8,"expense":2.7},
        {"label":"Mar","revenue":5.3,"expense":3.1},{"label":"Abr","revenue":4.9,"expense":2.8},
        {"label":"Mai","revenue":6.2,"expense":3.4},{"label":"Jun","revenue":7.1,"expense":3.8},
    ]
    operations = [
        {"label":"Jan","inspections":18},{"label":"Fev","inspections":24},{"label":"Mar","inspections":21},
        {"label":"Abr","inspections":32},{"label":"Mai","inspections":29},{"label":"Jun","inspections":38},
    ]
    return DashboardResponse(
        scope="enterprise",
        greeting=f"Bom trabalho, {user.full_name.split()[0]}",
        metrics=metrics,
        finance_chart=finance,
        operations_chart=operations,
        alerts=[
            {"id":"a1","title":"3 certificados próximos da validade","detail":"Vencem nos próximos 30 dias","level":"warning","time":"Há 12 min"},
            {"id":"a2","title":"Camião LD-45-67 sem sinal GPS","detail":"Última posição há 38 minutos","level":"critical","time":"Há 38 min"},
            {"id":"a3","title":"6 despesas aguardam aprovação","detail":"Valor total de Kz 1.240.000","level":"info","time":"Há 1 h"},
        ],
        activities=[
            {"id":"at1","title":"Certificado emitido","detail":"FNL-CTE-2026-005 · Sonangol EP","time":"Há 18 min","type":"certificate"},
            {"id":"at2","title":"Inspeção concluída","detail":"Guindaste Liebherr LTM 1100","time":"Há 44 min","type":"inspection"},
            {"id":"at3","title":"Viagem iniciada","detail":"TRP-2026-005 · Luanda → Benguela","time":"Há 1 h","type":"trip"},
            {"id":"at4","title":"Relatório diário recebido","detail":"António Manuel · Operações","time":"Há 2 h","type":"report"},
        ],
        pending_approvals=count(db, User, User.company_id == company_id, User.status == "pending"),
    )

