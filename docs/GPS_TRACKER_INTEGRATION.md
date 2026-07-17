# Integração de trackers GPS

## Estado implementado

O ERP aceita ingestão GPS sem login humano através de token próprio de dispositivo.

Fluxo:

1. Um utilizador com `fleet.manage` regista o tracker em `POST /api/v1/fleet/gps/devices`.
2. A resposta devolve o token uma única vez.
3. O equipamento envia eventos para `POST /api/v1/fleet/gps/ingest` com header:

```http
X-GPS-Device-Token: fnlgps.<device_id>.<secret>
```

## Payload mínimo

```json
{
  "event_id": "gps-20260717-0001",
  "trip_id": "opcional",
  "latitude": -8.839,
  "longitude": 13.289,
  "speed_kmh": 72,
  "heading": 180,
  "accuracy_meters": 7,
  "ignition_status": "on",
  "fuel_level_percent": 78,
  "odometer_km": 12001,
  "timestamp": "2026-07-17T03:00:00+00:00"
}
```

## Validações

- token do dispositivo;
- latitude/longitude;
- velocidade;
- camião associado à empresa;
- viagem pertencente ao camião;
- dedupe por `event_id`;
- tenant isolation via empresa do dispositivo.

## Efeitos automáticos

- grava `gps_integration_events`;
- grava `gps_positions` para o mapa real;
- atualiza `last_seen_at` do dispositivo;
- cria alerta de velocidade quando ultrapassa a regra ativa;
- avalia geofences ativas;
- cria eventos `ENTER`/`EXIT`;
- cria alertas e comandos operacionais deduplicados.

## Endpoints relacionados

- `GET /api/v1/fleet/gps/devices`
- `POST /api/v1/fleet/gps/devices`
- `POST /api/v1/fleet/gps/devices/{device_id}/rotate-token`
- `POST /api/v1/fleet/gps/ingest`
- `GET /api/v1/fleet/gps/history`
- `GET /api/v1/fleet/gps/replay`
- `GET /api/v1/fleet/gps/export.geojson`
- `GET /api/v1/fleet/gps/stream`
- `GET/POST /api/v1/fleet/geofences`
- `GET/POST /api/v1/fleet/alert-rules`
- `GET /api/v1/fleet/alerts`
- `POST /api/v1/fleet/alerts/{alert_id}/resolve`

## Limitação real

O endpoint SSE atual emite um snapshot curto para consumo local/fallback. Para telemetria de alta frequência com milhares de veículos, a próxima evolução deve usar broker/event bus ou WebSocket dedicado com backpressure.
