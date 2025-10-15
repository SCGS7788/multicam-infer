# Step 8: Local Run Scripts + Dockerfile - COMPLETE ✅

**Status:** Complete and Validated  
**Date:** 2024  
**Validation:** 8/8 checks passed

## Overview

Step 8 implements a complete Docker deployment infrastructure for the multi-camera inference pipeline, including GPU-accelerated production deployment and CPU-only local testing capabilities.

## What Was Implemented

### 1. Enhanced Dockerfile (80 lines)
- **Base Image:** `pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime`
- **GPU Support:** CUDA 12.1 with cuDNN 8
- **Port:** Exposes 8080 for HTTP server
- **Health Check:** curl-based endpoint check at `/healthz`
- **AWS Integration:** Environment variables for AWS_REGION and credential chain
- **System Dependencies:** ffmpeg, OpenCV libraries, curl, wget, git
- **Python Dependencies:** Installed from requirements.txt
- **Entry Point:** `python -m kvs_infer.app --config config/cameras.yaml --http 0.0.0.0:8080`

### 2. Comprehensive Makefile (380+ lines)

#### Core Development Targets
- **`make venv`** - Create Python virtual environment and install dependencies
- **`make venv-dev`** - Create venv with dev tools (pytest, black, flake8, mypy)
- **`make run-local CONFIG=./config/cameras.yaml`** - Run locally with AWS_REGION env var
- **`make run-venv`** - Run inside virtual environment

#### Docker Build Targets
- **`make docker-build IMG=<image-name>`** - Build Docker image for linux/amd64
- **`make docker-build-no-cache`** - Build without cache
- **`make info`** - Show configuration (Python version, Docker version, variables)
- **`make version`** - Show project version

#### Docker Run Targets (GPU)
```bash
make docker-run \
  IMG=kvs-infer:latest \
  CONFIG=./config/cameras.yaml \
  GPU=0 \
  REGION=ap-southeast-1 \
  HTTP_PORT=8080
```
- Uses `--gpus "device=$(GPU)"` and `--runtime=nvidia`
- Mounts config (read-only) and models (read-only)
- Injects AWS credentials from shell environment
- Maps HTTP port for metrics and health checks

- **`make docker-run-daemon`** - Run as background daemon
- **`make docker-stop`** - Stop running container
- **`make docker-logs`** - View container logs
- **`make docker-shell`** - Open shell inside container

#### Docker Compose Targets (CPU)
- **`make docker-compose-up`** - Start with docker-compose (foreground, CPU-only)
- **`make docker-compose-daemon`** - Start as background daemon
- **`make docker-compose-down`** - Stop and remove containers
- **`make docker-compose-logs`** - View compose logs

#### AWS ECR Targets
```bash
make docker-push IMG=123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/kvs-infer:latest
```
- **`make ecr-login`** - Automatically parse account/region from IMG and login
- **`make docker-push`** - Login and push image to ECR
- **`make docker-pull`** - Login and pull image from ECR

#### Testing & Validation Targets
- **`make test`** - Run pytest tests/
- **`make test-venv`** - Run tests in virtual environment
- **`make validate`** - Run all validate_step*.py scripts
- **`make lint`** - Run flake8 linter

#### Monitoring Targets
- **`make health`** - Check health endpoint at http://localhost:8080/healthz
- **`make metrics`** - View Prometheus metrics at http://localhost:8080/metrics

#### Cleanup Targets
- **`make clean`** - Remove Python artifacts (__pycache__, *.pyc)
- **`make clean-venv`** - Remove virtual environment
- **`make clean-all`** - Full cleanup (artifacts + venv + Docker images)

### 3. Docker Compose Configuration (130+ lines)

