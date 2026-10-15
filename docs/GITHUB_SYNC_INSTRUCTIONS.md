# Instruções de sincronização pendente

1. Confirmar `gh auth status` sem revelar tokens.
2. Executar `git fetch --all --tags --prune`.
3. Rever `git rev-list --left-right --count origin/main...HEAD`.
4. Se `origin/main` continuar ancestral, executar `git push origin main`.
5. Confirmar `git rev-parse HEAD` contra `git rev-parse origin/main`.
6. Criar uma GitHub pre-release para 0.12.2 apenas no commit confirmado, anexando o instalador Windows, APK debug e checksums.
7. Consultar a release e comparar tamanhos/SHA-256.
8. Executar um segundo push se esta documentação for criada depois do primeiro push.

Não usar `git push --force`, `git push --mirror`, `git reset --hard` ou incluir `.env`, bases, backups, SDKs, caches ou binários no Git.
