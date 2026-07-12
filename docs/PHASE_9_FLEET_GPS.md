# Fase 9 — Fleet, GPS e logística

## Entregue

- Command center em `/enterprise/fleet/command-center`.
- Criação de comandos logísticos em `/enterprise/fleet/commands`.
- Ingestão GPS em `/enterprise/gps/ingest`.
- UI “Command Center” no menu Fases 8–12.
- Integração com frota existente: camiões, viagens, GPS e incidentes.

O provider `local-gps` grava eventos reais na tabela `gps_integration_events`.
Integrações externas de GPS podem publicar no mesmo endpoint com `provider` próprio.
