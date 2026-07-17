# Auditoria de interações — FNLIFTING Enterprise ERP

Data: 2026-07-17  
Estado: inventário inicial obrigatório. Não substitui testes E2E completos.

| PÁGINA | LABEL | AÇÃO ESPERADA | PERMISSÃO | ENDPOINT | RESULTADO | TESTE | ESTADO |
|---|---|---|---|---|---|---|---|
| Login | Entrar no sistema | autenticar staff/client e criar sessão | pública | `POST /api/v1/auth/login` | funcional | auth tests | FUNCTIONAL_VALIDATED |
| Login | Validar e entrar | concluir MFA | pública/challenge | `POST /api/v1/auth/login/mfa` | funcional | parcial | FUNCTIONAL_NOT_VALIDATED |
| Dashboard | Atualizar | recarregar KPIs | autenticado | `/api/v1/dashboard/*` | funcional | auth/dashboard | FUNCTIONAL_VALIDATED |
| Frota · Camiões | Novo camião | abrir formulário e criar camião | `fleet.manage` | `/api/v1/fleet/trucks` | funcional base | parcial | FUNCTIONAL_NOT_VALIDATED |
| Frota · Motoristas | Novo motorista | abrir formulário e criar motorista | `fleet.manage` | `/api/v1/fleet/drivers` | funcional base | parcial | FUNCTIONAL_NOT_VALIDATED |
| Frota · Viagens & GPS | Nova viagem | abrir formulário de viagem | `fleet.manage` | `/api/v1/fleet/trips` | funcional base | parcial | PARTIAL |
| Frota · Viagens & GPS | Replay GPS | carregar rota histórica | `fleet.view` | `/api/v1/fleet/gps/replay` | funcional quando há pontos | `test_gps_geofences_replay.py` | FUNCTIONAL_VALIDATED |
| Frota · Viagens & GPS | Iniciar viagem | transicionar planned→in_progress | `fleet.manage` | `/api/v1/fleet/trips/{id}/status` | funcional base | parcial | PARTIAL |
| Frota · Viagens & GPS | Confirmar entrega | transicionar in_progress→delivered | `fleet.manage` | `/api/v1/fleet/trips/{id}/status` | funcional base | parcial | PARTIAL |
| Frota · Viagens & GPS | Resolver alerta | fechar alerta | `fleet.manage` | `/api/v1/fleet/alerts/{id}/resolve` | funcional | GPS tests | FUNCTIONAL_VALIDATED |
| Gestão de mapas | Importar pacote | copiar PMTiles/MBTiles para `userData/maps` | `fleet.manage` | `/api/v1/maps/packages/import` | funcional no backend; sem fixture real nesta sessão | pendente | FUNCTIONAL_NOT_VALIDATED |
| Gestão de mapas | Ativar pacote | definir pacote ativo | `fleet.manage` | `/api/v1/maps/packages/{id}/activate` | funcional | pendente | FUNCTIONAL_NOT_VALIDATED |
| Gestão de mapas | Remover pacote | apagar pacote importado | `fleet.manage` | `/api/v1/maps/packages/{id}` | funcional com confirmação | pendente | FUNCTIONAL_NOT_VALIDATED |
| Certificados | Inspetores e assinaturas | gerir signatários | certificados/manage | `/api/v1/operations/certificate-signatories` | funcional base | parcial | FUNCTIONAL_NOT_VALIDATED |
| Certificados | Novo certificado | criar rascunho a partir de inspeção aprovada | certificados/manage | `/api/v1/operations/certificates` | funcional base | tests parciais | FUNCTIONAL_NOT_VALIDATED |
| Certificados | Ver | pré-visualizar PDF dentro do sistema | certificados/view | PDF endpoint | funcional | visual pendente | FUNCTIONAL_NOT_VALIDATED |
| Certificados | Emitir | gerar PDF assinado/carimbado | certificados/issue | issue endpoint | funcional base | visual pendente | PARTIAL |
| Backup & Sync | Criar backup | gerar backup cifrado | admin | `/api/v1/system/backups` | funcional | preflight/parcial | FUNCTIONAL_NOT_VALIDATED |
| Backup & Sync | Sincronizar agora | executar sync local/cloud-ready | admin | sync endpoints | parcial | pendente Postgres | PARTIAL |
| RH Enterprise | Processar período | processar payroll | RH/payroll | `/api/v1/enterprise/hr/payroll/*` | funcional base | `test_hr_workflows.py` | FUNCTIONAL_VALIDATED |
| IA & Automação | Gerar sugestões | criar sugestões idempotentes | enterprise/ai | `/api/v1/enterprise/ai/assistant/generate` | funcional | `test_ai_ocr_rules.py` | FUNCTIONAL_VALIDATED |

## Bloqueadores de interação ainda existentes

- Pesquisa global no cabeçalho é visual e ainda não executa comando real.
- Google Maps provider não tem tela/health real.
- Integrações GPS físicas/Traccar ainda não têm wizard completo.
- Fotos/anexos em entidades ainda não têm fluxo universal.
- Browser acceptance real bloqueado pelo ambiente até existir browser/headless disponível.
