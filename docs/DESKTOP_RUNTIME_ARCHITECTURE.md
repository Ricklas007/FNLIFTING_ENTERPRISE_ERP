# Arquitetura Desktop Runtime 0.12.1

## Componentes

- Electron: janela, splash, lifecycle, single-instance lock e servidor local do frontend.
- Backend standalone: `FNLiftingBackend.exe` com comandos `migrate`, `seed`, `serve` e `run`.
- Frontend: `frontend/dist` servido localmente em `127.0.0.1`.
- Banco: SQLite em `userData/data/fnlifting.db`.
- Logs: `userData/logs`.

## Lifecycle

1. `app.requestSingleInstanceLock()`.
2. Criacao dos diretorios de runtime.
3. Selecao de portas livres.
4. Migracao segura de banco legado quando aplicavel.
5. `FNLiftingBackend.exe migrate`.
6. `FNLiftingBackend.exe seed`.
7. `FNLiftingBackend.exe serve`.
8. Espera real por `/ready`.
9. Servidor local do frontend.
10. Abertura da janela principal.

## Seguranca Electron

- `nodeIntegration=false`.
- `contextIsolation=true`.
- `sandbox=true`.
- Preload minimo.
- `fs`, `child_process` e shell arbitrario nao sao expostos ao renderer.
- Navegacao externa e `window.open` sao bloqueados/encaminhados para o browser externo.
- Backend escuta apenas em `127.0.0.1`.

## API runtime

O frontend continua funcional em browser/PWA com `/api/v1`. No Electron, a app local serve o frontend em porta dinamica e faz proxy de `/api`, `/ready` e `/health` para o backend selecionado.
