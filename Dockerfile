# Multi-stage or direct production Dockerfile for Liara PaaS
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend application and pre-indexed database
COPY backend/ ./backend/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PORT=80

EXPOSE 80

# Run FastAPI app via uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "80"]
