# Gestor de mapas offline

## Objetivo

O gestor permite importar, validar, ativar e remover pacotes cartográficos locais sem escrever em `Program Files` e sem empacotar mapas grandes dentro do instalador.

## Localização

| Item | Local |
|---|---|
| Pacotes offline | `userData/maps/packages` |
| Manifest | `userData/maps/manifest.json` |
| Cache | `userData/map-cache` |

## Operações

- Importar pacote por caminho local absoluto (`.mbtiles` ou `.pmtiles`).
- Calcular checksum SHA-256.
- Validar magic bytes PMTiles.
- Validar SQLite MBTiles e tabela `tiles`.
- Guardar metadata de fonte, licença, versão, zoom, formato e tamanho.
- Ativar pacote.
- Desativar pacote.
- Remover pacote com confirmação na UI.
- Mostrar espaço livre do volume.

## Fluxo recomendado para Angola

1. Obter pacote cartográfico real e licenciado para Angola.
2. Confirmar fonte, licença e versão.
3. Importar no módulo `Viagens & GPS`.
4. Ativar o pacote.
5. Alterar o modo para `offline` ou manter `auto`.
6. Validar pontos GPS reais sobre o mapa.

## Notas de segurança

- A importação exige permissão `fleet.manage`.
- A visualização do estado exige `fleet.view`.
- Os endpoints de tiles servem ficheiros locais pelo backend em `127.0.0.1` para o MapLibre.
- Nenhum pacote offline é copiado para `resources`, `app.asar` ou pasta do instalador.
