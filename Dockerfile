FROM python:3.11-slim

ARG CITY_GO_APP_VERSION=0.1.0
ARG CITY_GO_BUILD_SHA=local
ARG CITY_GO_BUILD_RUN_ID=local
ARG CITY_GO_BUILD_RUN_NUMBER=local
ARG CITY_GO_BUILD_TIME=local

ENV CITY_GO_APP_VERSION=$CITY_GO_APP_VERSION
ENV CITY_GO_BUILD_SHA=$CITY_GO_BUILD_SHA
ENV CITY_GO_BUILD_RUN_ID=$CITY_GO_BUILD_RUN_ID
ENV CITY_GO_BUILD_RUN_NUMBER=$CITY_GO_BUILD_RUN_NUMBER
ENV CITY_GO_BUILD_TIME=$CITY_GO_BUILD_TIME

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
