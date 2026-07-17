# Desktop e Mobile - FNLIFTING ENTERPRISE ERP

Este documento regista o estado da conversao do ERP local-first em:

- software Windows instalavel via Electron + NSIS;
- PWA instalavel;
- app Android via Capacitor.

O trabalho foi feito sem alterar a base funcional das Fases 8-12. Esta camada apenas empacota a experiencia existente para desktop e mobile.

## Estado implementado

### Desktop Windows

- Criada estrutura `desktop/`.
- Criados `desktop/main.js`, `desktop/preload.js`, `desktop/splash.html`, `desktop/error.html`.
- Criados assets `desktop/assets/icon.ico`, `desktop/assets/icon.png` e `desktop/assets/splash-logo.png`.
- App name: `FNLIFTING ENTERPRISE ERP`.
- Splash inicial com identidade FNLIFTING antes do carregamento do sistema.
- Backend FastAPI iniciado automaticamente em segundo plano.
- Espera ativa por `/ready` antes de abrir a janela principal.
- Frontend servido a partir de `frontend/dist`.
- Proxy local de `/api`, `/ready` e `/health` para o backend.
- Ecran de erro com retry, abrir pasta de logs e fechar.
- Configuracao Electron segura: `contextIsolation`, `nodeIntegration: false`, `sandbox` e preload minimo.
- Encerramento do processo backend ao fechar a aplicacao.
- Configuracao `electron-builder` com alvo NSIS.
- Backend standalone `backend-dist/FNLiftingBackend/FNLiftingBackend.exe` via PyInstaller.
- Pacote 0.12.1 sem `backend/.venv`, `.env`, banco de desenvolvimento, testes ou caches.
- Dados mutaveis em `userData`, nao em `Program Files`.

Scripts adicionados na raiz:

```powershell
npm run desktop:dev
npm run desktop:backend:build
npm run desktop:backend:smoke
npm run desktop:build
npm run desktop:pack
npm run desktop:smoke
npm run desktop:dist
npm run desktop:installed:smoke
npm run app:start
```

### Mobile / PWA / Android

- Criado `frontend/public/manifest.json`.
- Criado `frontend/public/sw.js`.
- Criados icones PWA em `frontend/public/icons/`.
- Registrado service worker em producao.
- Adicionadas meta tags mobile/PWA em `frontend/index.html`.
- Adicionados ajustes CSS para toque, safe-area e telas estreitas.
- Criado `capacitor.config.json`.
- Criado projeto Android em `android/`.
- App ID: `com.fnlifting.enterprise.erp`.
- App name: `FNLIFTING ENTERPRISE ERP`.
- Splash Android configurado com identidade visual FNLIFTING.
- Assets web copiados por `mobile:sync`; os assets gerados dentro de `android/app/src/main/assets/public` ficam ignorados e podem ser recriados.

Scripts adicionados na raiz:

```powershell
npm run mobile:init
npm run mobile:sync
npm run android:open
npm run android:build
npm run android:build:portable
```

## Comandos executados nesta maquina

