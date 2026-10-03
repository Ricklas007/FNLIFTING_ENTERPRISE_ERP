# Release candidate 0.12.1

Data: 2026-08-02  
Projeto: FNLIFTING ENTERPRISE ERP  
Escopo: Fases 13, 14 e 15, incluindo correcao do probe desktop/PYTHONPATH, pacote Windows, APK debug, preflight e readiness.

## Resultado

Release candidate local gerada e validada no ambiente disponivel.

## Artefactos gerados localmente

> Estes artefactos nao devem ser commitados.

| Artefacto | Caminho | Tamanho | SHA-256 |
|---|---|---:|---|
| Windows installer | `release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe` | `128,562,626` bytes | `A3CC05B0397518774B9E0CE7A60802941B8B2578FF520CCAFE7AAB44A1823472` |
| Windows blockmap | `release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe.blockmap` | `134,607` bytes | `6EE3946FFD12C10A107B36B46B3B6DEE9E7772D548952A54749ECF319C20CD5D` |
| Android APK debug | `android/app/build/outputs/apk/debug/app-debug.apk` | `9,346,368` bytes | `A4D3E576E8A77EA4C69542577D2305E8126B3CD8905DB8BDFF69C0A75F5ADE08` |

## Validacoes finais

| Gate | Resultado |
|---|---|
| Desktop static validation | `node desktop/validate-desktop.js`: passed |
| Backend standalone build | `scripts/build-desktop-backend.ps1 -SkipInstall`: OK |
| Backend standalone smoke | `scripts/test-backend-standalone.ps1`: OK |
| Windows win-unpacked | `electron-builder --dir`: OK |
| Windows installer NSIS | `electron-builder --win nsis`: OK |
| Installed desktop smoke | `scripts/test-desktop-relaunch.ps1 -Installed`: 3 ciclos OK |
| Frontend lint | 0 errors, 24 warnings legados |
| Frontend build | OK |
| Backend tests | 40 passed, 649 warnings |
| Alembic | current/head `20260802_0006` |
| Prod preflight | ready 12 OK/0 warnings/0 failures; tests 40 passed; frontend build OK |
| Backend `/ready` | HTTP 200, `ready`, 12 pass/0 warn/0 fail |
| Release-readiness | 0 failures, 2 warnings |
| Android build | `BUILD SUCCESSFUL in 9m 49s` |
| Android test/lint | `BUILD SUCCESSFUL in 6m 25s` |

## Correcoes de release aplicadas

- Desktop runtime injeta `PYTHONPATH` correto para backend e preserva fallback legado `packaged-python-legacy`.
- Smoke desktop agora usa userData isolado antes do single-instance lock, desativa GPU em modo smoke e grava `DESKTOP_READY` com fallback controlado.
- Scripts de smoke normalizam `PATH`/`Path` duplicados antes de `Start-Process`.
- Android build evita bugs de Node/Gradle/Android home em caminhos Windows e caches externos.
- `prod-preflight.ps1` agora falha corretamente quando comandos falham e usa basetemp seguro em `.runtime`.

## Avisos/bloqueios externos

| Item | Estado | Motivo |
|---|---|---|
| Docker runtime | `BLOCKED_EXTERNAL` | Docker CLI nao disponivel no PATH local |
| SerpApi live status | `AUTH_ERROR`/nao assertado pelo unauthenticated gate | chave configurada, mas fornecedor recusou na evidencia anterior; nao revelar segredo |
| Android AAB release | `BLOCKED_EXTERNAL_SIGNING` | sem keystore/signingConfig release seguro |
| Android device/emulator acceptance | `BLOCKED_EXTERNAL_DEVICE` | depende de alvo `adb` autorizado |
| GPS fisico | `GPS_PHYSICAL_PENDING_HARDWARE` | pipeline simulada validada, hardware real ausente |
| Cloud publica | `PUBLIC_DEPLOYMENT_BLOCKED` | sem servidor/dominio/provedor publico conectado |
