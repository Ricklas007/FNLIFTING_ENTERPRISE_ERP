# Incidente Desktop Runtime 0.12.0

## Causa raiz comprovada

A versao 0.12.0 empacotava uma `.venv` completa dentro de `resources/backend/.venv` e executava:

```text
python.exe -m alembic upgrade head
```

Na instalacao em `C:\Program Files\FNLIFTING ENTERPRISE ERP`, o import de `app.core.config` tentava criar:

```text
C:\Program Files\FNLIFTING ENTERPRISE ERP\resources\backend\data
```

O Windows bloqueou essa escrita com:

```text
PermissionError: [WinError 5] Acesso negado
```

Evidencias nos logs reais:

- `C:\Users\R3IS SOLUÇÕES\AppData\Roaming\fnlifting-enterprise-erp\logs\backend.log`
- `C:\Users\R3IS SOLUÇÕES\AppData\Roaming\fnlifting-enterprise-erp\logs\electron.log`

## Correcao aplicada em 0.12.1

- Backend standalone `FNLiftingBackend.exe` via PyInstaller.
- Electron deixa de executar `python -m alembic`.
- Electron deixa de empacotar `backend/.venv`.
- Dados mutaveis movidos para `app.getPath("userData")`.
- Assinaturas/carimbos tecnicos movidos para `userData/uploads/signatures`, evitando escrita em `resources/backend/FNLiftingBackend/_internal/data`.
- Logs separados: `desktop.log`, `backend.log`, `migration.log`, `startup.log`.
- Migration usa comando standalone `FNLiftingBackend.exe migrate`, com Alembic programatico.
- Backup pre-migration criado antes de upgrade quando ja existe SQLite.
- Smoke de tres arranques em `win-unpacked` passou.
- Smoke de tres arranques na instalacao 0.12.1 em `%LOCALAPPDATA%\Programs` passou.
- A reinstalacao all-users em `C:\Program Files\FNLIFTING ENTERPRISE ERP` exige UAC/administrador e nao foi concluida neste ambiente sem elevacao; a instalacao por utilizador foi usada como mitigacao funcional.

## Nota sobre instalacao antiga

A instalacao antiga em `C:\Program Files\FNLIFTING ENTERPRISE ERP` so deve ser atualizada executando o instalador 0.12.1 como Administrador. Quando nao houver elevacao, use a instalacao por utilizador 0.12.1 validada em:

```text
%LOCALAPPDATA%\Programs\FNLIFTING ENTERPRISE ERP
```
