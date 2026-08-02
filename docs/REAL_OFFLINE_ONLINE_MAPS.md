# Mapas reais offline/online

## Estado implementado

- A página `Viagens & GPS` usa MapLibre GL JS como renderer cartográfico principal.
- O componente abstrato/SVG foi removido do fluxo operacional: quando nenhum provider real está disponível, o sistema mostra erro claro e o gestor de mapas, não um mapa fictício.
- A implementação frontend foi modularizada em `frontend/src/features/maps/`.
- O build usa dependências locais `maplibre-gl` e `pmtiles`, em vez de carregar MapLibre via CDN.
- Provider online raster usa MapLibre com estilo funcional `frontend/public/maps/styles/fnl-dark.json`, baseado em tiles reais CARTO/OSM dark (`https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png`) e atribuição obrigatória.
- Provider offline local aceita pacotes `.mbtiles` e `.pmtiles` guardados em `userData/maps`.
- Modo de operação:
  - `auto`: tenta online e, havendo pacote ativo, alterna para offline quando o provider online falha;
  - `online`: força provider online MapLibre;
  - `offline`: força pacote local ativo e não apresenta “ao vivo” como prova de provider externo.

## Providers

| Provider | Estado | Observação |
|---|---|---|
| `ONLINE_RASTER` | Implementado | MapLibre raster real com estilo dark funcional, requer internet e deve manter atribuição dos dados. |
| `OFFLINE_MBTILES` | Implementado | Renderiza MBTiles raster e MBTiles vectoriais compatíveis com esquema OpenMapTiles. |
| `OFFLINE_PMTILES` | Implementado para pacotes vectoriais compatíveis | Usa protocolo `pmtiles://` no MapLibre; a qualidade visual depende dos source-layers do pacote real. |
| `ONLINE_VECTOR` | Provider-ready | Não há endpoint/licença de vector tiles configurado. |
| `GOOGLE_ONLINE` | Provider oficial separado | Somente online, somente com Google Maps JavaScript API oficial e `VITE_GOOGLE_MAPS_ENABLED=true`/`VITE_GOOGLE_MAPS_API_KEY`; não há Google offline nem tiles Google dentro do MapLibre. |
| `SERPAPI_PLACE_SEARCH` | Implementado como pesquisa auxiliar | Backend-only, usa `SERPAPI_ENABLED`/`SERPAPI_KEY`; pesquisa locais do Google Maps via SerpApi, normaliza resultados e permite mostrar/guardar ponto operacional sem renderizar mapas. |
| `MAP_UNAVAILABLE` | Implementado | Mostra erro explícito e orienta importar/configurar provider real. |

## Backend

Rotas principais:

- `GET /api/v1/maps/status`
- `POST /api/v1/maps/mode`
- `POST /api/v1/maps/packages/import`
- `POST /api/v1/maps/packages/{package_id}/activate`
- `POST /api/v1/maps/packages/deactivate`
- `DELETE /api/v1/maps/packages/{package_id}`
- `GET /api/v1/maps/packages/{package_id}/tiles/{z}/{x}/{y}.{extension}`
- `GET /api/v1/maps/packages/{package_id}/pmtiles`
- `GET /api/v1/maps/places/search`
- `POST /api/v1/integrations/serpapi/test`

Os mapas ficam fora do instalador e fora de `Program Files`, em `userData/maps`.

## Frontend

- `frontend/src/features/maps/components/GisFleetMap.tsx`
- `frontend/src/features/maps/providers/mapProvider.ts`
- `frontend/src/features/maps/providers/mapStyles.ts`
- `frontend/src/features/maps/types.ts`
- `frontend/public/maps/styles/fnl-dark.json`
- `frontend/.env.maps.example`

## SerpApi auxiliar

A SerpApi não desenha mapas no ERP. Ela é usada somente para pesquisa auxiliar de locais, com endpoint autenticado:

```http
GET /api/v1/maps/places/search?query=oficina&latitude=-8.8&longitude=13.2&zoom=10
```

Variáveis backend:

```env
SERPAPI_ENABLED=false
SERPAPI_KEY=
SERPAPI_BASE_URL=https://serpapi.com/search
SERPAPI_TIMEOUT=8
SERPAPI_RATE_LIMIT_PER_MINUTE=20
SERPAPI_RATE_LIMIT=20
SERPAPI_CACHE_TTL=300
```

Sem chave, a pesquisa responde `503` e o teste dedicado devolve `NOT_CONFIGURED`. Com chave inválida/rejeitada, o teste devolve `AUTH_ERROR` sem expor o segredo. A integração classifica `CONNECTED`, `AUTH_ERROR`, `QUOTA_EXCEEDED`, `TIMEOUT`, `RATE_LIMITED`, `PROVIDER_ERROR` e `DEGRADED`, aplica rate limit local, cache TTL e grava auditoria sanitizada.

Os resultados não são persistidos automaticamente: o utilizador precisa escolher “Guardar” para criar ponto operacional/geofence quando o modelo operacional dedicado estiver disponível.

## Validação executada

- `cmd /c "cd frontend && npx tsc -b --pretty false"`
- `cmd /c "cd frontend && npx vite build"`
- `backend/.venv/Scripts/python.exe -m compileall backend/app -q`
- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_gps_geofences_replay.py -q`
- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_maps_serpapi_traccar.py -q`
- Validação visual documentada em `docs/MAP_BROWSER_VALIDATION.md`
- `scripts/release-readiness.ps1 -SkipTests -SkipFrontendBuild`

## Limitação real

Não foi incluído um pacote Angola offline pesado/licenciado no repositório nem no instalador interno. O cliente deve importar um MBTiles/PMTiles licenciado pelo gestor offline.