**CPU-Only Local Testing**
```yaml
services:
  kvs-infer:
    container_name: kvs-infer-cpu
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${HTTP_PORT:-8080}:8080"
    volumes:
      - ./config/cameras.yaml:/app/config/cameras.yaml:ro
      - ./models:/app/models:ro
      - ./logs:/app/logs:rw
    environment:
      - CUDA_VISIBLE_DEVICES=""  # CPU-only
      - AWS_REGION=${REGION:-us-east-1}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    restart: unless-stopped
```

**Features:**
- CPU-only execution (CUDA_VISIBLE_DEVICES="")
- Health checks every 30 seconds
- Resource limits (4 CPUs, 8GB RAM)
- Logging with rotation (10MB, 3 files)
- Bridge networking
- Optional Prometheus/Grafana services (commented out)

### 4. Environment Configuration (.env.example - 130+ lines)

**AWS Configuration:**
```bash
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
# AWS_ACCESS_KEY_ID=AKIA...  # Optional, use IAM roles preferred
# AWS_SECRET_ACCESS_KEY=...  # Optional
# AWS_SESSION_TOKEN=...      # Optional for temporary credentials
AWS_PROFILE=default          # Optional, use named profile
```

**Application Configuration:**
```bash
LOG_LEVEL=INFO
HTTP_HOST=0.0.0.0
HTTP_PORT=8080
CONFIG_FILE=config/cameras.yaml
```

**CUDA/GPU Configuration:**
```bash
CUDA_VISIBLE_DEVICES=0  # GPU device ID, or empty for CPU
TORCH_HOME=/app/.cache/torch
CUDA_DEVICE_ORDER=PCI_BUS_ID
```

**Comprehensive Notes:**
- AWS credential chain priority explained
- Region configuration options
- Docker usage examples
- Local development setup
- Production deployment best practices

## Validation Results

All 8 validation checks passed:

1. ✅ **Dockerfile** - Structure and GPU support verified
2. ✅ **Makefile** - All required targets present
3. ✅ **docker-compose.yml** - Valid structure and CPU configuration
4. ✅ **.env.example** - All required variables documented
5. ✅ **Config Example** - cameras.example.yaml exists and valid
6. ✅ **Makefile Syntax** - Valid GNU Make syntax
7. ✅ **docker-compose Syntax** - Valid Compose v3.8 syntax
8. ✅ **Port Configuration** - Port 8080 correctly configured everywhere

Run validation: `python3 validate_step8.py`

## Usage Examples

### Local Development (CPU)

```bash
# Create virtual environment
make venv

# Run locally
make run-local CONFIG=./config/cameras.example.yaml

# Or with docker-compose (CPU-only)
docker-compose up
```

### GPU Production Deployment

```bash
# Build image
make docker-build IMG=kvs-infer:latest

# Run with GPU 0
make docker-run GPU=0 CONFIG=./config/cameras.yaml REGION=ap-southeast-1

# Run as background daemon
make docker-run-daemon GPU=0 CONFIG=./config/cameras.yaml
```

### AWS ECR Deployment

```bash
# Set image name with ECR URL
IMG=123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/kvs-infer:latest

# Build and push to ECR
make docker-build IMG=$IMG
make docker-push IMG=$IMG

# On production server, pull and run
make docker-pull IMG=$IMG
make docker-run IMG=$IMG GPU=0 CONFIG=./config/prod.yaml REGION=ap-southeast-1
```

### Health Monitoring

```bash
# Check health
make health

# View metrics
make metrics

# View logs
make docker-logs
# or
make docker-compose-logs
```

## AWS Credential Chain

The application uses boto3's automatic credential chain (no explicit reading required):

1. **Environment variables** - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
2. **Shared credentials file** - ~/.aws/credentials
3. **IAM role** - For ECS tasks, EC2 instances, Lambda functions
4. **Container credentials** - For ECS tasks with task role

**Best Practices:**
- ✅ **Production:** Use IAM roles (ECS task role, EC2 instance profile)
- ✅ **Development:** Use AWS_PROFILE with named profiles
- ⚠️ **Avoid:** Hardcoding credentials in environment files

