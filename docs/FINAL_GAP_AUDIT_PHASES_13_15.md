# Final gap audit — Fases 13, 14 e 15

Data: 2026-09-03
Estado: fechamento funcional/hardening executado com validações locais. Não é declaração de release pública final.

## Resumo executivo

Esta auditoria fecha lacunas internas das Fases 13–15 sem repetir fases anteriores e sem alterar a versão `0.12.1`.

Resultado local atual:

- Backend: `59 passed, 664 warnings` em `backend\.venv\Scripts\python.exe -m pytest tests -q`.
- Frontend lint: `npm run lint` passou sem erros e sem avisos.
- Frontend build: `npm run build` passou; permaneceu apenas o aviso Vite de chunk acima de 500 kB.
- Alembic: `current=head=20260830_0007`.
- Preflight core: `ready`, `OK=11`, `Avisos=1`, `Falhas=0`.
- Release readiness: `Failures=0`, `Warnings=2`.
- Browser audit: parcial. Login e mapa real foram observados, mas a automação do browser ficou instável com timeouts de attach/CDP; não declarar E2E visual completo.

## Ponto retomado

| Item | Resultado |
|---|---|
| Última etapa concluída antes da retomada | Testes novos de gap closure já existiam e o build frontend anterior já tinha passado. |
| Ponto exato da interrupção | Limpeza de `frontend/src/pages/OperationsPages.tsx`: bloco legado duplicado de certificados ainda estava no EOF e gerava imports/avisos. |
| Correção aplicada | Removido bloco legado `LegacyCertificatesPage`, corrigidos imports, separada autenticação/hook para resolver Fast Refresh, estabilizados hooks com `useCallback`. |
| Validação posterior | Lint sem avisos, build frontend, Alembic, pytest completo, preflight core e readiness. |

## Classificação final por requisito

Legenda: `VALIDATED`, `IMPLEMENTED_NOT_VALIDATED`, `SIMULATED_VALIDATED`, `PROVIDER_READY`, `BLOCKED_EXTERNAL`, `BROKEN`, `MISSING`.

