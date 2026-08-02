# Fase 13 — continuação operacional

Data: 2026-07-31

## Estado dos segredos

- `backend/.env` e `frontend/.env.local` continuam ignorados pelo Git.
- As chaves Google Maps e SerpApi foram configuradas apenas nesses ficheiros locais.
- Nenhum valor sensível deve ser impresso, comitado ou copiado para documentação.

## Mapas e geolocalização

- `GET /api/v1/maps/status` expõe provider padrão, provider ativo, modo online/offline/auto, pacote offline ativo, estado Google Maps, estado MapLibre/OSM e snapshot SerpApi.
- `POST /api/v1/integrations/serpapi/test` testa a SerpApi sem expor chave.
- `GET /api/v1/maps/places/search` usa cache TTL, rate limit local, paginação, deduplicação e auditoria sanitizada.
- A página `Configurações empresariais` inclui o bloco “Mapas e Geolocalização” com health-check de providers e botão “Testar” para SerpApi.

## Validação SerpApi real

- Ambiente local: chave presente e `SERPAPI_ENABLED=true`.
- Resultado do teste real em 2026-07-31: `AUTH_ERROR`.
- Interpretação: a integração está configurada e operacional, mas o fornecedor rejeitou a chave informada. É necessário substituir/validar a chave SerpApi na conta do fornecedor antes de declarar `CONNECTED`.

## Android

- Android Studio detectado em `C:\Program Files\Android\Android Studio\bin\studio64.exe`.
- JBR detectado em `C:\Program Files\Android\Android Studio\jbr\bin\java.exe`.
- `adb` detectado em `C:\Android\platform-tools\adb.exe`.
- SDK Android completo não detectado: faltam `platforms` e `build-tools`.
- `android/local.properties` não foi escrito porque apontar para SDK incompleto causaria build quebrado.

## Validações executadas

- `backend\.venv\Scripts\python.exe -m compileall backend\app -q`
- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_maps_serpapi_traccar.py -q`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run build`
