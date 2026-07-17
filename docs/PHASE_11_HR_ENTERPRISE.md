# Fase 11 — RH Enterprise, portal do trabalhador e payroll

## Entregue

- Assiduidade em `attendance_records`.
- Pedidos de férias/licença em `leave_requests`.
- Organograma persistente em `org_positions`.
- Endpoint `/enterprise/hr/employee-portal`.
- Endpoint `/enterprise/hr/org-chart`, com geração idempotente de posições a partir dos trabalhadores, departamentos e cargos existentes.
- Endpoint `/enterprise/hr/positions` para criar posições vagas ou ocupadas, com supervisor e departamento.
- Processamentos salariais em `payroll_runs` e `payroll_items`.
- Endpoint `/enterprise/hr/payroll-runs`.
- UI “RH Enterprise” com portal, assiduidade, payroll e organograma.

O payroll demo calcula dedução padrão de 8% sobre o salário registado e deixa o processamento como rascunho para aprovação.
O organograma preserva dados existentes: quando não há posições manuais, o sistema cria posições a partir dos trabalhadores reais e liga subordinados ao responsável identificado no departamento.

## Validação

- `backend/tests/test_hr_workflows.py`
- `backend/tests/test_payroll.py`
- `npm --prefix frontend run build`
