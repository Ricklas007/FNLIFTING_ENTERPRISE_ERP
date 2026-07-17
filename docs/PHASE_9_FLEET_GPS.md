# Fase 9 — Fleet, GPS e logística

## Entregue

- Command center em `/enterprise/fleet/command-center`.
- Compliance enterprise da frota em `/enterprise/fleet/compliance`, calculado a partir de camiões, motoristas, viagens, GPS, incidentes, validade documental, tanques e reboques registados.
- Criação de comandos logísticos em `/enterprise/fleet/commands`.
- Ingestão GPS legada em `/enterprise/gps/ingest`, agora encaminhada para gravação real de posições quando latitude/longitude são enviadas.
- UI “Command Center” no menu Fases 8–12.
- Integração com frota existente: camiões, viagens, GPS, combustível e incidentes.
- Mapa principal de `Viagens & GPS` migrado para MapLibre GL JS.
- Provider online raster OpenStreetMap configurado com CSP desktop.
- Gestor de mapas offline para importar, validar, ativar e remover PMTiles/MBTiles.
- MBTiles raster validado como provider offline renderizável.
- PMTiles validado como pacote importável/provider-ready; renderização exige stylesheet/layers do pacote.
- Dispositivos GPS com token próprio, sem login humano.
- Ingestão segura em `/fleet/gps/ingest` com `X-GPS-Device-Token`.
- Histórico, replay, exportação GeoJSON e SSE snapshot em `/fleet/gps/*`.
- Geofences reais de círculo/polígono/corredor/ponto.
- Alertas deduplicados de velocidade e geofence `ENTER`/`EXIT`.

O provider `local-gps` grava eventos reais na tabela `gps_integration_events` e posições em `gps_positions`.
Integrações externas de GPS podem publicar no endpoint dedicado de dispositivos com token próprio.

## Validação adicional em 0.12.1

- `backend/tests/test_maps_runtime.py`
- `backend/tests/test_fleet_trips_gps.py`
- `backend/tests/test_gps_geofences_replay.py`
- `frontend` build TypeScript/Vite
- `docs/REAL_OFFLINE_ONLINE_MAPS.md`
- `docs/MAP_PACKAGE_MANAGEMENT.md`
- `docs/GPS_TRACKER_INTEGRATION.md`
