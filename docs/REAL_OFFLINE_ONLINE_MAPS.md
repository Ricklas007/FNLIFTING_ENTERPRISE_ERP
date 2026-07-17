# Mapas reais offline/online

## Estado implementado

- A página `Viagens & GPS` usa MapLibre GL JS como renderer cartográfico principal.
- O componente abstrato/SVG foi removido do fluxo operacional: quando nenhum provider real está disponível, o sistema mostra erro claro e o gestor de mapas, não um mapa fictício.
- A implementação frontend foi modularizada em `frontend/src/features/maps/`.
- O build usa dependências locais `maplibre-gl` e `pmtiles`, em vez de carregar MapLibre via CDN.
- Provider online raster usa OpenStreetMap em `https://tile.openstreetmap.org`, com atribuição obrigatória.
- Provider offline local aceita pacotes `.mbtiles` e `.pmtiles` guardados em `userData/maps`.
- Modo de operação:
  - `auto`: tenta online e, havendo pacote ativo, alterna para offline quando o provider online falha;
  - `online`: força provider online MapLibre;
  - `offline`: força pacote local ativo e não apresenta “ao vivo” como prova de provider externo.

## Providers

| Provider | Estado | Observação |
|---|---|---|
| `ONLINE_RASTER` | Implementado | OSM raster, requer internet e deve manter atribuição dos dados. |
| `OFFLINE_MBTILES` | Implementado | Renderiza MBTiles raster e MBTiles vectoriais compatíveis com esquema OpenMapTiles. |
| `OFFLINE_PMTILES` | Implementado para pacotes vectoriais compatíveis | Usa protocolo `pmtiles://` no MapLibre; a qualidade visual depende dos source-layers do pacote real. |
| `ONLINE_VECTOR` | Provider-ready | Não há endpoint/licença de vector tiles configurado. |
| `GOOGLE_ONLINE` | Provider-ready | Somente online e somente com API oficial/chave configurada; não há Google offline. |
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

Os mapas ficam fora do instalador e fora de `Program Files`, em `userData/maps`.

## Frontend

- `frontend/src/features/maps/components/GisFleetMap.tsx`
- `frontend/src/features/maps/providers/mapProvider.ts`
- `frontend/src/features/maps/providers/mapStyles.ts`
- `frontend/src/features/maps/types.ts`
- `frontend/public/maps/styles/fnl-dark.json`

## Validação executada

- `cmd /c "cd frontend && npx tsc -b --pretty false"`
- `cmd /c "cd frontend && npx vite build"`
- `backend/.venv/Scripts/python.exe -m compileall backend/app -q`
- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_gps_geofences_replay.py -q`
- `scripts/release-readiness.ps1 -SkipTests -SkipFrontendBuild -SkipBackendHealth`

## Limitação real

Não foi incluído um pacote Angola offline pesado/licenciado no repositório nem no instalador interno. O cliente deve importar um MBTiles/PMTiles licenciado pelo gestor offline.
