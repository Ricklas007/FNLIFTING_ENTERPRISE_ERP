# Validação visual do mapa cartográfico

Data: 2026-07-17  
Ambiente: desenvolvimento local (`127.0.0.1:8000` + `127.0.0.1:5173`)  
Browser: Codex in-app browser

## Resultado

| Item | Estado | Evidência |
|---|---|---|
| MapLibre online | PASS | A página `Viagens & GPS` abriu com canvas MapLibre, tiles dark reais de Angola, estradas/labels, marcadores GPS e sem painel de erro. |
| Estilo `fnl-dark.json` | PASS | O ficheiro público contém source raster `carto-dark` e layer `carto-dark-raster`; o frontend usa `/maps/styles/fnl-dark.json` por padrão. |
| Pesquisa SerpApi | PASS controlado | O painel “Pesquisa auxiliar SerpApi” aparece no mapa. Sem `SERPAPI_KEY`, a UI mostra `SerpApi não configurada...` e não cria dados fictícios. |
| Assistente Traccar | PASS controlado | O card “Integrações GPS” mostra Traccar `DISCONNECTED`, botões `Testar`, `Listar devices`, `Importar` e `Ligar device ao camião`. |
| Google Maps oficial | NOT CONFIGURED | Provider separado existe, mas não foi validado por falta de `VITE_GOOGLE_MAPS_ENABLED=true` e `VITE_GOOGLE_MAPS_API_KEY`. |
| Offline Angola | NOT IMPORTED | Nenhum `angola.pmtiles`/`angola.mbtiles` real foi fornecido/importado neste ambiente. |

## Observações da execução

- Login local usado: conta demo seeded `admin@fnlifting.com` no portal staff.
- DOM verificado:
  - `.maplibregl-canvas` presente;
  - `.map-place-search` presente;
  - `.map-legend.real` com `4 posição(ões) GPS MapLibre online`;
  - `.map-unavailable-panel` vazio.
- Screenshot visual capturada durante a execução no browser integrado confirmou o mapa dark real com Angola, estradas e labels, aproximando a referência enviada pelo utilizador.

## Limites honestos

- Esta validação prova renderização cartográfica online MapLibre no ambiente local.
- Não prova Google Maps, SerpApi real, Traccar real nem GPS físico, porque não foram fornecidas chaves/servidor/dispositivos reais.
- O sistema está preparado para esses providers e falha de forma explícita quando não há configuração, sem simular conectividade externa.
