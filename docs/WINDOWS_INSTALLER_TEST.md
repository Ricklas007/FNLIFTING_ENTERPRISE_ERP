# Teste do Instalador Windows 0.12.1

## Artefactos

| Artefacto | Tamanho | SHA-256 |
|---|---:|---|
| `release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe` | 122.23 MB | `A650A0B3F781DA1F4C276C526FA21790E7BDB2B50DBBDA051481A675625813FB` |
| `release/FNLIFTING-ENTERPRISE-ERP-Setup-0.12.1.exe.blockmap` | 0.13 MB | `564D5E38EEB1AD052786DEBB327D203B11CE9F5A194591D616186BB5E25FA46B` |
| `release/win-unpacked/FNLIFTING ENTERPRISE ERP.exe` | 195.07 MB | `5EACFD822C335C84E239986B49ADB671F0EBD2762B18FCB741E5D62E20A7C2FA` |
| `release/win-unpacked/resources/backend/FNLiftingBackend/FNLiftingBackend.exe` | 15.91 MB | `19B47ACC8E1F826D5B931C1ACB4E22F1EEFDAEC38DC214FCDA9F4154431A8C23` |

`win-unpacked` completo: 392.04 MB.

## Validacoes executadas

- `npm run desktop:backend:smoke`: passou.
- `npm run desktop:pack`: passou.
- `npm run desktop:smoke`: passou com 3 ciclos.
- `npm run desktop:dist`: passou.
- Instalacao silenciosa 0.12.1 por utilizador: exit code 0.
- Instalacao 0.12.1 em `%LOCALAPPDATA%\Programs\FNLIFTING ENTERPRISE ERP`: backend standalone presente e `.venv` ausente.
- Smoke instalado 0.12.1 em `%LOCALAPPDATA%\Programs`: passou com 3 ciclos.
- Smoke com `userData` real existente: passou; `/ready` respondeu e `DESKTOP_READY` foi registado.

## Verificacoes negativas

No pacote 0.12.1:

- `resources/backend/.venv`: ausente.
- `resources/backend/.env`: ausente.
- `resources/backend/data`: ausente.
- `resources/backend/tests`: ausente.
- `resources/backend/__pycache__`: ausente.

## Limitacoes do ambiente

- A instalacao antiga em `C:\Program Files\FNLIFTING ENTERPRISE ERP` continuou presente e contem a arquitetura 0.12.0. A instalacao 0.12.1 validada foi a instalacao por utilizador.
- Android debug APK nao foi gerado porque `JAVA_HOME`/Java nao esta configurado no ambiente.
