FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" fnlifting

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY alembic ./alembic
COPY alembic.ini .
COPY app ./app
COPY seed.py .
COPY tools ./tools

RUN mkdir -p /app/data/backups /app/data/certificates /app/data/documents /app/data/financial /app/data/signatures \
    && chown -R fnlifting:fnlifting /app

USER fnlifting
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=5)"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2}"]

