# Use slim base to reduce build time
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy all files to container
COPY . .

# Install dependencies
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Run the bot
CMD ["python", "main.py"]
