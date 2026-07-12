# CI/CD — FNLIFTING Enterprise ERP

## Pipeline local

```powershell
cd C:\Projetos\FNLIFTING_ENTERPRISE_ERP\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest

cd C:\Projetos\FNLIFTING_ENTERPRISE_ERP\frontend
npm run build
```

## Deploy

`docker-compose.yml` inicia backend FastAPI, aplica `alembic upgrade head`, serve frontend Nginx e usa volume persistente `fnlifting_data`.

Para produção, definir `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `ALLOWED_HOSTS` e opcionalmente `SYNC_REMOTE_URL`.
