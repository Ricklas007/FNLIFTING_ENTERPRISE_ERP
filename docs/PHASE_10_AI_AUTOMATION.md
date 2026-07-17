# Fase 10 — IA, OCR, regras e automação

## Entregue

- Providers de IA/OCR/regras em `ai_provider_settings`.
- OCR jobs em `/enterprise/ai/ocr/jobs`.
- Centro de automação em `/enterprise/ai/automation`.
- Regras enterprise iniciais para certificados, frota e documentos.
- Assistente de decisões local em `/enterprise/ai/assistant`.
- Geração idempotente de sugestões a partir de OCR pendente e regras ativas em `/enterprise/ai/assistant/generate`.
- Revisão humana de sugestões com aceitar, editar ou descartar em `PATCH /enterprise/ai/assistant/{suggestion_id}`.
- UI “IA & Automação” com providers, regras, fila OCR e sugestões persistidas.

OCR local gera extrações com estado `review_required`, mantendo revisão humana antes da aprovação documental.
O assistente não chama provider externo sem credenciais/configuração; ele opera de forma determinística sobre dados reais do ERP e preserva trilho de revisão.

## Validação

- `backend/tests/test_ai_ocr_rules.py`
- `npm --prefix frontend run build`