| Comando | Resultado | Observacao |
|---|---:|---|
| `npm install` | parcial | O download dos pacotes iniciou, mas o processo excedeu o tempo disponivel antes de concluir os scripts nativos. |
| `npm install --package-lock-only --ignore-scripts` | passou | Gerou `package-lock.json`. |
| `npm install --ignore-scripts` | passou | Instalou dependencias JS sem executar downloads nativos do Electron. |
| `npm run build` | passou | Build Vite/React gerado em `frontend/dist`. |
| `npm run desktop:build` | passou | Validacao estrutural desktop concluida. |
| `npm run mobile:init` | passou | Projeto Android criado. |
| `npm run mobile:sync` | passou | Capacitor sincronizado com `frontend/dist`. |
| `npm run android:open` | falhou por ambiente | Android Studio nao esta configurado nesta maquina. |
| `npm run desktop:pack` | superado | Bloqueio inicial por download do Electron foi resolvido; `win-unpacked` final foi gerado. |
| `backend/.venv/Scripts/python.exe -m pytest tests/test_observability_headers.py` | passou | 1 teste passou; execucao lenta por seed/demo. |
| `backend/.venv/Scripts/python.exe -m pytest tests/test_auth_dashboard.py tests/test_public_certificate_validation.py` | passou | 11 testes passaram. |
| `backend/.venv/Scripts/python.exe -m alembic current` | passou | Banco em `20260717_0004 (head)`. |
| `backend/.venv/Scripts/python.exe -m alembic heads` | passou | Head unico `20260717_0004 (head)`. |
| `backend/.venv/Scripts/python.exe tools/preflight.py --json` | passou | Ready com 10 OK, 1 aviso de backup antigo e 0 falhas. |
| `/ready` em backend temporario local | passou | `status=ready`, versao `0.12.1`, 10 OK, 1 aviso de backup antigo no banco dev e 0 falhas. |
| `npm run desktop:backend:smoke` | passou | Backend standalone: migrate, seed, serve e `/ready` em runtime temporario, incluindo migration `20260717_0004`. |
| `npx electron-builder --dir --publish never` | passou | Gerou `release/win-unpacked` 0.12.1 com backend standalone e sem `.venv`. |
| Smoke `win-unpacked` | passou | 3 ciclos de abertura/fecho/reabertura em `win-unpacked`. |
| `npx electron-builder --win nsis --publish never` | passou | Gerou `release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe`. |
| Instalacao por utilizador 0.12.1 | passou | Atualizada em `%LOCALAPPDATA%\Programs\FNLIFTING ENTERPRISE ERP`; atalho do Desktop aponta para ela. |
| Smoke instalado 0.12.1 por utilizador | passou | 3 ciclos com executavel instalado em `%LOCALAPPDATA%\Programs`. |
| Smoke com `userData` real | passou | Migration idempotente, backup pre-migration e `DESKTOP_READY`. |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` | passou | 27 testes passaram. |
| `npx cap sync android` | passou | Assets web sincronizados para `android/app/src/main/assets/public`. |
| `android/gradlew.bat assembleDebug` | bloqueado por ambiente | `JAVA_HOME` nao esta definido e nao existe `java` no PATH. Android SDK/Android Studio tambem nao esta instalado. |
| `npm run android:build:portable` | parcialmente retomado | Download parcial do JDK preservado em `.runtime/downloads`; sem Android SDK nao ha APK validado nesta maquina. |

Nota: a instalacao all-users em `C:\Program Files\FNLIFTING ENTERPRISE ERP` requer execucao do instalador como Administrador. Sem elevacao/UAC, a validacao funcional desta execucao usa a instalacao por utilizador em `%LOCALAPPDATA%\Programs\FNLIFTING ENTERPRISE ERP`.

## Como gerar o instalador Windows

Em uma maquina com internet estavel para descarregar o Electron:

```powershell
npm install
npm run desktop:dist
```

Saida esperada:

```text
release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe
```

Se o download do Electron falhar, tente configurar um mirror:

```powershell
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
npm rebuild electron
npm run desktop:dist
```

## Como abrir e compilar o Android

Instale Android Studio, JDK e Android SDK. Depois:

```powershell
npm run mobile:sync
npm run android:open
```

Para build via Gradle:

```powershell
npm run android:build
```

Se a maquina nao tiver Java/JDK configurado, use o modo portatil:

```powershell
npm run android:build:portable
```

Esse comando descarrega um JDK 17 para `.runtime/android-jdk` e define `JAVA_HOME` apenas durante o build. A pasta `.runtime` fica ignorada pelo Git.
Se a ligacao estiver lenta e o download nao terminar, volte a executar o mesmo comando; o arquivo parcial em `.runtime/downloads` e retomado automaticamente.

Se `android:open` indicar que o Android Studio nao foi encontrado, defina:

```powershell
$env:CAPACITOR_ANDROID_STUDIO_PATH="C:\Program Files\Android\Android Studio\bin\studio64.exe"
npm run android:open
```

## Checklist de seguranca e empacotamento

- Nao versionar `.env`, bases SQLite, backups, logs, `node_modules`, `frontend/dist`, `release` ou builds Android.
- O backend desktop gera segredos locais no diretorio de dados da aplicacao do utilizador.
- O backend desktop usa `127.0.0.1` e porta local dedicada.
- O Electron nao expoe Node.js ao renderer.
- O frontend mobile/PWA usa build de producao.
- O Android precisa de `mobile:sync` antes de build/abertura no Android Studio.

## Troubleshooting rapido

### Desktop abre e fica no splash

Verifique os logs atraves do ecran de erro ou na pasta de dados da aplicacao. Confirme que as dependencias Python do backend existem e que `/ready` responde.

### Erro "Backend Python nao encontrado"

Instale as dependencias do backend ou defina:

```powershell
$env:FNLIFTING_PYTHON="C:\caminho\para\python.exe"
npm run app:start
```

### `desktop:pack` nao gera `release`

Confirme que `node_modules/electron/dist/electron.exe` existe. Caso contrario:

```powershell
npm rebuild electron
npm run desktop:pack
```

### Android Studio nao abre

Instale o Android Studio ou defina `CAPACITOR_ANDROID_STUDIO_PATH` conforme o caminho real do `studio64.exe`.
