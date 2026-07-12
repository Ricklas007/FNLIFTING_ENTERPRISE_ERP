# Base de dados

## SQLite local

Por omissão o ficheiro é criado em `backend/data/fnlifting.db`.

```powershell
cd backend
python seed.py --reset
```

Sem `--reset`, o seed é idempotente e não duplica a empresa proprietária.

## PostgreSQL

Defina no `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://fnlifting:palavra-passe@localhost:5432/fnlifting
```

O modelo SQLAlchemy usa tipos compatíveis com SQLite e PostgreSQL. A Fase 7 adiciona migrações Alembic com baseline inicial; antes da implantação cloud ainda devem ser definidas políticas externas de backup, alta disponibilidade e retenção.

## Convenções

As entidades persistentes possuem UUID textual, `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by` e `sync_status`. Exclusão funcional futura deve preencher `deleted_at`; consultas públicas filtram registos apagados.

Tabelas implementadas: empresas, utilizadores, sessões, histórico de login, perfis, permissões, departamentos, trabalhadores, avaliações de desempenho, clientes, equipamentos, inspeções, certificados, camiões, viagens, relatórios diários, despesas, receitas, faturas, itens de fatura, pagamentos, recibos, património, manutenções, transferências, documentos, versões documentais, auditoria, notificações, solicitações externas, fila e execuções de sincronização, backups e configurações.

Na Fase 2, `employees.department_id` normaliza a lotação e `employees.user_id` associa opcionalmente um trabalhador à conta que submete relatórios. O score de desempenho é calculado no backend a partir de seis dimensões de 0–5 e persistido numa escala de 0–100.

Na Fase 3, `equipment_types.checklist_template` armazena o modelo técnico em JSON. Cada inspeção copia esse modelo para `inspection_checklist_items`, preservando o histórico mesmo quando o tipo é revisto. `technical_signatories` associa trabalhadores às qualificações, assinatura, carimbo e competências de inspeção/aprovação. `certificates.inspection_id` é único: uma inspeção aprovada origina no máximo um certificado. O `qr_token`, também único, permite validação pública sem expor identificadores internos.

Os PDFs emitidos ficam em `backend/data/certificates/`. O caminho persistido no certificado só é criado na emissão e a pasta está excluída do controlo de versão.

Na Fase 4, `drivers` guarda carta, categoria, validade e avaliação; `trucks` concentra os dados técnicos e documentais; `trips` liga motorista, camião e cliente. `gps_positions` conserva a timeline recebida dos dispositivos, enquanto `fuel_records` e `fleet_incidents` registam abastecimentos e ocorrências por viagem.

Na Fase 5, `assets` concentra a ficha financeira e operacional do bem; `asset_maintenance` e `asset_transfers` preservam o respetivo histórico. `invoices` agrega `invoice_items`, pagamentos e recibos, mantendo total, saldo e estado. Cada pagamento cria a receita correspondente e pode liquidar a fatura automaticamente.

`documents` contém metadados, associação opcional a cliente/trabalhador, validade e estado de aprovação. O conteúdo físico fica em `backend/data/documents/`; `document_versions` conserva nome, MIME, tamanho, checksum SHA-256, caminho e notas de cada versão. `audit_logs` é um registo explícito e somente de acréscimo das ações sensíveis, com utilizador, IP, máquina, entidade e valores JSON antes/depois.

Faturas e recibos gerados ficam em `backend/data/financial/`. Os caminhos persistidos são resolvidos e validados dentro das pastas de dados da aplicação antes do download.

Na Fase 6, `client_service_requests` liga solicitações do portal ao cliente e equipamento sem misturar tenants. `sync_queue` recebe automaticamente cada criação, alteração ou exclusão ORM e preserva payload, versão base, tentativas, erro e conflito remoto. `sync_runs` contém o resumo de cada lote processado.

`backups` guarda apenas metadados e checksum; o conteúdo cifrado fica em `backend/data/backups/*.fnlbak`. `settings` usa chave única por empresa para políticas tipadas de backup, sincronização, relatórios, finanças e segurança.

Na Fase 7, `alembic_version` marca a versão aplicada do schema. Em bases antigas, `scripts\migrate.ps1` marca o baseline sem recriar tabelas existentes; em bases novas, o baseline cria a estrutura completa.
