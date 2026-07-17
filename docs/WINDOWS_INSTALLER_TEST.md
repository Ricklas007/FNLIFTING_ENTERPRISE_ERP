# Teste do Instalador Windows 0.12.1

## Artefactos finais

| Artefacto | Tamanho | SHA-256 | Gerado em |
|---|---:|---|---|
| `release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe` | 122.29 MB | `1BA7E76F9C4666BBDA686E2B8261C88F9EEA9EC4790F86F4ED459B91FC664D95` | 2026-07-17 09:25:13 |
| `release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe.blockmap` | 0.13 MB | `27BD72724ACE8975131F00F0D76A02E72CA774FF7FE51FC18EC479900CA26649` | 2026-07-17 09:25:23 |
| `release/win-unpacked/FNLIFTING ENTERPRISE ERP.exe` | 195.07 MB | `777D3BEB99F049C025DDB676EAD939AB18C7DB65AFF45C341FA883933024C053` | 2026-07-17 09:20:30 |
| `release/win-unpacked/resources/backend/FNLiftingBackend/FNLiftingBackend.exe` | 15.96 MB | `10C74D89D297808DA1355DB61BB5BB4E4D61751F8281713836C1653B5FBB895A` | 2026-07-17 09:00:51 |

## Validações executadas

- `npm run desktop:build`: passou com frontend Vite/TypeScript e backend PyInstaller.
- `npm run desktop:backend:smoke`: passou; migrations de `20260707_0001` até `20260717_0004`.
- `npx electron-builder --dir --publish never`: passou e gerou `release/win-unpacked`.
- Smoke `win-unpacked`: passou com 3 ciclos.
- `npx electron-builder --win nsis --publish never`: passou e regenerou o instalador 0.12.1.
- Instalação por utilizador em `%LOCALAPPDATA%\Programs\FNLIFTING ENTERPRISE ERP`: atualizada a partir do `win-unpacked` validado.
- Smoke da instalação por utilizador: passou com 3 ciclos.

## Verificações negativas

No pacote 0.12.1 validado:

- `resources/backend/.venv`: ausente.
- `resources/backend/.env`: ausente.
- `resources/backend/data`: ausente.
- `resources/backend/tests`: ausente.
- `resources/backend/__pycache__`: ausente.
- `resources/backend/FNLiftingBackend/_internal/alembic/versions/20260717_0004_enterprise_completion_hardening.py`: presente.

## Limitações reais do ambiente

- A atualização all-users em `C:\Program Files\FNLIFTING ENTERPRISE ERP` requer elevação/UAC. Nesta execução sem aprovação administrativa, o instalador silencioso `/S /allusers` retornou cancelamento de UAC e o Windows bloqueou escrita direta em Program Files.
- Para não deixar o utilizador sem aplicação, foi criada/atualizada uma instalação por utilizador em `%LOCALAPPDATA%\Programs\FNLIFTING ENTERPRISE ERP` e o atalho do Desktop do utilizador foi apontado para ela.
- Para restaurar uma instalação all-users em Program Files, execute `release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe` manualmente como Administrador.
- Android debug APK ainda depende de JDK/Android SDK disponíveis; o auxiliar portátil permanece pronto para retoma.
