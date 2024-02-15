FROM python:3.12 as builder

RUN pip install poetry==1.7.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --without dev --no-root

FROM python:3.12-slim as runtime

RUN pip install jinjanator jinjanator-plugin-ansible

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY docker/rootfs /

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY transmission_telegram_bot ./transmission_telegram_bot

ENTRYPOINT ["/docker-entrypoint.sh"]