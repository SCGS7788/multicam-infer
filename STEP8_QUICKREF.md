# Step 8: Quick Reference Card

## Common Commands

### 🚀 Quick Start

```bash
# Development (CPU-only)
docker-compose up

# Production (GPU)
make docker-run GPU=0 CONFIG=./config/cameras.yaml
```

### 📦 Development

```bash
# Create virtual environment
make venv

# Run locally
make run-local CONFIG=./config/cameras.example.yaml

# Run tests
make test

# Validate all steps
make validate
```

### 🐳 Docker - Local Build & Run

```bash
# Build image
make docker-build

# Run with GPU
make docker-run GPU=0 CONFIG=./config/cameras.yaml REGION=ap-southeast-1

# Run as daemon (background)
make docker-run-daemon GPU=0 CONFIG=./config/cameras.yaml

# View logs
make docker-logs

# Stop container
make docker-stop
```

### ☁️ AWS ECR Deployment

```bash
# Set ECR image URL
export IMG=123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/kvs-infer:latest

# Build
make docker-build IMG=$IMG

# Push to ECR
make docker-push IMG=$IMG

# On production server - pull and run
make docker-pull IMG=$IMG
make docker-run IMG=$IMG GPU=0 CONFIG=./config/prod.yaml REGION=ap-southeast-1
```

### 🔍 Monitoring

```bash
# Check health
make health
# or
curl http://localhost:8080/healthz

# View metrics
make metrics
# or
curl http://localhost:8080/metrics
```

### 🐙 Docker Compose (CPU-only)

```bash
# Start services (foreground)
docker-compose up

# Start services (background)
docker-compose up -d
# or
make docker-compose-daemon

# View logs
docker-compose logs -f
# or
make docker-compose-logs

# Stop services
docker-compose down
# or
make docker-compose-down
```

### 🧹 Cleanup

```bash
# Remove Python artifacts
make clean

# Remove virtual environment
make clean-venv

# Full cleanup (artifacts + venv + Docker images)
make clean-all
```

### ℹ️ Help & Info

```bash
# Show all Makefile targets
make help

# Show configuration
make info

# Show version
make version
```

## Environment Variables

### Required
```bash
AWS_REGION=ap-southeast-1
CONFIG_FILE=config/cameras.yaml
```

### Optional
```bash
LOG_LEVEL=INFO                    # DEBUG|INFO|WARNING|ERROR
HTTP_PORT=8080                    # HTTP server port
CUDA_VISIBLE_DEVICES=0            # GPU device ID (empty for CPU)
AWS_PROFILE=default               # Named AWS profile
```

### For docker-compose
```bash
# Create .env file from example
cp .env.example .env

# Edit variables
vim .env
```

## Makefile Variables (Override)

```bash
# Custom image name
make docker-build IMG=my-custom-image:v1.0

# Custom config file
make run-local CONFIG=./config/prod.yaml

# Custom GPU device
make docker-run GPU=1

# Custom AWS region
make docker-run REGION=us-west-2

# Custom HTTP port
make docker-run HTTP_PORT=9090

# Combine multiple overrides
make docker-run \
  IMG=kvs-infer:latest \
  GPU=0 \
  CONFIG=./config/cameras.yaml \
  REGION=ap-southeast-1 \
  HTTP_PORT=8080
```

## Validation

```bash
# Run Step 8 validation
python3 validate_step8.py

# Should output: All checks passed (8/8)
```

## Troubleshooting

### Port Already in Use
```bash
# Use different port
make docker-run HTTP_PORT=8081
# or
HTTP_PORT=8081 docker-compose up
```

### NVIDIA Runtime Not Found
```bash
# Install nvidia-docker2
sudo apt-get install nvidia-docker2
sudo systemctl restart docker
```

### AWS Credentials Not Found
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

### Config File Not Found
```bash
# Check if config exists
ls -la config/cameras.yaml

# Use example config
cp config/cameras.example.yaml config/cameras.yaml
```

## File Locations

```
multicam-infer/
├── Dockerfile                # GPU-enabled container
├── Makefile                  # 40+ build automation targets
├── docker-compose.yml        # CPU-only testing
├── .env.example              # Environment variable template
├── validate_step8.py         # Validation script
├── STEP8_COMPLETE.md         # Full documentation
├── STEP8_STATUS.md           # Status summary
├── STEP8_SUMMARY.md          # Implementation summary
└── STEP8_QUICKREF.md         # This file
```

## Quick Architecture

```
Developer → make venv → make run-local (CPU)
                     ↓
                 make docker-build
                     ↓
              make docker-push (ECR)
                     ↓
Production → make docker-pull → make docker-run (GPU)
                                        ↓
                                   Port 8080
                                   /healthz
                                   /metrics
                                        ↓
                                   AWS Services
                                   (KVS, KDS, S3)
```

## Endpoints

```
Health Check:    http://localhost:8080/healthz
Prometheus:      http://localhost:8080/metrics
```

## Status: ✅ COMPLETE

All validation checks passed (8/8)  
Ready for production deployment testing

---

For detailed documentation, see:
- **[STEP8_COMPLETE.md](./STEP8_COMPLETE.md)** - Full guide
- **[STEP8_STATUS.md](./STEP8_STATUS.md)** - Status summary
- **[STEP8_SUMMARY.md](./STEP8_SUMMARY.md)** - Implementation details
