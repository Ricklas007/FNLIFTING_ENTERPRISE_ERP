# API REST

Base local: `http://127.0.0.1:8000/api/v1`. Documentação interativa: `/docs`.

## Endpoints da Fase 1

| Método | Endpoint | Acesso | Descrição |
|---|---|---|---|
| `GET` | `/health` | Público | Estado do serviço |
| `GET` | `/ready` | Público | Readiness de produção; devolve `503` quando há falhas críticas |
| `POST` | `/api/v1/auth/login` | Público | Login por email/utilizador e portal |
| `POST` | `/api/v1/auth/register` | Público | Pedido de conta pendente |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT | Renovação da sessão |
| `POST` | `/api/v1/auth/logout` | Autenticado | Revoga a sessão |
| `GET` | `/api/v1/auth/me` | Autenticado | Identidade, empresa, perfis e permissões |
| `POST` | `/api/v1/auth/forgot-password` | Público | Regista pedido local de recuperação |
| `GET` | `/api/v1/dashboard/overview` | `dashboard.view` | Dashboard isolado por âmbito |
| `GET` | `/api/v1/admin/users` | `users.manage` | Lista de utilizadores |
| `POST` | `/api/v1/admin/users/{id}/approve` | `users.approve` | Aprova conta e atribui perfil |

## Recursos Humanos — Fase 2

| Método | Endpoint | Permissão | Descrição |
|---|---|---|---|
| `GET` | `/api/v1/hr/summary` | `hr.view` | Indicadores e ranking de RH |
| `GET/POST` | `/api/v1/hr/departments` | `departments.view/manage` | Lista e cria departamentos |
| `PATCH/DELETE` | `/api/v1/hr/departments/{id}` | `departments.manage` | Atualiza ou remove departamento vazio |
| `GET/POST` | `/api/v1/hr/employees` | `employees.view/manage` | Pesquisa e cria trabalhadores |
| `GET` | `/api/v1/hr/employees/me` | `daily_reports.submit` | Cadastro associado à conta autenticada |
| `GET/PATCH/DELETE` | `/api/v1/hr/employees/{id}` | `employees.view/manage` | Detalhe, atualização e arquivo lógico |
| `GET/POST` | `/api/v1/hr/daily-reports` | `daily_reports.view/submit` | Lista filtrada e submissão de relatório |
| `PATCH` | `/api/v1/hr/daily-reports/{id}` | `daily_reports.submit` | Corrige relatório permitido |
| `POST` | `/api/v1/hr/daily-reports/{id}/review` | `daily_reports.review` | Aprova ou solicita correção |
| `GET/POST` | `/api/v1/hr/performance` | `performance.view/manage` | Ranking e nova avaliação mensal |

Utilizadores sem permissão de revisão veem apenas os próprios relatórios, através da associação segura `users ↔ employees`.

## Operações técnicas — Fase 3

| Método | Endpoint | Permissão | Descrição |
|---|---|---|---|
| `GET` | `/api/v1/operations/summary` | `clients.view` | Indicadores de clientes, equipamentos, inspeções e certificados |
| `GET/POST` | `/api/v1/operations/clients` | `clients.view/manage` | Pesquisa e criação de clientes empresariais |
| `PATCH/DELETE` | `/api/v1/operations/clients/{id}` | `clients.manage` | Atualiza ou arquiva cliente sem equipamento associado |
| `GET` | `/api/v1/operations/equipment-types` | `equipment.view` | Tipos e modelo de checklist técnico |
| `GET/POST` | `/api/v1/operations/equipment` | `equipment.view/manage` | Inventário técnico com isolamento por empresa |
| `PATCH/DELETE` | `/api/v1/operations/equipment/{id}` | `equipment.manage` | Atualiza ou arquiva equipamento |
| `GET/POST` | `/api/v1/operations/inspections` | `inspections.view/manage` | Lista e regista inspeção com checklist |
| `PATCH` | `/api/v1/operations/inspections/{id}` | `inspections.manage` | Atualiza resultado e conclusão técnica |
| `GET/POST` | `/api/v1/operations/certificates` | `certificates.view/manage` | Lista certificados ou cria rascunho de inspeção aprovada |
| `PATCH` | `/api/v1/operations/certificates/{id}` | `certificates.manage` | Edita metadados de certificado em rascunho |
| `POST` | `/api/v1/operations/certificates/{id}/issue` | `certificates.manage` | Emite certificado e gera PDF com QR |
| `GET` | `/api/v1/operations/certificates/{id}/pdf` | `certificates.view` | Pré-visualiza/descarrega PDF; rascunhos só para utilizadores internos |
| `GET` | `/api/v1/public/certificates/{qr_token}` | Público | Confirma autenticidade e validade do certificado |
| `GET/POST` | `/api/v1/operations/signatories` | `certificates.view/manage` | Lista ou regista inspetores/supervisores autorizados |
| `PATCH` | `/api/v1/operations/signatories/{id}` | `certificates.manage` | Atualiza qualificações, assinatura, carimbo e competências |

