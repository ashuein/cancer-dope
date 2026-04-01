FROM python:3.8-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY docker/requirements-pvactools.txt .
RUN pip install --no-cache-dir -r requirements-pvactools.txt

COPY backend/ ./backend/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "backend.queue.worker", "--queue", "pvactools"]
