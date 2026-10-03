# Baseline técnico — Fases 13 a 15

Data: 2026-08-02  
Estado: baseline funcional retomada, Android corrigido, SerpApi bloqueada por fornecedor, Google Maps carregável.

## Resumo executivo

- O projeto não foi reiniciado e alterações existentes foram preservadas.
- A falha anterior atribuída a `seed.py` era, na prática, execução fora do diretório correto/PYTHONPATH. O seed foi validado quando executado dentro de `backend`.
- O SDK Android portátil foi concluído em `.runtime/android-sdk` e o APK debug foi gerado com sucesso.
- A SerpApi está configurada no backend, mas a chave atual é recusada pelo fornecedor com HTTP 401/AUTH_ERROR.
- Google Maps JavaScript API está configurado e respondeu HTTP 200 sem marcadores de erro conhecidos.
- Foi criada a entidade real `operational_places` para guardar resultados SerpApi como locais operacionais, com geofence associada opcional.

## Evidências backend

| Validação | Resultado |
|---|---|
| `backend\.venv\Scripts\python.exe -m compileall backend\app -q` | OK |
| `backend\.venv\Scripts\python.exe -m pip check` | OK, sem dependências quebradas |
| `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_auth_dashboard.py -q` | 10 passed |
| `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_maps_serpapi_traccar.py -q` após 0005 | 7 passed |
| `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` após 0005 | 35 passed |
| `alembic heads` | `20260802_0005 (head)` |
| `alembic upgrade head` | OK |
| `alembic current` | `20260802_0005 (head)` |

## Evidências frontend/PWA

| Validação | Resultado |
|---|---|
| `npm --prefix frontend run lint` | 0 errors, warnings legados |
| `npm --prefix frontend run build` | OK |
| Service worker | cache atualizado para `fnlifting-enterprise-erp-v0.12.1` |
| Google Maps frontend env | `VITE_GOOGLE_MAPS_API_KEY=SET`, `VITE_GOOGLE_MAPS_ENABLED=true` |

## Evidências Android/mobile

| Item | Resultado |
|---|---|
| JBR Java/Javac | OK via Android Studio JBR |
| SDK local original | tinha platform/build-tools, mas faltava `cmdline-tools/latest` e `android-35` |
| SDK portátil | `.runtime/android-sdk` criado com `cmdline-tools`, `platform-tools`, `platforms/android-35`, `build-tools/35.0.0` e `build-tools/34.0.0` |
| `android/local.properties` | aponta para `C:/Projetos/FNLIFTING_ENTERPRISE_ERP/.runtime/android-sdk`; ficheiro ignorado por Git |
| Capacitor sync | assets Android atualizados |
| `npx cap doctor android` | success: “Android looking great” |
| APK debug | `android/app/build/outputs/apk/debug/app-debug.apk`, 8,850,944 bytes |
| `apksigner verify --print-certs` | exit 0, certificado debug Android |
| `aapt dump badging` | package `com.fnlifting.enterprise.erp`, minSdk 23, targetSdk 35 |
| `adb devices -l` | sem dispositivo/emulador conectado |

## Desktop runtime/seed

| Validação | Resultado |
|---|---|
| `backend\.venv\Scripts\python.exe desktop_runtime.py migrate` com `DATA_DIR` temporário | OK |
| `backend\.venv\Scripts\python.exe desktop_runtime.py seed` com `DATA_DIR` temporário | OK |
| Evidência | DB temporário criado e seed concluiu “FNLIFTING, RBAC, 7 utilizadores e dados de demonstração” |

Conclusão: a falha anterior do probe era de cwd/PYTHONPATH. O runtime desktop atual executa `desktop_runtime.py seed` com diretório correto e não depende de chamar `python seed.py` a partir de cwd errado.

## SerpApi

| Prova | Resultado |
|---|---|
| Env backend | `SERPAPI_ENABLED=SET`, `SERPAPI_KEY=SET` |
| Provider direto `serpapi_health_check("Luanda")` | `AUTH_ERROR` |
| Endpoint autenticado `/api/v1/integrations/serpapi/test` | HTTP 200 com payload `AUTH_ERROR` |
| HTTP mínimo ao fornecedor | HTTP 401, classificado como `AUTH_ERROR` |