O portal externo recebe apenas equipamentos e certificados associados ao seu `client.portal_company_id`. Inspeções reprovadas, com defeito ou com qualquer item não conforme não podem originar certificado.

## Frota, viagens e GPS — Fase 4

| Método | Endpoint | Permissão | Descrição |
|---|---|---|---|
| `GET` | `/api/v1/fleet/summary` | `fleet.view` | Indicadores de motoristas, camiões, viagens, GPS e incidentes |
| `GET/POST` | `/api/v1/fleet/drivers` | `fleet.view/manage` | Lista e cria motoristas |
| `PATCH/DELETE` | `/api/v1/fleet/drivers/{id}` | `fleet.manage` | Atualiza ou arquiva motorista sem viagens |
| `GET/POST` | `/api/v1/fleet/trucks` | `fleet.view/manage` | Lista e cria camiões |
| `PATCH/DELETE` | `/api/v1/fleet/trucks/{id}` | `fleet.manage` | Atualiza ou arquiva camião sem viagens |
| `GET/POST` | `/api/v1/fleet/trips` | `fleet.view/manage` | Lista e planeia viagens |
| `PATCH` | `/api/v1/fleet/trips/{id}` | `fleet.manage` | Atualiza estado, chegada e atribuições |
| `GET` | `/api/v1/fleet/gps/live` | `fleet.view` | Última posição conhecida por camião |
| `GET` | `/api/v1/fleet/gps/trips/{id}` | `fleet.view` | Timeline GPS de uma viagem |
| `POST` | `/api/v1/fleet/gps/positions` | `fleet.manage` | Recebe latitude, longitude, velocidade, direção e combustível |
| `GET/POST` | `/api/v1/fleet/gps/devices` | `fleet.view/manage` | Lista ou regista trackers GPS com token próprio |
| `POST` | `/api/v1/fleet/gps/devices/{id}/rotate-token` | `fleet.manage` | Roda token de dispositivo GPS |
| `POST` | `/api/v1/fleet/gps/ingest` | `X-GPS-Device-Token` | Ingestão GPS segura sem login humano |
| `GET` | `/api/v1/fleet/gps/history` | `fleet.view` | Histórico filtrado e paginado de posições |
| `GET` | `/api/v1/fleet/gps/replay` | `fleet.view` | Replay de rota por camião ou viagem |
| `GET` | `/api/v1/fleet/gps/export.geojson` | `fleet.view` | Exporta rota e pontos em GeoJSON |
| `GET` | `/api/v1/fleet/gps/stream` | `fleet.view` | Snapshot SSE para atualizações de mapa |
| `GET/POST` | `/api/v1/fleet/geofences` | `fleet.view/manage` | Lista ou cria geofences reais |
| `PATCH` | `/api/v1/fleet/geofences/{id}` | `fleet.manage` | Atualiza geofence |
| `GET/POST` | `/api/v1/fleet/alert-rules` | `fleet.view/manage` | Lista ou cria regras de alerta |
| `GET` | `/api/v1/fleet/alerts` | `fleet.view` | Lista alertas deduplicados |
| `POST` | `/api/v1/fleet/alerts/{id}/resolve` | `fleet.manage` | Resolve alerta de frota |
| `GET` | `/api/v1/fleet/fuel-records` | `fleet.view` | Registos de abastecimento |
| `GET` | `/api/v1/fleet/incidents` | `fleet.view` | Incidentes operacionais |

## Gestão empresarial — Fase 5

| Método | Endpoint | Permissão | Descrição |
|---|---|---|---|
| `GET` | `/api/v1/management/assets/summary` | `assets.view` | Indicadores de património e manutenção |
| `GET/POST` | `/api/v1/management/assets` | `assets.view/manage` | Lista ou regista bens patrimoniais |
| `PATCH` | `/api/v1/management/assets/{id}` | `assets.manage` | Atualiza valor, localização, responsável e estado |
| `GET/POST` | `/api/v1/management/assets/{id}/maintenance` | `assets.view/manage` | Histórico e registo de manutenção |
| `POST` | `/api/v1/management/assets/{id}/transfers` | `assets.manage` | Transfere o bem com histórico permanente |
| `GET` | `/api/v1/management/finance/summary` | `finance.view` | Receitas, despesas, resultado, contas a receber e fluxo |
| `GET/POST` | `/api/v1/management/finance/expenses` | `finance.view/manage` | Lista ou regista despesas |
| `POST` | `/api/v1/management/finance/expenses/{id}/approve` | `finance.manage` | Aprova uma despesa pendente |
| `GET/POST` | `/api/v1/management/finance/revenues` | `finance.view/manage` | Lista ou regista receitas |
| `GET/POST` | `/api/v1/management/finance/invoices` | `finance.view/manage` | Lista ou emite faturas com itens e IVA |
| `POST` | `/api/v1/management/finance/invoices/{id}/payments` | `finance.manage` | Regista pagamento e emite recibo automático |
| `GET` | `/api/v1/management/finance/invoices/{id}/pdf` | `finance.view` | Descarrega a fatura em PDF |
| `GET` | `/api/v1/management/finance/receipts` | `finance.view` | Lista recibos emitidos |
| `GET` | `/api/v1/management/finance/receipts/{id}/pdf` | `finance.view` | Descarrega o recibo em PDF |
| `GET/POST` | `/api/v1/management/documents` | `documents.view/manage` | Pesquisa ou envia documentos |
| `PATCH` | `/api/v1/management/documents/{id}` | `documents.manage` | Edita metadados e devolve o documento à revisão |
| `POST` | `/api/v1/management/documents/{id}/versions` | `documents.manage` | Adiciona uma versão com checksum |
| `POST` | `/api/v1/management/documents/{id}/approve` | `documents.manage` | Aprova a versão corrente |
| `POST` | `/api/v1/management/documents/{id}/review` | `documents.manage` | Aprova ou rejeita formalmente o documento |
| `GET` | `/api/v1/management/documents/{id}/download` | `documents.view` | Descarrega a versão corrente autorizada |
| `GET` | `/api/v1/management/audit/summary` | `audit.view` | Indicadores do trilho de auditoria |
| `GET` | `/api/v1/management/audit/logs` | `audit.view` | Eventos com filtros, origem e antes/depois |

