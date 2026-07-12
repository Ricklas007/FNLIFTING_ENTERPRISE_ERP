# Fase 3 — Operações técnicas

A Fase 3 fecha o primeiro fluxo operacional completo do ERP:

```text
Cliente → Equipamento → Inspeção + checklist → Aprovação → Certificado → PDF + QR
```

## Regras principais

- cada equipamento pertence a um cliente e a um tipo técnico;
- o tipo fornece o checklist inicial, copiado para a inspeção para garantir rastreabilidade;
- uma inspeção marcada como aprovada não aceita itens não conformes;
- apenas inspeções aprovadas e ainda não certificadas podem gerar um rascunho;
- a emissão é uma ação separada, regista o aprovador e gera o PDF;
- o QR aponta para a rota pública de validação e usa um token aleatório, não o UUID interno;
- o cliente externo vê apenas equipamentos e certificados ligados à sua empresa.

## Documento PDF

O gerador usa ReportLab e reproduz o documento oficial: logotipo, referência normativa, ordem de serviço, dados do cliente e local, legenda ND/SDR/NF, tabela WLL/SWL, datas do exame, códigos A–E, estado, segurança de utilização, dupla autenticação, carimbos, rodapé e QR. Os documentos ficam em `backend/data/certificates/` e são servidos somente após a verificação de acesso.

Cada inspetor ou supervisor autorizado possui um perfil técnico ligado ao cadastro de trabalhador. O perfil guarda qualificações, código, imagem da assinatura, imagem do carimbo e as competências `can_inspect`/`can_approve`. A emissão é bloqueada quando algum desses elementos está ausente; assim, o PDF sempre sai pronto e autenticado.

Para um ambiente publicado, configure a origem pública usada pelo QR para o domínio real da API. Em desenvolvimento, o endereço é `http://localhost:8000/api/v1/public/certificates/{token}`.

## Dados de demonstração

O seed cria cinco clientes, cinco tipos técnicos, dez equipamentos, seis inspeções e cinco certificados emitidos. Para restaurar esse estado:

```powershell
cd backend
python seed.py --reset
```

## Validação

Os testes de integração cobrem criação de cliente e equipamento, inspeção aprovada, rascunho, emissão, download do PDF e consulta pública do QR. O fluxo também foi validado nos portais interno e externo, incluindo isolamento multiempresa e viewport móvel.
