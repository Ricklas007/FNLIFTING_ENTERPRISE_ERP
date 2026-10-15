# Rollback piloto

Antes do empacotamento foi criada e validada a cópia `C:\Projetos\FNLIFTING_ENTERPRISE_ERP\.runtime\pilot-backup-20261015-143218.db` (SHA-256 `5B6DDCEEE8A39BA38F8D276B1A6F132474B65B5DF5BEF61748C8C53A0E658D42`; `PRAGMA quick_check=ok`).

Desinstale 0.12.2 sem remover `%APPDATA%`/`app.getPath("userData")`, reinstale a versão anterior e restaure a cópia apenas com a aplicação fechada. Não substituir a base original sem cópia adicional.
