# Android build report

Data: 2026-08-02  
Objetivo: corrigir e validar build Android/Capacitor sem reiniciar o projeto.

## Correções aplicadas

- `android/local.properties` foi corrigido para apontar para o SDK portátil ignorado:
  - `C:/Projetos/FNLIFTING_ENTERPRISE_ERP/.runtime/android-sdk`
- `scripts/build-android.ps1` passou a:
  - gravar paths do SDK em formato seguro para `.properties`, escapando caracteres não ASCII quando necessário;
  - procurar Gradle cacheado quando o wrapper ficar preso;
  - manter JDK/SDK portáteis fora do Git.
- O SDK Android portátil foi instalado em `.runtime/android-sdk` com:
  - command-line tools;
  - platform-tools;
  - Android platform 35;
  - build-tools 35.0.0;
  - build-tools 34.0.0, instalado automaticamente pelo Android Gradle Plugin durante o build.

## Validação executada

| Comando/validação | Resultado |
|---|---|
| JBR `java` / `javac` | OK |
| `adb version` | OK |
| `npm run mobile:sync` | assets Android sincronizados |
| Gradle `assembleDebug` | OK |
| APK | `android/app/build/outputs/apk/debug/app-debug.apk` |
| Tamanho APK | 8,850,944 bytes |
| `apksigner verify --print-certs` | exit 0 |
| `aapt dump badging` | package `com.fnlifting.enterprise.erp`, minSdk 23, targetSdk 35 |
| `npx cap doctor android` | success |
| `adb devices -l` | sem dispositivo/emulador conectado |

## Observações

- O APK gerado é debug e assinado com certificado debug Android.
- O aviso do `apksigner` sobre entradas `META-INF/*` em APK debug não bloqueia instalação/execução; é aviso conhecido de empacotamento de metadados de dependências.
- A validação em dispositivo físico/emulador depende de haver um target listado por `adb devices -l`.

## Reproduzir

```powershell
npm run android:build
```
