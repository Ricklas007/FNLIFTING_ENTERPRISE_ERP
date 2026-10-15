# Instalação piloto Android

APK debug: `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\android\app\build\outputs\apk\debug\app-debug.apk`.

Instalação manual: copie o APK para o dispositivo, permita instalação da origem escolhida e instale. Para ADB autorizado: `adb install -r app-debug.apk`.

`adb devices` nesta execução não apresentou dispositivo autorizado; testes de UI, login, mapa, documentos, offline e reconexão ficam `BLOCKED_EXTERNAL`.
