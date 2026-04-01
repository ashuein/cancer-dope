FROM rocker/r-ver:4.3

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    libcurl4-openssl-dev libssl-dev libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN R -e "install.packages(c('BiocManager'), repos='https://cloud.r-project.org')" && \
    R -e "BiocManager::install(c('fgsea', 'DESeq2'), ask=FALSE)"

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "backend.queue.worker", "--queue", "r"]
