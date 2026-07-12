# Fase 5 — Gestão empresarial

A Fase 5 acrescenta quatro áreas integradas ao ERP: Património, Financeiro, Documentos e Auditoria. Todas usam o RBAC existente, funcionam com SQLite local e estão preparadas para PostgreSQL.

## Património

- ficha do bem com código, categoria, marca, modelo, série, aquisição e depreciação;
- valor de aquisição e valor atual;
- localização, responsável, estado e notas;
- histórico de manutenções preventivas/corretivas;
- transferências entre responsáveis e localizações, com motivo e auditoria.

## Financeiro

- centro financeiro com totais de receitas, despesas, resultado e contas a receber;
- despesas por categoria, departamento, fornecedor, responsável e aprovação;
- receitas independentes ou associadas a faturas;
- faturas com múltiplos itens, subtotal, IVA, total, saldo e estado;
- pagamentos parciais ou integrais;
- geração automática de fatura e recibo em PDF com identidade FNLIFTING.

## Gestão documental

- upload de PDF, PNG, JPEG, TXT e DOCX até 10 MB;
- numeração automática, categoria, descrição, validade e associação a cliente ou trabalhador;
- histórico de versões com checksum SHA-256 e notas da alteração;
- aprovação da versão corrente;
- download controlado por permissão e, no portal externo, pelo tenant do cliente.

## Auditoria

As ações de criação, alteração, aprovação, pagamento, transferência e upload são gravadas com:

- utilizador e data/hora;
- IP e identificação da máquina/navegador;
- tipo, identificador e rótulo da entidade;
- descrição da ação;
- conteúdo anterior e posterior em JSON.

## Permissões

| Área | Consulta | Gestão |
|---|---|---|
| Património | `assets.view` | `assets.manage` |
| Financeiro | `finance.view` | `finance.manage` |
| Documentos | `documents.view` | `documents.manage` |
| Auditoria | `audit.view` | — |

## Dados de demonstração

O seed entrega cinco bens, respetivas manutenções e uma transferência; dez despesas; dez receitas; cinco faturas com itens, pagamentos e três recibos; três documentos versionados; e dez eventos de auditoria.

Para recriar o ambiente:

```powershell
cd backend
python seed.py --reset
```

Os ficheiros de demonstração ficam em `backend/data/documents/seed`. PDFs financeiros são criados quando uma fatura ou recibo é emitido.
