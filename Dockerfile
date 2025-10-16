# =============================================================================
# kvs-infer: Multi-camera inference pipeline for Kinesis Video Streams
# GPU-enabled Docker image with CUDA support (OPTIMIZED for smaller size)
# =============================================================================

# Use PyTorch base image with CUDA 12.1 support
FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

# Metadata
LABEL maintainer="kvs-infer"
LABEL description="Multi-camera inference pipeline with GPU support"
LABEL version="1.1-optimized"

# Set working directory
WORKDIR /app

# Install system dependencies (minimal set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential only
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    ca-certificates \
    # Cleanup aggressively
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (optimized)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    # Remove pip cache
    rm -rf /root/.cache/pip && \
    # Remove unnecessary files
    find /opt/conda -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# Copy application code
COPY src/kvs_infer/ ./kvs_infer/

# Create config directory and copy config file
RUN mkdir -p ./config
COPY deployment/ecs/cameras-ecs.yaml ./config/cameras.yaml

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Create directories for models, logs, and cache
RUN mkdir -p /app/models /app/logs /app/.cache && \
    # Final cleanup
    rm -rf /tmp/* /var/tmp/* /root/.cache

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
