# Fase 8 — Cloud, Sync 2.0, MFA e notificações

Implementado em modo local-first com adapters preparados para cloud.

## Entregue

- Migração `20260712_0002` com tabelas enterprise.
- Registo de dispositivos em `/api/v1/enterprise/devices/register`.
- Gestão de sessões em `/api/v1/enterprise/sessions`.
- MFA TOTP com QR local, confirmação e códigos de recuperação.
- Login com desafio MFA quando o utilizador tem MFA ativo.
- Sync 2.0 local com `/enterprise/sync/push`, `/pull` e `/status`.
- Centro de notificações in-app com delivery local.
- Eventos de segurança auditáveis.

## Providers

Sem `SYNC_REMOTE_URL`, o sistema usa provider `local-sqlite`.
Quando `SYNC_REMOTE_URL` for definido, o status passa a indicar cloud-ready e o adapter pode ser ligado a PostgreSQL/API remota sem mudar o frontend.
