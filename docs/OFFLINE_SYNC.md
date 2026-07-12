# Offline e sincronização

## Implementação da Fase 6

O ERP continua totalmente funcional sem internet sobre SQLite. As entidades usam UUID, soft delete e `sync_status`; um evento transacional do SQLAlchemy cria uma entrada em `sync_queue` para cada mutação local.

Estados disponíveis:

- `pending`: aguarda processamento;
- `synced`: consolidado no checkpoint ou servidor remoto;
- `conflict`: a versão local divergiu da remota;
- `failed`: erro preservado para nova tentativa.

Cada entrada contém entidade, UUID, operação, payload JSON, versão base, tentativas, erro, conteúdo remoto conflitante e datas de processamento. A tela **Backup & Sync** apresenta a ligação do dispositivo, contagens, fila, histórico e ações de resolução.

## Modo local

Sem `SYNC_REMOTE_URL`, **Sincronizar agora** cria um checkpoint local: processa o lote, atualiza `sync_status` e mantém histórico em `sync_runs`. Isso permite testar todo o ciclo sem depender da cloud.

## Modo PostgreSQL/cloud

Configure no `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://fnlifting:palavra-passe@servidor:5432/fnlifting
SYNC_REMOTE_URL=https://erp-remoto.exemplo.ao
```

O campo `SYNC_REMOTE_URL` ativa o modo remoto na interface e constitui o ponto de extensão para o agente de transporte da implantação. O contrato de fila já é idempotente por UUID, preserva versões e nunca resolve conflitos silenciosamente.

## Conflitos

O administrador pode:

- manter a versão local, recolocando-a como pendente;
- aceitar a versão remota e concluir a entrada;
- fornecer um payload mesclado pela API e reenviar.

## Backup e restauro

O ficheiro `.fnlbak` contém snapshot consistente do SQLite, manifesto e ficheiros documentais. O payload é cifrado com Fernet; a chave é derivada da palavra-passe com PBKDF2-HMAC-SHA256 e 600.000 iterações. SHA-256 valida o pacote, a base e cada ficheiro.

O restauro exige palavra-passe e confirmação explícita. Depois de concluído, reinicie o backend para renovar todas as ligações à base restaurada.
