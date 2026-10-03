# Rollback instructions 0.12.1

Data: 2026-08-02  
Aplicacao: FNLIFTING ENTERPRISE ERP

## Objetivo

Reverter com seguranca uma instalacao local da release candidate `0.12.1` sem apagar dados reais, uploads, certificados, fotografias, backups ou bases locais.

## Principios

- Nao apagar `%APPDATA%`, `%LOCALAPPDATA%`, `ProgramData`, `backend/data`, uploads ou backups sem copia validada.
- Fazer backup do userData antes de reinstalar/desinstalar.
- Reinstalar apenas artefacto previamente validado.
- Validar `/ready` e login apos qualquer rollback.

## Backup antes do rollback

1. Fechar o FNLIFTING Enterprise ERP.
2. Copiar a pasta de dados do utilizador atual, por exemplo:
   - `%APPDATA%/fnlifting-enterprise-erp`
   - `%LOCALAPPDATA%/fnlifting-enterprise-erp`
3. Guardar tambem logs recentes para diagnostico.
4. Confirmar que a copia contem `data/fnlifting.db` quando existir.

## Rollback do desktop Windows

1. Desinstalar a versao atual pelo Windows Apps/Programas ou executar o instalador anterior validado.
2. Reinstalar o instalador anterior aprovado.
3. Nao escolher opcoes que removam dados de utilizador.
4. Abrir o app e validar que nao aparece o erro antigo de `resources/backend/.venv/Scripts/python.exe seed.py`.
5. Se necessario, executar smoke instalado:

```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/test-desktop-relaunch.ps1 -Installed
```

## Rollback de APK Android debug

1. Remover apenas o app debug se necessario:

```powershell
adb uninstall com.fnlifting.enterprise.erp
```

2. Instalar APK anterior validado:

```powershell
adb install -r caminho\para\app-debug.apk
```

3. Confirmar splash, login, dashboard e mapas.

## Validacao pos-rollback

| Validacao | Esperado |
|---|---|
| App desktop abre | sem erro de seed/PYTHONPATH |
| Backend local | `/ready` status `ready` |
| Login | utilizador autorizado entra |
| Base de dados | dados preservados |
| Documentos/certificados | ficheiros continuam visiveis |
| Logs | sem `boot failed`, `PermissionError`, `ModuleNotFoundError: app` |

## Recuperacao se rollback falhar

1. Fechar app.
2. Restaurar backup do userData para o local original.
3. Reinstalar o instalador `0.12.1` validado nesta release candidate.
4. Abrir logs pela tela de erro ou pela pasta `logs` do userData.
5. Rodar `scripts/test-desktop-relaunch.ps1 -Installed` para capturar evidencia.
