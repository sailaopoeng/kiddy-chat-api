# Use Python 3.11 slim image for AWS App Runner compatibility
FROM python:3.11-slim

# Set environment variables for proper logging
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (AWS App Runner uses 8080 by default)
EXPOSE 8080

# Run the application with direct Python for better logging visibility
# Alternative options for production (commented out):
# CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--error-logfile", "-"]
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
CMD ["python3", "main.py"]