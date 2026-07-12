# Arquitetura

## Decisões das Fases 1–7

O sistema usa uma arquitetura em duas aplicações, com contratos REST versionados:

```text
React/Vite  -- /api/v1 --> FastAPI --> SQLAlchemy --> SQLite local
                                      └------------> PostgreSQL cloud configurável
```

Em produção Docker, o React é servido por Nginx e o proxy encaminha `/api`, `/health` e `/ready` para o backend:

```text
Nginx/React -- /api,/ready --> FastAPI --> SQLAlchemy --> SQLite volume / PostgreSQL
```

O frontend não conhece diretamente a base de dados. Autenticação, isolamento por empresa e autorização são sempre validados no backend.

### Backend

- `app/api`: rotas REST e dependências de autorização;
- `app/core`: configuração e criptografia;
- `app/database`: engine, sessão e metadata;
- `app/models`: identidade, RBAC e entidades de negócio;
- `app/schemas`: contratos Pydantic;
- `app/services`: regras de negócio a expandir;
- `app/pdf`: geração local de certificados técnicos, faturas e recibos;
- `app/sync`: rastreio transacional, fila, backup cifrado e restauro;
- `app/reports`: consolidação e exportação PDF/Excel/CSV;
- `app/gps`: posições e telemetria local;
- `app/ops`: readiness, preflight e checks de produção.

### Frontend

- `components`: componentes partilhados e sequência de arranque;
- `pages`: login, registo, dashboard e módulos de RH, operações, frota, gestão, portal e operação;
- `layouts`: shell empresarial responsivo;
- `services`: cliente REST e armazenamento de sessão;
- `store`: contexto de autenticação;
- `types`: contratos TypeScript.

## Multiempresa

`users.company_id` define o tenant do utilizador. A FNLIFTING é do tipo `owner`; empresas clientes são do tipo `client`. O registo de cliente liga a empresa do portal a um registo `clients.portal_company_id`. Endpoints externos usam essa ligação como filtro obrigatório.

## Segurança

As palavras-passe usam PBKDF2-HMAC-SHA256 com salt aleatório e 600.000 iterações. O JWT contém utilizador, sessão, empresa, tipo, expiração e identificador único. A tabela `user_sessions` permite revogação no logout. As permissões são reunidas a partir dos perfis do utilizador e validadas por dependências FastAPI.

A Fase 7 acrescenta cabeçalhos HTTP básicos, `TrustedHostMiddleware` em produção e validações explícitas para `SECRET_KEY`, `DEBUG`, CORS e hosts permitidos.

## Gestão e rastreabilidade

Os módulos de património, finanças e documentos partilham o prefixo REST `/api/v1/management`. A interface só apresenta ações permitidas pelo RBAC, mas a autorização é repetida obrigatoriamente no backend. Downloads financeiros e documentais são resolvidos em diretórios locais controlados.

Toda mutação sensível da Fase 5 escreve um evento em `audit_logs` na mesma sessão transacional, incluindo entidade, utilizador, origem e estado antes/depois. Isso mantém o histórico consultável sem depender dos logs voláteis do servidor.

## Continuidade e sincronização

O listener `before_flush` observa entidades baseadas em `RecordMixin` e adiciona a mutação a `sync_queue` na mesma transação. Modelos operacionais da própria sincronização são excluídos para evitar recursão. O processamento em lote atualiza a fila e o `sync_status` da entidade de forma idempotente.

Backups usam a API nativa de snapshot do SQLite, empacotam documentos autorizados e são cifrados antes de chegar ao disco. O restauro valida cabeçalho, autenticação Fernet, manifesto, SHA-256 e caminhos para impedir corrupção e *zip slip*.

## Portal externo e relatórios

As rotas `/portal` resolvem obrigatoriamente `users.company_id -> clients.portal_company_id` antes de consultar qualquer equipamento, documento ou lançamento financeiro. O portal não recebe permissões financeiras internas.

O motor de relatórios consulta as entidades normalizadas e produz um contrato único de métricas, séries, decomposições e destaques. Os exportadores PDF, XLSX e CSV consomem esse mesmo contrato, evitando divergências entre o dashboard e os ficheiros.

## Operação e produção

Alembic versiona o schema a partir do baseline das Fases 1–7. Em produção, `AUTO_CREATE_SCHEMA=false` força o uso de migrações em vez de criação automática de tabelas no lifespan do FastAPI.

`/ready` comunica prontidão para Docker, balanceadores e monitores. O painel **Produção & Saúde** expõe o mesmo checklist para administradores com recomendações acionáveis. Os scripts PowerShell padronizam migração, preflight e arranque produtivo.

