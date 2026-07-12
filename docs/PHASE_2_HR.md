# Fase 2 — Recursos Humanos

## Funcionalidades

- dashboard de RH com trabalhadores ativos, departamentos, relatórios pendentes e score médio;
- departamentos com código, responsável, descrição, estado e contagem de trabalhadores;
- trabalhadores com dados pessoais, BI/NIF, contactos, cargo, lotação, admissão, contrato e salário;
- pesquisa, filtros, atualização e arquivo lógico de trabalhadores;
- relatórios diários com horários, local, tarefas, dificuldades, resultados, observações e estado;
- aprovação ou pedido de correção pelo RH/supervisor;
- avaliações mensais com pontualidade, produtividade, qualidade, tarefas, relatórios e supervisor;
- ranking automático por score geral.

## Regras de acesso

- Administrador: acesso total.
- RH: gestão completa e aprovação.
- Supervisor: consulta de trabalhadores, revisão de relatórios e avaliações.
- Inspetor, técnico e motorista: apenas os próprios relatórios.
- Diretor Geral: consulta dos indicadores e resultados.

## Recriar os dados demo

Como a Fase 2 introduz novas tabelas e campos, bases locais da Fase 1 devem ser recriadas no ambiente de demonstração:

```powershell
cd backend
python seed.py --reset
```

Em produção, esta operação será substituída por migrações Alembic que preservam os dados existentes.
