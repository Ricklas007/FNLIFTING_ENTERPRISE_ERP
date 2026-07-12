# Implantação

## Desenvolvimento local

Use `scripts/setup.ps1` uma vez e `scripts/start-dev.ps1` nos arranques seguintes.

## Produção local sem Docker

```powershell
copy backend\.env.production.example backend\.env
# edite SECRET_KEY, CORS_ORIGINS e ALLOWED_HOSTS

.\scripts\setup.ps1
.\scripts\migrate.ps1
.\scripts\prod-preflight.ps1
.\scripts\start-prod.ps1
```

O script `start-prod.ps1` define `ENVIRONMENT=production`, `DEBUG=false`, `AUTO_CREATE_SCHEMA=false`, aplica migrações por defeito e cria o build do frontend apontando para o backend local.

## Produção com Docker Compose

```powershell
copy .env.production.example .env
# edite SECRET_KEY obrigatoriamente

docker compose up --build -d
docker compose ps
docker compose logs -f backend
```

O frontend fica em `http://localhost:8080` por defeito. O volume `fnlifting_data` preserva SQLite, backups, certificados, documentos, PDFs financeiros e assinaturas.

## Readiness e monitorização

- `/health`: resposta simples do serviço;
- `/ready`: readiness operacional; devolve `503` se houver falhas críticas;
- `/api/v1/system/ops/readiness`: checklist detalhado protegido por `settings.manage`;
- `scripts\prod-preflight.ps1`: valida backend, readiness, testes e build antes da entrega.

## Checklist para produção real

- `SECRET_KEY` aleatória e guardada fora do repositório;
- `DEBUG=false`;
- `AUTO_CREATE_SCHEMA=false` e migrações aplicadas;
- CORS limitado ao domínio real;
- `ALLOWED_HOSTS` com domínios/IPs reais;
- TLS no proxy reverso;
- troca de todas as contas demo;
- backups cifrados e restauro testado;
- monitorização de `/ready`;
- política de atualização para certificados, assinaturas e documentos;
- plano futuro para PostgreSQL remoto, MFA, rate limiting e observabilidade.

