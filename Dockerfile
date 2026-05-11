FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_PATH=/app/data/relay_bot.sqlite3

WORKDIR /app

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends gosu; \
    rm -rf /var/lib/apt/lists/*; \
    groupadd --system relay \
    && useradd --system --gid relay --home-dir /app relay

COPY pyproject.toml README.md ./
COPY src ./src
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && mkdir -p /app/data /app/exports \
    && chown -R relay:relay /app \
    && chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["relay-bot"]
