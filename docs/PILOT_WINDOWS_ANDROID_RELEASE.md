# FNLIFTING ENTERPRISE ERP — Pilot Build 0.12.2

Estado: `BUILT_NOT_INSTALLED` para o instalador Windows e `BUILT_NOT_INSTALLED` para o APK Android.

## Artefactos validados

- Windows unpacked: `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\release\win-unpacked\FNLIFTING ENTERPRISE ERP.exe`
- Windows NSIS: `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\release\FNLIFTING-ENTERPRISE-ERP-Setup-0.12.2.exe` (129,407,087 bytes; SHA-256 `c15bdbfee3802c7e3798aafd1469922871874ed54fffd2e1601fcb9a7fde4482`)
- Backend standalone: `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\backend-dist\FNLiftingBackend\FNLiftingBackend.exe`
- Android APK debug: `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\android\app\build\outputs\apk\debug\app-debug.apk` (8,856,625 bytes; SHA-256 `8fb0accff8a2af73d5287bae824cff7c7d501613093a2320c328f9234f2f8b2b`)

## Gates

- Backend standalone migrate/seed/serve/ready: `VALIDATED`.
- Electron win-unpacked build: `VALIDATED`.
- Electron smoke: `VALIDATED` — 3 ciclos.
- NSIS installer: `VALIDATED`.
- Capacitor sync e Gradle assembleDebug: `VALIDATED`.
- Dispositivo Android: `BLOCKED_EXTERNAL` — `adb devices` não listou alvo autorizado.
- Docker/cloud: fora do escopo desta release piloto.

Esta release não é produção final nem cloud-ready.