| Área | Requisito | Estado | Evidência |
|---|---|---:|---|
| Estrutura/estado | Não reiniciar projeto, não repetir fases, preservar alterações | `VALIDATED` | Trabalho aplicado sobre árvore existente; nenhum reset/descarte Git executado. |
| Segurança de segredos | Não expor chaves no output/documentação | `VALIDATED` | Docs e respostas não incluem valores de API keys; readiness apenas informa configuração/estado. |
| Migrações | Nova tabela para anexos/media rastreáveis | `VALIDATED` | `backend/alembic/versions/20260830_0007_media_attachments.py`; Alembic `current=head=20260830_0007`. |
| Perfis completos | Trabalhador com anexos/fotos/documentos associados | `VALIDATED` | `test_worker_full_profile.py`, `test_media_workflows.py`, `MediaAttachmentPanel` em `EmployeesPage`. |
| Perfis completos | Equipamento com anexos/fotos/documentos associados | `VALIDATED` | `test_equipment_full_profile.py`, `test_media_workflows.py`, `MediaAttachmentPanel` em `EquipmentPage`. |
| Perfis completos | Património/asset com anexos/fotos/documentos associados | `VALIDATED` | `test_asset_full_profile.py`, `test_media_workflows.py`, `MediaAttachmentPanel` em `AssetsPage`. |
| Frota | Camiões com anexos/fotos/documentos associados | `VALIDATED` | `test_attachment_sync.py`, `MediaAttachmentPanel` em `FleetPage`. |
| Gestão documental | Upload, versionamento, edição, preview, download, aprovação e rejeição | `VALIDATED` | `test_document_lifecycle.py`; UI em `DocumentsPage` inclui `Ver`, `Baixar`, `Editar`, `Nova versão`, `Aprovar`, `Rejeitar`. |
| Certificados | Criação de rascunho, edição, emissão, download PDF, validação pública | `VALIDATED` | `test_certificate_lifecycle.py`, `test_public_certificate_validation.py`; UI em `CertificatePages.tsx`. |
| Certificados | Preview dentro do sistema antes de download/revisão | `VALIDATED` | `api.previewCertificate`, iframe `.document-preview-frame`, `test_certificate_lifecycle.py`. Browser visual direto ficou parcial por instabilidade do runtime. |
| Certificados | Gestão de inspetores com assinatura e carimbo próprios | `VALIDATED` | `SignatoryManager`, `TechnicalSignatory`, emissão bloqueia ausência de assinatura/carimbo; coberto por lifecycle tests. |
| Certificados | Igualdade visual exata ao PDF exemplar enviado | `IMPLEMENTED_NOT_VALIDATED` | Há geração com template oficial, carimbos e assinaturas; não foi executado diff visual pixel/perceptual contra o PDF exemplar nesta retomada. |
| RBAC/portal | Staff/admin/client/worker portal com restrições | `VALIDATED` | `test_customer_portal_full_workflow.py`, `test_worker_portal_full_workflow.py`, `test_tenant_isolation.py`; correção em `hr_enterprise.py` permite trabalhador com `daily_reports.submit`. |
| Dashboard/topbar | Pesquisa global, notificações reais, menu de perfil e suporte | `IMPLEMENTED_NOT_VALIDATED` | Código implementado em `DashboardLayout.tsx`; browser search ficou ambígua por instabilidade do runtime. Backend notificações passa em `test_notifications.py`. |
| Import/export | Relatórios, GeoJSON GPS, backups, validação de backup | `VALIDATED` | `test_import_export_jobs.py`, `test_attachment_sync.py`. |
| Automação/IA | Providers, OCR job, regras, sugestões e revisão | `VALIDATED` | `test_ai_ocr_rules.py`, `test_automation_engine.py`. |
| Payroll/RH enterprise | Assiduidade/licenças/payroll/portal do trabalhador | `VALIDATED` | `test_payroll.py`, `test_payroll_full_workflow.py`, `test_hr_workflows.py`, `test_worker_portal_full_workflow.py`. |
| Financeiro | Receitas, despesas, aprovação, faturas, pagamentos, recibos | `VALIDATED` | `test_finance_full_workflow.py`; UI em `FinancePage`. |
| Cliente/portal | Cliente externo com equipamentos, certificados, solicitações e faturação | `VALIDATED` | `test_customer_portal.py`, `test_customer_portal_full_workflow.py`. |
| Storage | Local storage + abstração MinIO/S3 compatível | `VALIDATED` | `test_storage_provider.py`, `test_minio_storage.py`; Docker MinIO real bloqueado por ambiente. |
| PostgreSQL | Compatibilidade SQL/DSN e preparação | `VALIDATED` | `test_postgresql_compatibility.py`; runtime Docker/PostgreSQL real não executado. |
| Docker cloud | Compose PostgreSQL/MinIO/staging runtime | `BLOCKED_EXTERNAL` | `docker` não está disponível no PATH; readiness avisa `Docker CLI not available`. |
| SerpApi | Pesquisa operacional real de locais | `BLOCKED_EXTERNAL` | Key configurada, mas readiness não autentica provider; manter como não validado até teste live autenticado sem `AUTH_ERROR`. |
| Google Maps | Provider/renderer com key configurada | `PROVIDER_READY` | Variável configurada fora da documentação; MapLibre/CARTO/OSM continua fallback funcional. |
| Mapa real | MapLibre/CARTO/OSM renderizado com marcadores GPS | `VALIDATED` | Browser parcial observou tela `Viagens & GPS` com MapLibre, marcadores e painel de viagens; `test_maps_runtime.py` e `test_real_map_package.py` passam. |
| Pacote Angola offline | Importar/validar/ativar MBTiles/PMTiles | `SIMULATED_VALIDATED` | `test_real_map_package.py` valida pacote gerado em teste; pacote cartográfico real/licenciado de Angola ainda precisa ser fornecido. |
| GPS/Traccar | Pipeline, replay, geofences, alertas, provider health | `SIMULATED_VALIDATED` | `test_traccar_pipeline.py`, `test_gps_geofences_replay.py`, `test_gps_pilot_acceptance.py`; dispositivo físico e servidor Traccar real não executados. |
| Android/mobile | Artefatos e aceitação em dispositivo/emulador | `BLOCKED_EXTERNAL` | Conforme docs anteriores, APK debug existe em relatórios; AAB assinado e device/emulator acceptance permanecem fora do ambiente desta retomada. |
| Browser E2E visual | Navegar por todos os módulos e abrir modais via browser | `BLOCKED_EXTERNAL` | Runtime do navegador interno falhou com timeouts attach/CDP; artefato em `.runtime/final-gap-browser-audit/browser-audit-summary.md`. |

