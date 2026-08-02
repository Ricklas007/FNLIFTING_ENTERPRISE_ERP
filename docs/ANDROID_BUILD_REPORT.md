# Android build report

Data: 2026-08-02  
Objetivo: corrigir e validar build Android/Capacitor sem reiniciar o projeto.

## Correcoes aplicadas

- `android/local.properties` permanece local/ignorado e aponta para o SDK portatil em `.runtime/android-sdk`.
- `scripts/build-android.ps1` foi endurecido para:
  - gravar paths do SDK em formato seguro para `.properties`;
  - usar `NODE_OPTIONS=--require scripts/capacitor-os-userinfo-shim.cjs` durante o Capacitor, evitando falha Node `uv_os_get_passwd returned ENOMEM`;
  - usar `GRADLE_USER_HOME=.runtime/gradle-home`, evitando falha `native-platform.dll` no cache do perfil Windows;
  - usar `ANDROID_USER_HOME=.runtime/android-home`, evitando escrita em `C:\.android`;
  - manter JDK/SDK/Gradle cache fora do Git.
- `scripts/capacitor-os-userinfo-shim.cjs` corrige apenas a falha recuperavel de `os.userInfo()` no Node/Windows e nao altera `node_modules`.

## Ambiente validado

| Item | Resultado |
|---|---|
| JBR | `C:\Program Files\Android\Android Studio\jbr` |
| Android SDK | `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\.runtime\android-sdk` |
| Gradle home | `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\.runtime\gradle-home` |
| Android user home | `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\.runtime\android-home` |
| Capacitor CLI | `7.6.7` validado com shim |

## Validacao executada

| Comando/validacao | Resultado |
|---|---|
| `npm run android:build` | `BUILD SUCCESSFUL in 9m 49s` |
| `cap sync android` | OK |
| Gradle `assembleDebug` | OK |
| Gradle `test lint` | `BUILD SUCCESSFUL in 6m 25s` |
| APK | `android/app/build/outputs/apk/debug/app-debug.apk` |
| Tamanho APK | `9,346,368` bytes |
| SHA-256 APK | `A4D3E576E8A77EA4C69542577D2305E8126B3CD8905DB8BDFF69C0A75F5ADE08` |
| Package id | `com.fnlifting.enterprise.erp` |
| minSdk/targetSdk | minSdk 23, targetSdk 35 |
| Signing | debug signing |

## Retentativas e classificacao

| Falha | Causa | Correcao | Estado |
|---|---|---|---|
| `uv_os_get_passwd returned ENOMEM` | Node/Capacitor consultando usuario Windows | Shim `capacitor-os-userinfo-shim.cjs` restrito ao Capacitor | VALIDATED |
| `native-platform.dll` | Gradle cache no perfil Windows | `GRADLE_USER_HOME=.runtime/gradle-home` | VALIDATED |
| `Permission denied: getsockopt` | rede bloqueada para Maven | retentativa com rede autorizada | VALIDATED |
| `C:\.android` | Android user home incorreto no processo | `ANDROID_USER_HOME=.runtime/android-home` | VALIDATED |
| `npx cap doctor android` preso | probe CLI nao concluiu em tempo util | Gradle `test lint assembleDebug` usado como validacao nativa | DEGRADED_PROBE_NOT_BLOCKING |

## AAB

AAB release nao foi gerado porque nao existe `signingConfig` seguro nem keystore release configurada. Isto esta corretamente classificado como `BLOCKED_EXTERNAL_SIGNING`; nao criar ou versionar keystore dentro do repositorio.

## Observacoes

- O APK gerado e debug e nao deve ser commitado.
- A validacao em dispositivo fisico/emulador continua dependente de `adb devices -l` listar um alvo autorizado.
