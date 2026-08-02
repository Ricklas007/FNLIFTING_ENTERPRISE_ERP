# Fase 15 - GPS pilot and operational acceptance

Date: 2026-08-02

## Status

Classification: `GPS_SIMULATED_VALIDATED` for the ERP GPS pipeline with simulator.
Classification: `GPS_PHYSICAL_PENDING_HARDWARE` for real tracker installation until a physical tracker, SIM/APN and gateway credentials are supplied.
Classification: `TRACCAR_PIPELINE_READY_PENDING_EXTERNAL_RUNTIME` in this local environment because Docker/Traccar runtime is not available in PATH.
Classification: `VENDOR_API_NOT_AVAILABLE` until a manufacturer API endpoint and credentials are configured outside Git.

## Implemented scope

- GPS onboarding checklist endpoint: `GET /api/v1/fleet/gps/pilot/checklist`.
- Pilot simulator endpoint: `POST /api/v1/fleet/gps/pilot/simulate`.
- Pilot report download endpoint: `GET /api/v1/fleet/gps/pilot/reports/{filename}`.
- Deterministic pilot route: Luanda to Malanje.
- Per-run simulated truck and HTTP tracker device, avoiding cross-run GPS history contamination.
- Device token is generated and stored as hash only; the pilot response does not return the token.
- Speed alert rule for 80 km/h pilot limit.
- Run-scoped origin, restricted-area and destination geofences.
- GPS position ingestion through the existing idempotent GPS service.
- Offline buffer simulation with queued points and ordered flush evidence.
- Duplicate/replay probe validating idempotency.
- Replay validation through existing `/fleet/gps/replay`.
- GeoJSON/export, SSE stream and secure device ingest remain covered by existing GPS tests.
- PDF operational report generated with route, vehicle, driver, client, distance, stops, alerts, geofences, status flow and signature lines.

## API evidence

Targeted test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_gps_pilot_acceptance.py -q --basetemp=.runtime\pytest-tmp-phase15-pilot-rerun2
```

Result: `1 passed`.

The test validates:

- onboarding checklist includes hardware fields such as IMEI;
- simulator provider is `HTTP_TRACKER_SIMULATOR`;
- route positions are persisted;
- replay count equals persisted positions;
- stops are detected;
- alerts and geofence events are created;
- offline buffer queued points are preserved in order;
- duplicate GPS event replay is deduplicated;
- token hash exists and token is not returned in the response;
- PDF report is downloadable and starts with `%PDF`.

## PDF visual validation

The latest generated report was rendered with Poppler using the bundled runtime. The first render exposed right-margin clipping in the operational evidence paragraph. The PDF generator was corrected to set font explicitly and wrap long words/classifications. The corrected report was rendered again to:

`C:\Projetos\FNLIFTING_ENTERPRISE_ERP\.runtime\pdf-review\phase15-gps-pilot-fixed.png`

Visual result: readable page, no margin clipping, summary/table/signature area aligned.

Poppler emitted font warnings for `Symbol` and `ArialUnicode`, but the generated PNG was valid and visually legible.

## Physical tracker onboarding checklist

Required fields before declaring `GPS_PHYSICAL_CONNECTED`:

- manufacturer;
- model;
- IMEI;
- serial;
- protocol;
- SIM ICCID;
- operator;
- APN;
- firmware;
- server/port;
- transmission frequency;
- truck assignment;
- driver/shift assignment where applicable.

Supported methods prepared by the ERP:

- `TRACCAR`;
- `VENDOR_API`;
- `DIRECT_PROTOCOL`;
- `HTTP`;
- `MQTT`;
- `WEBHOOK`;
- `MANUAL_IMPORT`.

## Operational acceptance notes

The ERP can now prove the GPS flow without hardware:

1. Create pilot trip.
2. Assign truck, driver, client and simulated device.
3. Ingest route points.
4. Trigger speed/geofence alerts.
5. Simulate offline buffering.
6. Validate deduplication.
7. Replay historical route.
8. Download PDF report.

Real Traccar/physical tracker acceptance still needs an external runtime/device and must not be declared complete without evidence from the actual gateway/device.
