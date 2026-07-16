# Localizacao de Dados Desktop

Todos os dados mutaveis da app desktop ficam em `app.getPath("userData")`.

| Recurso | Localizacao |
|---|---|
| SQLite | `userData/data/fnlifting.db` |
| Uploads | `userData/uploads` |
| Certificados | `userData/certificates` |
| Relatorios | `userData/reports` |
| Faturas | `userData/invoices` |
| Recibos | `userData/receipts` |
| Backups | `userData/backups` |
| Logs | `userData/logs` |
| Configuracao | `userData/config` |
| Temporarios | `userData/temp` |
| Exportacoes | `userData/exports` |
| Mapas offline | `userData/maps` |
| Cache de mapas | `userData/map-cache` |
| GPS | `userData/gps` |
| Anexos | `userData/attachments` |

Nada disso deve ser gravado em `Program Files`, `resources`, ASAR ou `frontend/dist`.