Decisão: não declarar SerpApi como `CONNECTED` com a chave atual. O código está pronto; falta corrigir a chave/conta/quota no fornecedor.

## Google Maps

| Prova | Resultado |
|---|---|
| Env frontend | `VITE_GOOGLE_MAPS_API_KEY=SET`, `VITE_GOOGLE_MAPS_ENABLED=true` |
| Google Maps JavaScript API | HTTP 200 |
| Marcadores de erro conhecidos | nenhum dos marcadores testados foi encontrado |
| `/api/v1/maps/status` | `GOOGLE_ONLINE.status=CONFIGURED`, `available=True` |

## Locais operacionais

Implementado:

- modelo SQLAlchemy `OperationalPlace`;
- migration `20260802_0005_operational_places.py`;
- endpoints:
  - `GET /api/v1/fleet/operational-places`;
  - `POST /api/v1/fleet/operational-places`;
  - `PATCH /api/v1/fleet/operational-places/{place_id}`;
- persistência idempotente por `company_id + source + external_id`;
- criação opcional de geofence do tipo `point`;
- frontend: botão “Guardar” usa `createOperationalPlace`.

## Bloqueios externos

- Docker/Compose não estão disponíveis no PATH local.
- Dispositivo/emulador Android não está conectado.
- SerpApi rejeita a chave fornecida com HTTP 401.

## Próximo gate

Executar no final da retentativa:

- full backend tests;
- frontend lint/build;
- Alembic heads/current;
- preflight;
- readiness/release-readiness;
- secret scan;
- validação dos módulos alterados.

Último gate executado:

| Validação | Resultado |
|---|---|
| `/ready` com backend temporário | HTTP 200, `ready`, 0 warnings, 0 failures |
| `scripts\release-readiness.ps1 -SkipTests -SkipFrontendBuild` com backend temporário em `127.0.0.1:8000` | 0 failures, 0 warnings |

## Fase 15 - GPS piloto operacional

Implementado nesta continua��o:

- `GET /api/v1/fleet/gps/pilot/checklist` para onboarding de rastreador fisico.
- `POST /api/v1/fleet/gps/pilot/simulate` para executar viagem piloto Luanda-Malanje com camiao/device unicos por run.
- `GET /api/v1/fleet/gps/pilot/reports/{filename}` para download de relatorio PDF.
- Simulacao de buffer offline com flush ordenado.
- Prova de deduplicacao de evento GPS repetido.
- Alertas/geofences/replay usando a pipeline GPS existente.
- Relatorio PDF renderizado e corrigido apos QA visual.

Evidencia alvo:

| Validacao | Resultado |
|---|---|
| `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_gps_pilot_acceptance.py -q --basetemp=.runtime\pytest-tmp-phase15-pilot-rerun2` | 1 passed |
| Render PDF Poppler | PNG gerado em `.runtime\pdf-review\phase15-gps-pilot-fixed.png`, sem clipping visual |
| Classificacao | `GPS_SIMULATED_VALIDATED`; `GPS_PHYSICAL_PENDING_HARDWARE`; `TRACCAR_PIPELINE_READY_PENDING_EXTERNAL_RUNTIME`; `VENDOR_API_NOT_AVAILABLE` |

## Gate final da retentativa - 2026-08-02

| Validacao | Resultado |
|---|---|
| Backend tests completos | `40 passed, 649 warnings` com `--basetemp .runtime/pytest-basetemp` |
| Frontend lint | 0 errors, 24 warnings legados |
| Frontend build | OK |
| Alembic current/heads | `20260802_0006 (head)` |
| Prod preflight | ready 12 OK/0 warnings/0 failures; backend 40 passed; frontend build OK |
| Backend `/ready` temporario | HTTP 200, `ready`, 12 pass/0 warn/0 fail |
| Release-readiness | 0 failures, 2 warnings: Docker CLI ausente e SerpApi live nao assertado pelo gate |
| Desktop win-unpacked smoke | 3 ciclos OK |
| Desktop instalado smoke | 3 ciclos OK em `C:/Program Files/FNLIFTING ENTERPRISE ERP` |
| Android assembleDebug | BUILD SUCCESSFUL |
| Android test/lint | BUILD SUCCESSFUL |
| AAB | `BLOCKED_EXTERNAL_SIGNING`, sem keystore/signingConfig seguro |