As mutações da Fase 5 gravam eventos de auditoria. Faturas e recibos são gerados localmente em PDF; documentos aceites são validados por tipo, limitados a 10 MB e preservados com SHA-256 e histórico de versões.

## Continuidade, portal e inteligência — Fase 6

| Método | Endpoint | Permissão | Descrição |
|---|---|---|---|
| `GET` | `/api/v1/system/sync/summary` | `sync.manage` | Estado da ligação e contagem da fila |
| `GET` | `/api/v1/system/sync/queue` | `sync.manage` | Alterações locais e conflitos |
| `GET` | `/api/v1/system/sync/runs` | `sync.manage` | Histórico de sincronizações |
| `POST` | `/api/v1/system/sync/run` | `sync.manage` | Processa um lote idempotente da fila |
| `POST` | `/api/v1/system/sync/conflicts/{id}/resolve` | `sync.manage` | Resolve conflito por versão local, remota ou mesclada |
| `GET/POST` | `/api/v1/system/backups` | `sync.manage` | Lista ou cria backup cifrado |
| `GET` | `/api/v1/system/backups/{id}/download` | `sync.manage` | Exporta o ficheiro `.fnlbak` |
| `POST` | `/api/v1/system/backups/{id}/verify` | `sync.manage` | Decifra e verifica manifesto/checksums |
| `POST` | `/api/v1/system/backups/{id}/restore` | `sync.manage` | Restaura base e ficheiros após confirmação |
| `GET` | `/api/v1/system/reports/advanced` | `reports.view` | Consolida indicadores e séries por período |
| `GET` | `/api/v1/system/reports/export` | `reports.view` | Exporta `pdf`, `xlsx` ou `csv` |
| `GET/PATCH` | `/api/v1/system/settings` | `settings.manage` | Consulta e atualiza políticas empresariais |
| `GET` | `/api/v1/system/ops/readiness` | `settings.manage` | Checklist operacional detalhado da Fase 7 |
| `GET` | `/api/v1/portal/overview` | `client_portal.view` | Resumo isolado da empresa cliente |
| `GET/POST` | `/api/v1/portal/requests` | `client_portal.view` | Lista ou submete solicitação de serviço |
| `GET` | `/api/v1/portal/billing` | `client_portal.view` | Faturas e recibos do próprio cliente |
| `GET` | `/api/v1/portal/invoices/{id}/pdf` | `client_portal.view` | Fatura PDF isolada por tenant |
| `GET` | `/api/v1/portal/receipts/{id}/pdf` | `client_portal.view` | Recibo PDF isolado por tenant |
| `GET/PATCH` | `/api/v1/portal/requests-admin` | `inspections.view/manage` | Tratamento interno das solicitações |

Toda mutação ORM cria uma entrada em `sync_queue` dentro da mesma transação. O modo sem servidor remoto gera checkpoints locais; `SYNC_REMOTE_URL` reserva o transporte para a implantação PostgreSQL/cloud.

## Produção e operação — Fase 7

`/ready` é destinado a Docker, balanceadores e monitores: só falhas críticas devolvem HTTP `503`. O painel autenticado `/api/v1/system/ops/readiness` expõe os detalhes para administradores, incluindo recomendações de correção para segredo JWT, debug, CORS, hosts permitidos, schema, migrações, backups e fila de sincronização.

## Login

```json
{
  "identifier": "admin@fnlifting.com",
  "password": "Admin@12345",
  "portal": "staff",
  "remember_me": false
}
```

Use `Authorization: Bearer <access_token>` nos endpoints protegidos. Um cliente externo deve usar `portal: "client"`; a API rejeita a mesma conta no portal de colaboradores.
