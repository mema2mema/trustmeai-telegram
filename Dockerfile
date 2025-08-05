FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip \
 && pip install -r requirements.txt

EXPOSE 8000
CMD ["python", "main.py"]