## File Structure

```
multicam-infer/
├── Dockerfile                  # GPU-enabled container (80 lines)
├── Makefile                    # Build automation (380+ lines)
├── docker-compose.yml          # CPU-only testing (130+ lines)
├── .env.example                # Environment variables (130+ lines)
├── validate_step8.py           # Validation script
├── config/
│   ├── cameras.yaml           # Production config
│   └── cameras.example.yaml   # Example config
├── models/                     # Model weights (mounted read-only)
├── logs/                       # Application logs (mounted read-write)
└── src/kvs_infer/
    └── app.py                 # Main application entry point
```

## Key Features

### Security
- ✅ AWS credential chain (no hardcoded credentials)
- ✅ Read-only config and model mounts
- ✅ Non-root user in Docker (optional, can be added)
- ✅ Health checks for container monitoring

### Performance
- ✅ GPU acceleration with NVIDIA runtime
- ✅ CUDA 12.1 + cuDNN 8 for optimal inference
- ✅ Resource limits prevent runaway processes
- ✅ Platform-specific builds (linux/amd64)

### Observability
- ✅ Prometheus metrics at /metrics
- ✅ Health endpoint at /healthz
- ✅ Structured logging with configurable levels
- ✅ Log rotation (10MB, 3 files)

### Developer Experience
- ✅ 40+ Makefile targets with color-coded output
- ✅ Virtual environment management
- ✅ One-command testing and deployment
- ✅ Comprehensive documentation

## Testing the Implementation

### 1. Test Makefile Help
```bash
make help
```

### 2. Test Virtual Environment
```bash
make venv
source venv/bin/activate
python -c "import torch; print(torch.__version__)"
```

### 3. Test Docker Build
```bash
make docker-build
docker images | grep kvs-infer
```

### 4. Test Docker Compose (CPU)
```bash
docker-compose up
# In another terminal:
curl http://localhost:8080/healthz
curl http://localhost:8080/metrics
```

### 5. Test GPU Run (requires NVIDIA GPU)
```bash
make docker-run GPU=0 CONFIG=./config/cameras.example.yaml
```

### 6. Test ECR Push (requires AWS credentials)
```bash
IMG=123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/kvs-infer:latest
make ecr-login IMG=$IMG
```

## Common Issues & Solutions

### Issue: NVIDIA runtime not found
**Solution:** Install nvidia-docker2:
```bash
# Ubuntu/Debian
sudo apt-get install nvidia-docker2
sudo systemctl restart docker
```

### Issue: Port 8080 already in use
**Solution:** Use different port:
```bash
make docker-run HTTP_PORT=8081
# or
HTTP_PORT=8081 docker-compose up
```

### Issue: AWS credentials not found
**Solution:** Check credential chain:
```bash
# Option 1: Environment variables
export AWS_REGION=ap-southeast-1
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# Option 2: Named profile
export AWS_PROFILE=my-profile

# Option 3: Use IAM role (production)
# No explicit credentials needed
```

### Issue: Config file not found
**Solution:** Ensure config exists:
```bash
ls -la config/cameras.yaml
# or use example
cp config/cameras.example.yaml config/cameras.yaml
```

## Next Steps

1. **Test GPU deployment** on production server
2. **Set up ECR repository** for image storage
3. **Configure CI/CD pipeline** for automated builds
4. **Add monitoring dashboards** (Grafana + Prometheus)
5. **Implement rolling updates** for zero-downtime deployment
6. **Add horizontal scaling** with multiple GPU instances

## Related Documentation

- [Dockerfile Reference](./Dockerfile)
- [Makefile Targets](./Makefile)
- [Docker Compose Guide](./docker-compose.yml)
- [Environment Variables](./.env.example)
- [Step 7: ROI & Temporal Smoothing](./STEP7_COMPLETE.md)

---

**Step 8 Status:** ✅ Complete and validated (8/8 checks)  
**Ready for:** Production deployment testing
