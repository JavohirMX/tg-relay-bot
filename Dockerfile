FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_PATH=/app/data/relay_bot.sqlite3

WORKDIR /app

RUN groupadd --system relay \
    && useradd --system --gid relay --home-dir /app relay

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && mkdir -p /app/data /app/exports \
    && chown -R relay:relay /app

USER relay

CMD ["relay-bot"]
