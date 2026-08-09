# Full ComicEngine admin (stats, library, curation, ROI)
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY dashboard ./dashboard
COPY scripts ./scripts
COPY data ./data
COPY outputs ./outputs
COPY reports ./reports

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e .

ENV DASHBOARD_HOST=0.0.0.0
ENV DASHBOARD_PORT=8765
ENV BETA_REQUIRE_LOGIN=0
ENV PYTHONPATH=/app/src:/app/dashboard

EXPOSE 8765
CMD ["python", "scripts/run_dashboard.py"]
