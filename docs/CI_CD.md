# CI/CD — FNLIFTING Enterprise ERP

## Pipeline local

```powershell
cd C:\Projetos\FNLIFTING_ENTERPRISE_ERP\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe tools\preflight.py --json

cd C:\Projetos\FNLIFTING_ENTERPRISE_ERP\frontend
npm.cmd run lint
npm.cmd run build
```

## Pipeline GitHub Actions

`.github/workflows/ci.yml` executa:

- backend SQLite: install, Alembic upgrade/current/heads, seed, pytest e preflight;
- backend PostgreSQL: serviço `postgres:16-alpine`, migrations, seed e testes críticos de sync/tenant/certificados;
- frontend: `npm ci`, lint e build;
- segurança/compose: scan simples de segredos e `docker compose config` base + staging.

## Staging cloud-ready

```powershell
copy .env.staging.example .env.staging
docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging.yml up --build
```

Com observabilidade:

```powershell
docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.observability.yml --profile observability up --build
```

## Produção

`docker-compose.production.yml` exige variáveis reais via ambiente/secret manager:

- `SECRET_KEY`;
- `BACKUP_ENCRYPTION_KEY`;
- `DATABASE_URL` PostgreSQL;
- `CORS_ORIGINS`;
- `ALLOWED_HOSTS`;
- `STORAGE_BUCKET`;
- `STORAGE_ACCESS_KEY_ID`;
- `STORAGE_SECRET_ACCESS_KEY`.

Não versionar `.env.staging`, `.env.production`, credenciais reais, dumps PostgreSQL, buckets MinIO/S3, logs ou artefactos de release.
