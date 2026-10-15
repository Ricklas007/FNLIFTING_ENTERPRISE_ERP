# Auditoria de ficheiros ausentes no GitHub

Com base no clone local, não existem ficheiros legítimos não commitados neste momento. Os artefactos gerados (instalador, APK, `win-unpacked`, `.runtime`, bases, backups, logs, `.env`) permanecem fora do Git por segurança e devem ser assets de Release, não commits.

## Commitado apenas localmente

- Commit `47f973b` (`build: package pilot release 0.12.2`) ainda está 1 commit à frente de `origin/main` no clone local.
- Os ficheiros do commit incluem a atualização de versão, documentação piloto e ajuste do build PyInstaller.

## Excluído por segurança

- `backend/.env` e `frontend/.env.local`: ignorados e não rastreados.
- Bases SQLite, backups, uploads, logs, `.runtime`, SDK/JDK/Gradle cache, `release/`, APK e instaladores: não devem entrar no histórico.

## Estado não comprovável

Sem fetch/API funcional, não é possível afirmar quais ficheiros do commit `47f973b` já existem no servidor. Essa comparação permanece pendente de autenticação/rede.
