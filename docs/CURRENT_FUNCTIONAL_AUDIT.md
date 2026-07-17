# Auditoria funcional atual — FNLIFTING Enterprise ERP

Data: 2026-07-17  
Escopo: recuperação após o build interno `0.12.1`, sem gerar novo instalador.

## Estado de recuperação

| Item | Evidência |
|---|---|
| Branch | `main` |
| Último commit antes desta auditoria | `6ee1804 chore: prepare portable android sdk build` |
| Worktree inicial | limpo |
| Remote | não configurado |
| Regra de release | empacotamento congelado até `scripts/release-readiness.ps1` passar |

## Classificação por módulo

| MÓDULO | PÁGINA | AÇÃO/BOTÃO | ENDPOINT | BANCO | PERMISSÃO | WORKFLOW | TESTE | ESTADO | EVIDÊNCIA | AÇÃO CORRETIVA |
|---|---|---|---|---|---|---|---|---|---|---|
| Mapas/GIS | Frota · GPS | Mapa principal | `GET /api/v1/maps/status`, tiles MBTiles/PMTiles | `userData/maps/manifest.json` | `fleet.view` | online/offline/auto | build frontend | PARTIAL | antes existia fallback abstrato `angola-map`; agora componente operacional aponta para `features/maps/components/GisFleetMap.tsx` | validar com pacote real Angola PMTiles/MBTiles e provider online contratado |
| Mapas/GIS | Gestor de mapas | Importar/ativar/remover pacote | `/api/v1/maps/packages/*` | `userData/maps/packages` | `fleet.manage` | importação segura por path local backend | pendente E2E | FUNCTIONAL_NOT_VALIDATED | backend valida extensão/checksum e não lê path arbitrário do frontend diretamente | criar teste com MBTiles/PMTiles fixture |
| Mapas/GIS | Google online | Provider externo | n/d | n/d | admin/settings | provider opcional | pendente | MISSING | sem API key real; não pode ser declarado funcional | criar página de configuração e health quando houver key |
| GPS físico | Integrações GPS | Device token HTTP | `/api/v1/fleet/gps/devices`, `/ingest` | tabelas fleet tracking | `fleet.manage`/token dispositivo | ingestão segura normalizada | `test_gps_geofences_replay.py` | FUNCTIONAL_VALIDATED | token de dispositivo separado de login humano | expandir para Traccar/MQTT/HTTP vendor |
| GPS físico | Traccar | Testar conexão/importar devices | n/d | n/d | `fleet.manage` | provider-ready | pendente | MISSING | não há `TRACCAR_URL`/credenciais reais nem adapter | implementar adapter registry e página Integrações GPS |
| Frota | Viagens & GPS | Criar viagem/iniciar/entregar/replay | `/api/v1/fleet/*`, `/api/v1/fleet/gps/replay` | SQLite | `fleet.manage`, `fleet.view` | parcial | backend tests | PARTIAL | status básico existe; checklist e bloqueios críticos ainda não estão completos | implementar workflow completo DRAFT→CLOSED |
| Geofences | Viagens & GPS | Listar/alertar/resolver | `/api/v1/fleet/geofences`, `/alerts` | SQLite | `fleet.view/manage` | ENTER/EXIT parcial | backend tests | PARTIAL | geofences são renderizadas no mapa real quando há provider | criar editor no mapa e regras por veículo/cliente/horário |
| Documentos | Certificados | Preview/PDF/emitir | `/api/v1/operations/certificates/*` | SQLite | operações/certificados | preview e emissão protegida | testes existentes | PARTIAL | preview iframe existe; revisão/aprovação completa de todos documentos ainda parcial | generalizar workflow documental DRAFT→ARCHIVED |
| Certificados | Certificados | Assinaturas/carimbos | signatories + PDF | SQLite/uploads | manage certificates | automático por inspetor | testes parciais | FUNCTIONAL_NOT_VALIDATED | suporte existe, fidelidade visual ainda depende do exemplar PDF real | teste visual PDF e regressão de template |
| Fotos/anexos | Trabalhadores/equipamentos/veículos/património | Upload/preview/galeria | parcial/não consolidado | uploads/userData | granular | pendente | pendente | MISSING | prompt exige fotos/anexos em todas entidades | criar módulo media central |
| RH | RH Enterprise | Assiduidade/payroll/portal | `/api/v1/enterprise/hr/*` | SQLite | RH | parcial | `test_hr_workflows.py` | PARTIAL | portal e payroll existem; perfil trabalhador completo com abas ainda não | implementar EmployeeProfilePage completa |
| Património | Património | CRUD/manutenção | `/api/v1/management/assets/*` | SQLite | gestão | parcial | pendente | PARTIAL | entidades existem; fotos/galeria/transferência/baixa não completas | adicionar media e workflow de ciclo de vida |
| Financeiro | Financeiro | faturas/recibos | `/api/v1/management/finance/*` | SQLite | financeiro | parcial | pendente | PARTIAL | fluxo base existe; automações e ligação viagem→custos incompletas | expandir automações financeiras |
| Automação | IA & Automação | gerar/rever sugestões | `/api/v1/enterprise/ai/assistant/*` | SQLite | admin/enterprise | idempotente parcial | `test_ai_ocr_rules.py` | FUNCTIONAL_VALIDATED | sugestões de OCR/regras e revisão existem | scheduler local/online completo pendente |
| Sync | Backup & Sync | backup/sync/conflitos | `/api/v1/system/*`, sync services | SQLite/cloud-ready | admin | parcial | preflight | PARTIAL | SQLite local pronto; PostgreSQL real não validado neste ambiente | validar Postgres/cloud com credenciais reais |
| Permissões | Backend APIs | RBAC | deps `require_permission` | SQLite roles | granular parcial | aplicado nas rotas críticas | testes parciais | PARTIAL | backend valida várias ações; matriz total por botão ainda pendente | completar auditoria por interação |
| Release | Build | Gerar instalador | n/d | n/d | release manager | congelado | `release-readiness` | FUNCTIONAL_NOT_VALIDATED | prompt proíbe novo instalador nesta fase | só gerar após gate passar |

## Última etapa verdadeiramente concluída

Build interno desktop `0.12.1` com backend standalone, mapas/provider inicial, GPS/geofences/replay base e Fases 8–12 locais.

## Etapa parcial atual

Completação funcional total: mapa operacional migrado para GIS MapLibre modular, mas ainda precisa validação com pacote real de Angola e provider externo quando houver credenciais/dados licenciados.

## Itens críticos ainda não concluídos

- Traccar/provider telemático real.
- Google Maps online oficial com API key e health.
- Pacote Angola PMTiles/MBTiles real fornecido/importado e validado visualmente.
- Editor real de geofences no mapa.
- Fotos/anexos centralizados em todas entidades.
- Workflow documental completo para todos documentos.
- E2E/browser acceptance em ambiente com browser integrado funcional.
- PostgreSQL/cloud sync validado com infraestrutura real.
