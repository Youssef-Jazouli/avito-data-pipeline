FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

RUN which chromedriver || (find / -name chromedriver 2>/dev/null | head -5)

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper/ ./scraper/
COPY staging/ ./staging/
COPY clean/ ./clean/
COPY warehouse/ ./warehouse/
COPY pipeline/ ./pipeline/

RUN mkdir -p logs data

CMD ["python", "-u", "pipeline/run_pipeline.py"]