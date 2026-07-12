# Fase 6 — Continuidade, portal e inteligência

A Fase 6 fecha o plano funcional do ERP com quatro capacidades: backup cifrado, sincronização offline/online, portal completo do cliente e relatórios avançados.

## Backup cifrado

- snapshot consistente da base SQLite;
- inclusão opcional de documentos, certificados, faturas e recibos;
- PBKDF2-HMAC-SHA256 com 600.000 iterações e cifragem autenticada Fernet;
- checksum SHA-256 do pacote, base e ficheiros;
- verificação antes do restauro;
- exportação `.fnlbak`, histórico e auditoria.

O backup inicial de demonstração usa `DemoBackup@2026`. Em operação real, use uma palavra-passe privada que não seja guardada no ERP.

## Sincronização

- captura automática de mutações na transação local;
- estados `pending`, `synced`, `conflict` e `failed`;
- processamento em lote e histórico em `sync_runs`;
- resolução explícita de conflitos local/remota/mesclada;
- modo checkpoint local sem internet;
- contrato preparado para PostgreSQL e transporte configurado por `SYNC_REMOTE_URL`.

## Portal do cliente

O utilizador externo só vê dados associados à sua empresa:

- resumo de equipamentos, certificados, documentos e saldos;
- equipamentos e certificados com download do PDF;
- solicitações de inspeção, certificação, manutenção ou consultoria;
- acompanhamento do estado e resposta da equipa técnica;
- faturas e recibos PDF;
- documentos aprovados.

As rotas internas de finanças nunca são abertas ao perfil externo; o portal usa endpoints dedicados com filtro obrigatório de tenant.

## Relatórios avançados

Tipos disponíveis:

- executivo consolidado;
- financeiro;
- operações técnicas;
- pessoas e desempenho;
- frota e logística;
- património.

O utilizador escolhe um período até dois anos. O mesmo conjunto consolidado alimenta a interface e exportações PDF, Excel e CSV.

## Configurações

Políticas persistentes e tipadas controlam nome empresarial, moeda, backup automático, retenção, sincronização automática, intervalo, relatório mensal e duração de sessão.

## Dados de demonstração

- quatro solicitações de serviço em diferentes estados;
- oito entradas de sincronização, incluindo conflito e falha;
- uma execução histórica;
- oito configurações empresariais;
- um backup cifrado válido.

Para recriar tudo:

```powershell
cd backend
python seed.py --reset
```
