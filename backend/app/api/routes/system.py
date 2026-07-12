import io
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import SessionLocal, get_db
from app.models import AuditLog, BackupRecord, SyncQueue, SyncRun, SystemSetting, User
from app.ops.readiness import build_readiness_report
from app.reports.advanced import build_report, export_csv, export_pdf, export_xlsx
from app.schemas.auth import MessageResponse
from app.schemas.system import (
    AdvancedReport, BackupCreate, BackupOut, BackupRestore, ConflictResolve,
    SettingOut, SettingUpdate, SyncQueueOut, SyncRunOut, SyncRunRequest, SyncSummary,
)
from app.sync.backup import backup_path, create_backup, inspect_backup, restore_backup
from app.sync.service import resolve_conflict, run_sync, sync_summary


router = APIRouter(prefix="/system", tags=["Backup, Sync, Relatórios e Configurações"])


def _audit(db: Session, request: Request, user: User, action: str, entity_type: str, entity_id: str | None,
           label: str | None, description: str, after: dict | None = None) -> None:
    db.add(AuditLog(
        company_id=user.company_id,
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=label,
        after_data=json.dumps(after, ensure_ascii=False, default=str) if after else None,
        ip_address=request.client.host if request.client else None,
        machine_name=(request.headers.get("x-machine-name") or request.headers.get("user-agent") or "")[:160],
        description=description,
        created_by=user.id,
    ))


