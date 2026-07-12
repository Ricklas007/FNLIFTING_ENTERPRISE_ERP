# Fase 7 — Produção, hardening e operação

A Fase 7 transforma a base local-first das Fases 1–6 num pacote mais preparado para instalação real: migrações, readiness checks, Docker, scripts operacionais e configuração segura por ambiente.

## Entregas principais

- endpoint público `/ready` para healthcheck de orquestradores;
- endpoint protegido `/api/v1/system/ops/readiness` para administradores com `settings.manage`;
- painel frontend **Produção & Saúde** com OK, avisos, falhas e recomendações;
- cabeçalhos de segurança HTTP no backend;
- `TrustedHostMiddleware` em produção através de `ALLOWED_HOSTS`;
- configuração `AUTO_CREATE_SCHEMA=false` para produção com migrações Alembic;
- baseline Alembic em `backend/alembic`;
- `Dockerfile` para backend FastAPI;
- `Dockerfile` + Nginx para frontend React;
- `docker-compose.yml` com volume persistente para a base SQLite;
- scripts Windows:
  - `scripts\migrate.ps1`
  - `scripts\prod-preflight.ps1`
  - `scripts\start-prod.ps1`
- exemplos `.env` para backend, frontend e Docker Compose.

## Fluxo recomendado sem Docker

```powershell
copy backend\.env.production.example backend\.env
# edite SECRET_KEY, CORS_ORIGINS e ALLOWED_HOSTS

.\scripts\setup.ps1
.\scripts\migrate.ps1
.\scripts\prod-preflight.ps1
.\scripts\start-prod.ps1
```

## Fluxo recomendado com Docker

```powershell
copy .env.production.example .env
# edite SECRET_KEY obrigatoriamente

docker compose up --build -d
docker compose logs -f backend
```

O frontend fica por defeito em `http://localhost:8080`; o Nginx encaminha `/api`, `/health` e `/ready` para o backend.

## Readiness

O checklist valida:

- força da `SECRET_KEY`;
- `DEBUG=false` em produção;
- CORS e hosts permitidos;
- ligação à base de dados;
- tabelas esperadas pelo SQLAlchemy;
- presença de `alembic_version`;
- permissões de escrita em `backend/data`;
- existência de empresas/utilizadores;
- backup cifrado recente;
- conflitos/falhas na fila de sincronização.

Falhas bloqueiam `/ready` com HTTP `503`. Avisos continuam visíveis no painel, mas não impedem readiness.

## Variáveis novas

| Variável | Uso |
|---|---|
| `APP_VERSION` | versão exposta na API e readiness |
| `ALLOWED_HOSTS` | hosts aceites em produção |
| `AUTO_CREATE_SCHEMA` | cria tabelas automaticamente em desenvolvimento; use `false` em produção |
| `SECURITY_HEADERS_ENABLED` | ativa cabeçalhos básicos de proteção |
| `BACKUP_WARNING_HOURS` | idade máxima recomendada para backup pronto |

## Nota operacional

O baseline Alembic foi criado para a estrutura atual das Fases 1–7. Em bases já existentes, `alembic upgrade head` marca a versão sem recriar tabelas existentes; em bases novas, cria todo o schema inicial.

