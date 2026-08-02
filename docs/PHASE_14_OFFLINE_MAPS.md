# Fase 14 — Mapa offline real PMTiles/MBTiles

Data: 2026-08-02

## Resultado implementado

- Criadas as entidades persistentes `MapPackage`, `MapPackageValidation`, `MapPackageActivation` e `MapPackageUsage`.
- Criada a migration `20260802_0006_map_packages.py`.
- Implementados endpoints autenticados/RBAC para:
  - `GET /api/v1/maps/packages`
  - `POST /api/v1/maps/packages/import`
  - `POST /api/v1/maps/packages/{id}/validate`
  - `POST /api/v1/maps/packages/{id}/activate`
  - `POST /api/v1/maps/packages/{id}/deactivate`
  - `POST /api/v1/maps/packages/deactivate`
  - `DELETE /api/v1/maps/packages/{id}`
  - `GET /api/v1/maps/packages/{id}/metadata`
  - `GET /api/v1/maps/packages/active`
  - `GET /api/v1/maps/packages/{id}/pmtiles`
  - `GET /api/v1/maps/packages/{id}/tiles/{z}/{x}/{y}.{extension}`
- Validação real de pacote:
  - extensão `.pmtiles`/`.mbtiles`;
  - assinatura PMTiles;
  - estrutura SQLite/MBTiles;
  - checksum SHA-256;
  - MIME inferido;
  - tamanho;
  - espaço livre;
  - bounds;
  - zoom mínimo/máximo;
  - licença;
  - proteção contra path traversal;
  - isolamento por `company_id`;
  - registo de uso de tiles/PMTiles.
- Frontend atualizado no gestor de mapas offline com ações de validar, ativar, desativar e remover.

## Falhas encontradas e corrigidas

1. `alembic` executado da raiz falhava com `No 'script_location' key found in configuration`.
   - Correção: validações Alembic executadas com `cwd=backend`, mantendo o mesmo princípio aplicado ao problema anterior de `PYTHONPATH`.

2. SQLite/MBTiles ficava com handle aberto no Windows e bloqueava a remoção do ficheiro (`WinError 32`).
   - Correção: conexões SQLite passaram a fechar explicitamente; remoção captura `PermissionError` e devolve HTTP 409 controlado.

3. Reimportação idempotente do mesmo checksum podia reaproveitar registo antigo sem refletir `active=True` na resposta.
   - Correção: ativação agora marca explicitamente o registo alvo antes de desativar os restantes pacotes da empresa.

4. `npm` via PowerShell falhou por `ExecutionPolicy`.
   - Correção: build validado com `npm.cmd --prefix frontend run build`.

5. `pytest tmp_path` tentou usar `%TEMP%` com caminho/permissão corrompida.
   - Correção operacional: suíte repetida com `--basetemp=backend\data\pytest-tmp-phase14b`.

## Evidências

| Validação | Resultado |
|---|---|
| `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_maps_serpapi_traccar.py -q --basetemp=backend\data\pytest-tmp-phase14b` | 8 passed |
| `npm.cmd --prefix frontend run build` | OK |
| `backend\.venv\Scripts\python.exe -m alembic heads` em `backend` | `20260802_0006 (head)` |
| `backend\.venv\Scripts\python.exe -m alembic current` em `backend` | `20260802_0006 (head)` |
| Consulta SQLite | `map_packages`, `map_package_validations`, `map_package_activations`, `map_package_usage` existem |

## Estado

Fase 14 marcada como implementada e validada para o escopo de mapa offline real. Ainda depende de pacotes PMTiles/MBTiles reais licenciados para operação cartográfica de produção.
