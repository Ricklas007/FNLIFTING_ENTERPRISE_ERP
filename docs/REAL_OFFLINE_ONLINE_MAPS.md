# Mapas reais offline/online

## Estado implementado

- Frontend de GPS usa MapLibre GL JS como motor cartográfico principal.
- Provider online raster usa tiles OpenStreetMap em `https://tile.openstreetmap.org`.
- Provider offline local aceita pacotes `.mbtiles` e `.pmtiles` guardados em `userData/maps`.
- Modo de operação:
  - `auto`: tenta online e, havendo pacote ativo, alterna para offline em falha de mapa;
  - `online`: força provider raster online;
  - `offline`: força pacote local ativo.
- O mapa abstrato/SVG deixou de ser o mapa principal da página `Viagens & GPS`.

## Providers

| Provider | Estado | Observação |
|---|---|---|
| `ONLINE_RASTER` | Implementado | OSM raster, requer internet e deve manter atribuição dos dados. |
| `OFFLINE_MBTILES` | Implementado para raster | Renderiza MBTiles com tiles `png`, `jpg`, `jpeg`, `webp` via backend local. |
| `OFFLINE_PMTILES` | Provider-ready | Importação/ativação/diagnóstico implementados; renderização visual exige stylesheet/layers do pacote. |
| `ONLINE_VECTOR` | Provider-ready | Não há endpoint/licença de vector tiles configurado. |
| `MAP_UNAVAILABLE` | Implementado | Mostra fallback operacional e erro explícito quando não há provider disponível. |

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

## Validação executada

- `npm --prefix frontend run build`
- `pytest backend/tests/test_maps_runtime.py`
- Validação de MBTiles com metadata.
- Rejeição de PMTiles corrompido.

## Limitação real

Não foi incluído um pacote Angola offline pesado/licenciado no instalador. O cliente deve importar um MBTiles/PMTiles licenciado pelo gestor offline.
