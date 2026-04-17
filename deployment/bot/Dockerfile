FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc procps && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ core/
COPY bot/ bot/

COPY deployment/bot/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN mkdir -p logs data

ENTRYPOINT ["/entrypoint.sh"]