@router.get("/sync/summary", response_model=SyncSummary)
def get_sync_summary(user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    return sync_summary(db, user.company_id)


@router.get("/sync/queue", response_model=list[SyncQueueOut])
def get_sync_queue(
    status: str | None = Query(default=None, pattern="^(pending|synced|conflict|failed)$"),
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(require_permission("sync.manage")),
    db: Session = Depends(get_db),
):
    query = select(SyncQueue).where(SyncQueue.company_id == user.company_id, SyncQueue.deleted_at.is_(None))
    if status:
        query = query.where(SyncQueue.status == status)
    return list(db.scalars(query.order_by(SyncQueue.queued_at.desc()).limit(limit)))


@router.get("/sync/runs", response_model=list[SyncRunOut])
def get_sync_runs(user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    return list(db.scalars(select(SyncRun).where(
        SyncRun.company_id == user.company_id, SyncRun.deleted_at.is_(None)
    ).order_by(SyncRun.started_at.desc()).limit(30)))


@router.post("/sync/run", response_model=SyncRunOut)
def synchronize(payload: SyncRunRequest, request: Request, user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    run = run_sync(db, user.company_id, user.id, payload.limit)
    _audit(db, request, user, "sync", "sync_run", run.id, "Sincronização manual", "Fila local processada", {"processed": run.pushed_count, "failed": run.failed_count})
    db.commit()
    db.refresh(run)
    return run


@router.post("/sync/conflicts/{entry_id}/resolve", response_model=SyncQueueOut)
def resolve_sync_conflict(entry_id: str, payload: ConflictResolve, request: Request,
                          user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    entry = db.scalar(select(SyncQueue).where(
        SyncQueue.id == entry_id, SyncQueue.company_id == user.company_id,
        SyncQueue.status == "conflict", SyncQueue.deleted_at.is_(None),
    ))
    if not entry:
        raise HTTPException(status_code=404, detail="Conflito de sincronização não encontrado")
    resolve_conflict(db, entry, payload.strategy, payload.merged_payload, user.id)
    _audit(db, request, user, "resolve", "sync_queue", entry.id, entry.entity_type, f"Conflito resolvido com estratégia {payload.strategy}")
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/backups", response_model=list[BackupOut])
def list_backups(user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    return list(db.scalars(select(BackupRecord).where(
        BackupRecord.company_id == user.company_id, BackupRecord.deleted_at.is_(None)
    ).order_by(BackupRecord.created_at.desc())))


@router.post("/backups", response_model=BackupOut, status_code=201)
def create_encrypted_backup(payload: BackupCreate, request: Request,
                            user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    try:
        record = create_backup(db, user.company_id, user.id, payload.password, payload.include_files, payload.notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(record)
    _audit(db, request, user, "backup", "backup", record.id, record.backup_no, "Backup cifrado criado", {"includes_files": payload.include_files})
    db.commit()
    db.refresh(record)
    return record


@router.get("/backups/{backup_id}/download")
def download_backup(backup_id: str, user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    record = db.scalar(select(BackupRecord).where(
        BackupRecord.id == backup_id, BackupRecord.company_id == user.company_id, BackupRecord.deleted_at.is_(None)
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Backup não encontrado")
    try:
        path = backup_path(record)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FileResponse(path, filename=record.file_name, media_type="application/octet-stream")


@router.post("/backups/{backup_id}/verify")
def verify_backup(backup_id: str, payload: BackupRestore,
                  user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    record = db.scalar(select(BackupRecord).where(
        BackupRecord.id == backup_id, BackupRecord.company_id == user.company_id, BackupRecord.deleted_at.is_(None)
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Backup não encontrado")
    try:
        manifest = inspect_backup(record, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"valid": True, "manifest": manifest}


@router.post("/backups/{backup_id}/restore", response_model=MessageResponse)
def restore_encrypted_backup(backup_id: str, payload: BackupRestore, request: Request,
                             user: User = Depends(require_permission("sync.manage")), db: Session = Depends(get_db)):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirme explicitamente o restauro da base de dados")
    record = db.scalar(select(BackupRecord).where(
        BackupRecord.id == backup_id, BackupRecord.company_id == user.company_id, BackupRecord.deleted_at.is_(None)
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Backup não encontrado")
    try:
        inspect_backup(record, payload.password)
        record_id, backup_no = record.id, record.backup_no
        db.close()
        result = restore_backup(record, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with SessionLocal() as restored_db:
        restored_record = restored_db.get(BackupRecord, record_id)
        if restored_record:
            restored_record.restored_at = datetime.now(timezone.utc)
            restored_record.restored_by = user.id
        _audit(restored_db, request, user, "restore", "backup", record_id, backup_no, "Base local restaurada a partir de backup cifrado", result)
        restored_db.commit()
    return MessageResponse(message=f"Backup {backup_no} restaurado com sucesso. Reinicie o backend para renovar todas as ligações.")


@router.get("/settings", response_model=list[SettingOut])
def list_settings(user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    return list(db.scalars(select(SystemSetting).where(
        SystemSetting.company_id == user.company_id, SystemSetting.deleted_at.is_(None)
    ).order_by(SystemSetting.category, SystemSetting.label)))


@router.patch("/settings/{setting_id}", response_model=SettingOut)
def update_setting(setting_id: str, payload: SettingUpdate, request: Request,
                   user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    record = db.scalar(select(SystemSetting).where(
        SystemSetting.id == setting_id, SystemSetting.company_id == user.company_id, SystemSetting.deleted_at.is_(None)
    ))
    if not record:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    if record.value_type == "boolean" and payload.value.lower() not in {"true", "false"}:
        raise HTTPException(status_code=422, detail="Valor booleano inválido")
    if record.value_type == "integer":
        try:
            int(payload.value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Valor inteiro inválido") from exc
    before = record.value
    record.value = payload.value
    record.updated_by = user.id
    _audit(db, request, user, "update", "setting", record.id, record.label, "Configuração atualizada", {"before": "***" if record.is_secret else before, "after": "***" if record.is_secret else payload.value})
    db.commit()
    db.refresh(record)
    return record


@router.get("/ops/readiness")
def operational_readiness(user: User = Depends(require_permission("settings.manage"))):
    return build_readiness_report()


@router.get("/reports/advanced", response_model=AdvancedReport)
def advanced_report(
    report_type: str = Query(default="executive", pattern="^(executive|financial|operations|hr|fleet|assets)$"),
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=180)),
    date_to: date = Query(default_factory=date.today),
    client_id: str | None = None,
    department_id: str | None = None,
    user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
):
    if date_from > date_to or (date_to - date_from).days > 730:
        raise HTTPException(status_code=422, detail="Intervalo inválido; utilize no máximo dois anos")
    return build_report(db, user.company_id, report_type, date_from, date_to, client_id, department_id)


@router.get("/reports/export")
def export_advanced_report(
    format: str = Query(pattern="^(pdf|xlsx|csv)$"),
    report_type: str = Query(default="executive", pattern="^(executive|financial|operations|hr|fleet|assets)$"),
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=180)),
    date_to: date = Query(default_factory=date.today),
    client_id: str | None = None,
    department_id: str | None = None,
    user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
):
    if date_from > date_to or (date_to - date_from).days > 730:
        raise HTTPException(status_code=422, detail="Intervalo inválido; utilize no máximo dois anos")
    report = build_report(db, user.company_id, report_type, date_from, date_to, client_id, department_id)
    exporters = {
        "pdf": (export_pdf, "application/pdf"),
        "xlsx": (export_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "csv": (export_csv, "text/csv; charset=utf-8"),
    }
    exporter, media_type = exporters[format]
    content = exporter(report)
    filename = f"FNL-{report_type}-{date_from}-{date_to}.{format}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
