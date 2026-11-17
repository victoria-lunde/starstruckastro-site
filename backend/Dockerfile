FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python install_ephemeris.py --directory /app/ephe --asteroids
ENV PORT=8000
ENV EPHEMERIS_PATH=/app/ephe
CMD ["sh", "-c", "uvicorn service:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
