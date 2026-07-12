# FNLIFTING Enterprise Management System

> Estado atual: versão `0.12.0` local-first com Fases 1–12, incluindo MFA, sync 2.0 local/cloud-ready, fleet command center, IA/OCR local, RH enterprise/payroll, BI, compliance e preparação SaaS.

Documentação enterprise:

- `docs/PHASE_8_CLOUD_SECURITY.md`
- `docs/PHASE_9_FLEET_GPS.md`
- `docs/PHASE_10_AI_AUTOMATION.md`
- `docs/PHASE_11_HR_ENTERPRISE.md`
- `docs/PHASE_12_EXECUTIVE_SAAS.md`
- `docs/GAP_AUDIT_PHASES_8_12.md`
- `docs/BROWSER_VALIDATION_PHASES_8_12.md`
- `docs/CI_CD.md`
- `docs/SAAS_READY.md`
- `docs/SECURITY_ENTERPRISE.md`

Base local-first do ERP da **FNLIFTING ANGOLA**, construída com FastAPI, React, TypeScript e SQLite. As Fases 1–7 entregam identidade empresarial, dashboard, Recursos Humanos, inspeção/certificação, frota com GPS, património, finanças, documentos, auditoria, portal externo, relatórios avançados, backup cifrado, sincronização e preparação para produção.

## Arranque rápido (Windows / PowerShell)

Pré-requisitos: Python 3.11+ e Node.js 20+.

```powershell
.\scripts\setup.ps1
.\scripts\start-dev.ps1
```

Depois abra [http://localhost:5173](http://localhost:5173). A API fica em [http://localhost:8000/docs](http://localhost:8000/docs).

Para iniciar manualmente em dois terminais:

```powershell
# Terminal 1
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm run dev
```

## Contas de demonstração

| Perfil | Portal | Utilizador | Palavra-passe |
|---|---|---|---|
| Administrador | Colaborador FNL | `admin@fnlifting.com` | `Admin@12345` |
| Recursos Humanos | Colaborador FNL | `rh@fnlifting.com` | `RH@12345` |
| Inspetor | Colaborador FNL | `inspetor@fnlifting.com` | `Inspetor@12345` |
| Motorista | Colaborador FNL | `motorista@fnlifting.com` | `Motorista@12345` |
| Técnico | Colaborador FNL | `tecnico@fnlifting.com` | `Tecnico@12345` |
| Cliente Sonangol | Empresa cliente | `cliente@sonangol.co.ao` | `Cliente@12345` |

> As credenciais são exclusivamente de demonstração. Troque a `SECRET_KEY` e todas as palavras-passe antes de qualquer implantação.

O backup inicial de demonstração usa a palavra-passe `DemoBackup@2026`. Crie backups próprios com uma palavra-passe privada antes de usar dados reais.

## Módulos entregues

- sequência visual logotipo → preparação local → login;
- login por email ou nome de utilizador, com portais separados para colaboradores e clientes;
- pedidos de conta pendentes de aprovação;
- hash de palavra-passe PBKDF2-SHA256, JWT HS256, sessões revogáveis e histórico de login;
- RBAC com 15 perfis e 35 permissões granulares;
- isolamento multiempresa no portal de cliente;
- dashboard conectado à API, responsivo, com métricas, gráficos, alertas e atividade;
- SQLite local e configuração pronta para PostgreSQL;
- UUID, timestamps, soft delete, autoria e estado de sincronização nas entidades;
- seed com trabalhadores, clientes, equipamentos, inspeções, certificados, frota, viagens, finanças e património;
- OpenAPI/Swagger automático e testes de integração.
- centro de Recursos Humanos com indicadores por departamento;
- CRUD de departamentos e trabalhadores, contratos e contactos;
- relatórios diários com submissão, filtros, aprovação e pedido de correção;
- avaliações de desempenho com score automático, ranking e isolamento por perfil;
- navegação filtrada pelas permissões efetivas do utilizador.
- gestão multiempresa de clientes e inventário técnico de equipamentos;
- tipos de equipamento com modelos de checklist reutilizáveis;
- inspeções técnicas com responsável, resultado, defeitos, recomendações e próxima data;
- certificados emitidos apenas a partir de inspeções aprovadas;
- PDF técnico com identidade FNLIFTING, checklist, aprovação digital e QR de autenticidade;
- portal externo isolado para consulta dos equipamentos e certificados da própria empresa.
- certificado oficial inspirado no exemplar FNLIFTING, com tabela WLL/SWL, códigos A–E, norma, dupla assinatura, carimbos e QR;
- perfis técnicos de inspetores e supervisores com qualificações, assinatura e carimbo próprios;
- cadastro funcional de motoristas e camiões-cisterna, documentos e alertas de validade;
- viagens, carga, cliente, estados operacionais, incidentes e posições GPS;
- mapa local responsivo com última posição, velocidade, combustível e fallback sem internet.
- património empresarial com valores, depreciação, localização, responsável, manutenções e transferências;
- centro financeiro com despesas, receitas, faturas, pagamentos, recibos e PDFs automáticos;
- gestão documental com upload local, checksum SHA-256, versões, validade, aprovação e acesso controlado;
- trilho de auditoria com utilizador, máquina/IP, ação e valores antes/depois;
- dados de demonstração completos para todos os fluxos da Fase 5.
- portal do cliente isolado por empresa, com solicitações de serviço, equipamentos, certificados, documentos, faturas e recibos;
- relatórios executivos, financeiros, operacionais, RH, frota e património, exportáveis em PDF, Excel e CSV;
- fila automática de sincronização com estados pendente, sincronizado, conflito e falha;
- centro Backup & Sync com processamento manual, resolução de conflitos e histórico;
- backup integral cifrado por PBKDF2/Fernet, verificação SHA-256, exportação e restauro controlado;
- configurações empresariais persistentes para backup, sincronização, finanças, relatórios e segurança.
- readiness público em `/ready` e painel protegido Produção & Saúde;
- migrações Alembic com baseline das Fases 1–7;
- Dockerfiles para backend/frontend e `docker-compose.yml` com volume persistente;
- scripts de produção para preflight, migração e arranque local;
- hardening de cabeçalhos HTTP, hosts permitidos e configuração por ambiente.

## Estrutura

```text
backend/   FastAPI, SQLAlchemy, autenticação, RBAC, modelos, seed e testes
frontend/  React, TypeScript, TailwindCSS, Lucide e Recharts
docs/      arquitetura, API, base de dados, sync e implantação
scripts/   instalação e arranque local
```

Consulte [docs/API.md](docs/API.md), [docs/DATABASE.md](docs/DATABASE.md), [docs/PHASE_3_OPERATIONS.md](docs/PHASE_3_OPERATIONS.md), [docs/PHASE_4_FLEET.md](docs/PHASE_4_FLEET.md), [docs/PHASE_5_MANAGEMENT.md](docs/PHASE_5_MANAGEMENT.md), [docs/PHASE_6_CONTINUITY.md](docs/PHASE_6_CONTINUITY.md), [docs/PHASE_7_PRODUCTION.md](docs/PHASE_7_PRODUCTION.md) e [docs/OFFLINE_SYNC.md](docs/OFFLINE_SYNC.md).
