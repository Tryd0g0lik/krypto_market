# Docker.fastapi
FROM python:3.13
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/www/src
ENV PIP_CACHE_DIR=/var/cache/pip
LABEL maintainer="work80@mail.ru"
LABEL description="FastAPI block for crypto market"
RUN mkdir /www && \
    mkdir /www/src
WORKDIR /www/src
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org"
RUN python -m pip install --upgrade "pip>=25.0"

COPY ./requirements.txt /www/src/
COPY ./requirements-base.txt /www/src/
COPY ./requirements-db.txt /www/src/
COPY ./requirements-redis.txt /www/src/
RUN --mount=type=cache,target=/var/cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY . /www/src/
