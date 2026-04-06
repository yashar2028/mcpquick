FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_HOME=/opt/poetry \
    PATH="/opt/poetry/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libpq-dev \
        nix-bin \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system nixbld \
    && for n in $(seq 1 10); do \
        useradd --system --no-create-home --home-dir /var/empty --shell /usr/sbin/nologin --groups nixbld "nixbld${n}"; \
    done

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --with dev --no-interaction --no-ansi --no-root

COPY . .

EXPOSE 8000

CMD ["bash", "-lc", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
