# Docker.fastapi
FROM python:3.13
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_CACHE_DIR=/var/cache/pip
LABEL maintainer="work80@mail.ru"
LABEL description="FastAPI block for crypto market"
RUN mkdir /www && \
    mkdir /www/src
WORKDIR /www/src

RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org"
RUN python -m pip install --upgrade "pip>=25.0"

COPY ./requirements.txt .
COPY ./requirements-base.txt .
COPY ./requirements-db.txt .
COPY ./requirements-redis.txt .
RUN --mount=type=cache,target=/var/cache/pip \
    pip install --no-cache-dir -r requirements.txt
RUN mkdir -p cryptomarket alembic collectstatic media
COPY alembic /www/src/alembic
COPY alembic.ini /www/src
COPY logs.py /www/src
