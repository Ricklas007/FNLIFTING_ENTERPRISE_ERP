# Segurança Enterprise

## Implementado

- JWT com sessões revogáveis.
- MFA TOTP opcional por utilizador.
- Códigos de recuperação com hash PBKDF2.
- Eventos de segurança.
- Headers de segurança.
- RBAC por permissão.
- Backup cifrado local.
- Preview documental antes de download/aprovação.

## Recomendações antes de produção aberta

- Tornar MFA obrigatório para perfis sensíveis.
- Rodar `SECRET_KEY` fora de ficheiros locais.
- Configurar `ALLOWED_HOSTS` e `CORS_ORIGINS` restritos.
- Usar PostgreSQL/volume cifrado.
