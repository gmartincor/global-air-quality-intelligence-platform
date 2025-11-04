FROM python:3.10-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        build-essential \
        openjdk-21-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

FROM base AS dev

ENV POETRY_VERSION=1.7.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s $POETRY_HOME/bin/poetry /usr/local/bin/poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN if [ -f poetry.lock ]; then \
        poetry install --no-root --no-interaction --no-ansi; \
    else \
        poetry lock --no-interaction && \
        poetry install --no-root --no-interaction --no-ansi; \
    fi

CMD ["/bin/bash"]

FROM apache/airflow:2.7.0-python3.10 AS airflow

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-11-jre-headless \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

RUN pip install --no-cache-dir --user \
    boto3==1.34.* \
    boto3-stubs[s3,kinesis,dynamodb]==1.34.* \
    pydantic==2.5.* \
    pydantic-settings==2.1.* \
    pyyaml==6.0.* \
    pyspark==3.5.* \
    delta-spark==3.0.*
