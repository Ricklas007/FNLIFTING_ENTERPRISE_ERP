# Fase 14 — Cloud/staging readiness

Data: 2026-08-02

## Estado

Classificação: `LOCAL_STAGING_VALIDATED` para configuração e código local.  
Classificação adicional: `PUBLIC_DEPLOYMENT_BLOCKED` até existir servidor, domínio, TLS público, credenciais PostgreSQL/S3 reais e política operacional aprovada.

## Componentes preparados

| Componente | Estado | Evidência |
|---|---|---|
| PostgreSQL | Configurado para staging/local | `docker-compose.yml` com serviço `postgres`; `docker-compose.staging.yml` força `DATABASE_URL` PostgreSQL |
| Object storage | Configurado para LOCAL/MINIO/S3 | `backend/app/storage/provider.py`; readiness `object_storage`; MinIO em compose |
| Backend | Cloud-ready | variáveis `DATA_DIR`, `STORAGE_*`, `/ready`, `/live`, `/metrics` |
| Frontend | Cloud-ready | `frontend/Dockerfile`; Vite build validado |
| Reverse proxy | Preparado | frontend Nginx serve SPA e proxy API conforme Dockerfile/config existente |
| Observabilidade | Preparada | `/metrics`; `docker-compose.observability.yml`; `monitoring/prometheus.yml` |
| CI/CD | Preparado | `.github/workflows/ci.yml` com SQLite, PostgreSQL, lint, build, secret scan e compose config |
| Segurança | Preparada | CORS/TrustedHost/security headers/readiness; segredos apenas via env |
| Backup/restore | SQLite validado; PostgreSQL documentado | backup local cifrado existente; PostgreSQL exige dump/restore no ambiente staging real |

## Como subir staging local

```powershell
copy .env.staging.example .env.staging
docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging.yml up --build
```

Opcionalmente com observabilidade:

```powershell
docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.observability.yml --profile observability up --build
```

## Validações executadas neste ambiente

- Backend tests completos: 36 passed.
- Frontend lint: 0 errors, 24 warnings legados.
- Frontend build: OK.
- Alembic current/head: `20260802_0006 (head)`.
- Preflight após storage: ready, 12 pass, 0 warnings, 0 failures, incluindo `object_storage`.
- `/ready`: ready validado em backend temporário antes desta subfase; deve ser repetido no gate final após commit.
- `release-readiness` atualizado: 0 failures, 2 warnings (`Docker CLI` ausente e SerpApi pendente de prova CONNECTED).
- YAML parse local com PyYAML: OK para `docker-compose.yml`, `docker-compose.staging.yml`, `docker-compose.production.yml`, `docker-compose.observability.yml`, `monitoring/prometheus.yml` e `.github/workflows/ci.yml`.
- Testes alvo storage/observabilidade: 4 passed.

## Bloqueios externos

- Docker CLI não estava disponível em verificações anteriores neste Windows; se continuar ausente, `docker compose config/up` fica `BLOCKED_EXTERNAL`.
- Nesta retentativa, `docker --version` e `docker compose version` continuam ausentes no PATH.
- Não há cloud pública, domínio, certificado TLS público, bucket S3 real nem PostgreSQL gerido configurados neste workspace.
- PostgreSQL em container deve ser validado num ambiente com Docker funcional antes de declarar produção.

## Próximas validações obrigatórias

- `docker compose -f docker-compose.yml config`
- `docker compose -f docker-compose.yml -f docker-compose.staging.yml config`
- `docker compose ... up --build`
- `alembic upgrade head` contra PostgreSQL
- `seed.py` contra PostgreSQL
- testes backend críticos contra PostgreSQL
- upload/download via `STORAGE_PROVIDER=MINIO`
- backup/restore PostgreSQL e MinIO
- `/metrics` raspado pelo Prometheus
