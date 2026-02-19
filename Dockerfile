# Docker.fastapi
FROM python:latest
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
LABEL maintainer="work80@mail.ru"
LABEL description="FastAPI block for crypto market"
RUN mkdir /www && \
    mkdir /www/src
WORKDIR /www/src

RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org"
RUN python -m pip install --upgrade "pip>=25.0"

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir cryptomarket && \
    mkdir alembic && \
    mkdir collectstatic && \
    mkdir media
COPY alembic /www/src/alembic
COPY alembic.ini /www/src
COPY logs.py /www/src
