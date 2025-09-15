# syntax=docker/dockerfile:1
FROM python:3.13-slim

LABEL maintainer="Noah Krieger"
LABEL application="GlobeCo Security Service"

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Install uv (universal package manager)
RUN pip install --upgrade pip && pip install uv

# Set work directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Start the FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"] 