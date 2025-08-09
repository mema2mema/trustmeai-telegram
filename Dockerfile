# Dockerfile (Production - Gunicorn)
FROM python:3.11-slim
WORKDIR /app

# Optional tools for building some wheels
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

ENV PYTHONUNBUFFERED=1

# Start Gunicorn; Railway provides $PORT
CMD ["python", "telegram_bot.py"]
