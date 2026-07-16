# Backend Standalone Build

## Comandos

```powershell
npm run desktop:backend:clean
npm run desktop:backend:build
npm run desktop:backend:smoke
```

## Saida

```text
backend-dist/FNLiftingBackend/FNLiftingBackend.exe
```

## Comandos do executavel

```powershell
FNLiftingBackend.exe migrate
FNLiftingBackend.exe seed
FNLiftingBackend.exe serve
FNLiftingBackend.exe run
```

## Inclui

- FastAPI;
- Uvicorn;
- SQLAlchemy;
- Alembic;
- migrations;
- ReportLab/PDF;
- QR/barcodes;
- assets de certificados.

## Nao inclui

- `.venv`;
- `.env`;
- bancos SQLite de desenvolvimento;
- testes;
- pytest;
- caches.

## Smoke validado

`npm run desktop:backend:smoke` passou em runtime temporario fora do projeto, com migrate, seed, serve e `/ready`.