## Correções implementadas nesta retomada

### Backend

- Adicionado modelo `MediaAttachment` com metadata, checksum, caminho, thumbnail, status e usuário de upload.
- Adicionada migration `20260830_0007_media_attachments`.
- Adicionados endpoints JSON/base64 para anexos de entidades em `management.py`:
  - listar anexos por entidade;
  - criar anexo;
  - download;
  - thumbnail;
  - arquivamento lógico.
- Corrigido portal do trabalhador para permitir acesso por `hr.view` ou `daily_reports.submit`.
- Adicionados helpers de testes para entidades demo reutilizáveis.
- Corrigido `test_runtime_paths.py` para validar `SIGNATURE_DIR` pela fonte leve `app.core.config`, evitando import pesado de rotas no subprocesso.

### Frontend

- Criado `MediaAttachmentPanel` reutilizável.
- Integrado painel de anexos em trabalhador, equipamento, património e camião.
- Adicionadas APIs frontend de media attachment.
- Separado `AuthProvider`, `AuthContext` e `useAuth` para remover warning Fast Refresh.
- Movido `hasPermission` para `frontend/src/lib/permissions.ts`.
- Separados formatters de componentes em `frontend/src/features/enterprise/formatters.ts`.
- Corrigidos hooks com `useCallback`.
- Removida página legada duplicada de certificados de `OperationsPages.tsx`.
- Implementada topbar funcional com pesquisa global, notificações reais, perfil/logout e suporte.

### Scripts/gates

- Adicionado lock global `.runtime/fnlifting-gate.lock` a:
  - `scripts/prod-preflight.ps1`;
  - `scripts/release-readiness.ps1`.
- Motivo: impedir execução concorrente de gates que usam o mesmo SQLite e provocavam `database is locked`.

## Evidência de validação

| Comando | Resultado |
|---|---|
| `npm run lint` em `frontend` | Passou sem erros/avisos. |
| `npm run build` em `frontend` | Passou; aviso Vite de chunk grande permanece. |
| `backend\.venv\Scripts\python.exe -m pytest tests\test_runtime_paths.py -q` | `1 passed in 2.28s`. |
| `backend\.venv\Scripts\python.exe -m pytest tests -q` | `59 passed, 664 warnings in 775.70s`. |
| `backend\.venv\Scripts\python.exe -m alembic current` | `20260830_0007 (head)`. |
| `backend\.venv\Scripts\python.exe -m alembic heads` | `20260830_0007 (head)`. |
| `scripts\prod-preflight.ps1 -SkipTests -SkipFrontendBuild` | `ready`, `OK=11`, `Avisos=1`, `Falhas=0`. |
| `scripts\release-readiness.ps1 -SkipTests -SkipFrontendBuild -BackendPort 8000` | `Failures=0`, `Warnings=2`. |

## Avisos e bloqueios que permanecem

| Bloqueio | Estado | Próxima ação necessária |
|---|---:|---|
| Backup recente | `IMPLEMENTED_NOT_VALIDATED` | Criar backup pelo sistema; preflight informou último backup com mais de 24h. |
| Docker/PostgreSQL/MinIO/staging runtime | `BLOCKED_EXTERNAL` | Instalar/abrir Docker Desktop e repetir readiness sem skip de testes Docker. |
| SerpApi live | `BLOCKED_EXTERNAL` | Executar teste autenticado do provider com key válida e registrar se retornou `CONNECTED` ou `AUTH_ERROR`. |
| Pacote real Angola offline | `BLOCKED_EXTERNAL` | Fornecer PMTiles/MBTiles licenciado/real de Angola e repetir import/activate. |
| GPS físico/Traccar real | `BLOCKED_EXTERNAL` | Conectar dispositivo/servidor real e executar piloto com dados reais. |
| Android AAB assinado/device acceptance | `BLOCKED_EXTERNAL` | Configurar signing keystore e executar em dispositivo/emulador. |
| Browser E2E completo | `BLOCKED_EXTERNAL` | Repetir quando o runtime do browser/headless estiver estável; não usar como gate verde nesta sessão. |

## Conclusão

As lacunas funcionais locais principais foram implementadas e validadas por testes/backend, lint/build frontend, Alembic, preflight core e release readiness.

As Fases 13–15 não devem ser declaradas como release final completo enquanto os bloqueios externos acima não forem resolvidos com evidência real.
