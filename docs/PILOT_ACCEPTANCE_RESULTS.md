# Resultados de aceitação da release piloto

| Área | Estado | Evidência |
|---|---|---|
| Backend standalone | VALIDATED | migrate, seed, serve e `/ready` em runtime temporário |
| Migrations | VALIDATED | head `20260830_0007` no código empacotado |
| Electron | VALIDATED | win-unpacked + 3 ciclos smoke |
| Instalador NSIS | BUILT_NOT_INSTALLED | ficheiro 0.12.2 e checksum presentes |
| Android APK | BUILT_NOT_INSTALLED | assembleDebug e artefacto presente |
| Android físico/emulador | BLOCKED_EXTERNAL | nenhum alvo ADB autorizado |
| Cloud/Docker | BLOCKED_EXTERNAL | não necessário para piloto local |
