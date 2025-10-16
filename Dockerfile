# =============================================================================
# kvs-infer: Multi-camera inference pipeline for Kinesis Video Streams
# GPU-enabled Docker image with CUDA support
# =============================================================================

# Use PyTorch base image with CUDA 12.1 support
FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

# Metadata
LABEL maintainer="kvs-infer"
LABEL description="Multi-camera inference pipeline with GPU support"
LABEL version="1.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Video processing
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Networking
    curl \
    wget \
    # Development tools
    git \
    vim \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/kvs_infer/ ./kvs_infer/

# Create config directory and copy config file
RUN mkdir -p ./config
COPY deployment/ecs/cameras-ecs.yaml ./config/cameras.yaml

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Create directories for models, logs, and cache
RUN mkdir -p /app/models /app/logs /app/.cache

# Environment variables
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# AWS credentials (will be overridden by runtime env vars or IAM role)
# Set these via -e flags or docker-compose environment section
ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1

# Expose HTTP server port (metrics + health)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Default command (override with docker run command)
# Usage: docker run kvs-infer
CMD ["python", "-m", "kvs_infer", "--config", "config/cameras.yaml", "--http", "0.0.0.0:8080"]
