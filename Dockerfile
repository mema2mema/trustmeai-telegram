# Use stable Python slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Python packages (numpy, pandas, etc.)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files into container
COPY . .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "main.py"]
