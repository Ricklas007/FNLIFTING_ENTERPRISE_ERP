# Fase 4 — Motoristas, camiões, viagens e GPS

A Fase 4 implementa o ciclo de transporte:

```text
Motorista + Camião + Cliente → Viagem → Posições GPS → Entrega / Incidente
```

## Motoristas e camiões

Motoristas possuem código, carta de condução, categoria, validade, telefone, avaliação e disponibilidade. Camiões guardam matrícula, marca, modelo, ano, tipo, capacidade do tanque, chassis, validade do seguro/licença/inspeção e motorista atribuído. Registos com histórico de viagem não podem ser eliminados.

## Viagens

Cada viagem liga camião, motorista e cliente, com origem, destino, província, cidade, tipo e quantidade de combustível, janela de saída/chegada e estado. Ao iniciar uma viagem, camião e motorista ficam ocupados; na entrega ou cancelamento voltam a ficar disponíveis.

## GPS local-first

`POST /api/v1/fleet/gps/positions` recebe latitude, longitude, velocidade, direção, estado do veículo, nível de combustível, camião, viagem e data/hora. A interface apresenta a última posição de cada camião num mapa real MapLibre, com provider online raster e fallback/importação offline por MBTiles/PMTiles. O histórico permanece disponível por viagem.

## Dados de demonstração

O seed cria cinco motoristas, cinco camiões-cisterna, cinco viagens, nove posições GPS, um abastecimento e um incidente. Três viagens começam em andamento e aparecem no mapa em tempo real.
