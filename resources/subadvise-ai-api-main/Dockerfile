FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN groupadd --system app \
    && useradd --system --gid app --create-home app \
    && mkdir -p /app/data/chat_history /app/data/chroma_db \
    && chown -R app:app /app

USER app

EXPOSE 7072

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7072/openapi.json', timeout=3)"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7072"]