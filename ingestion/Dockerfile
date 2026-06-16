FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --uid 10001 docsuri

COPY shared/python /app/shared/python
COPY ingestion /app/ingestion

RUN python -m pip install --upgrade pip==24.2 \
    && python -m pip install /app/shared/python /app/ingestion

USER docsuri

ENTRYPOINT ["python", "-m", "docsuri_ingestion.worker"]
