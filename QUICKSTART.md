# Quick Start Guide for kvs-infer

## Step 0 — Bootstrap Complete! ✅

You now have a fully scaffolded Python 3.11 project with:
- ✅ Source layout (`src/kvs_infer/`)
- ✅ All modules implemented with minimal boilerplate
- ✅ Configuration management with Pydantic
- ✅ Detector framework with YOLO support
- ✅ Publisher integrations (KDS, S3, DynamoDB)
- ✅ Utilities (logging, metrics, ROI)
- ✅ Docker support
- ✅ Example configuration

## Next Steps

### 1. Install Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Note**: This will install all dependencies including PyTorch, Ultralytics YOLO, PaddleOCR, etc. It may take a few minutes.

### 2. Test the Application

```bash
# Quick test - see help output
./run.sh --help

# Or with PYTHONPATH
PYTHONPATH=src python -m kvs_infer.app --help
```

Expected output:
```
usage: app.py [-h] [--config CONFIG] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--log-format {json,text}]

kvs-infer: Multi-camera inference pipeline for Kinesis Video Streams
...
```

### 3. Configure Your Cameras

```bash
# Copy example config
cp config/cameras.example.yaml config/cameras.yaml

# Edit with your settings
vim config/cameras.yaml  # or use your favorite editor
```

Update:
- AWS region
- KVS stream names
- Detector settings
- Publisher configuration (Kinesis stream, S3 bucket, etc.)

### 4. AWS Credentials

Make sure you have AWS credentials configured:

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-east-1"

# Option 2: AWS CLI profile
aws configure

# Option 3: IAM role (if running on EC2/ECS)
# Credentials will be automatically retrieved
```

### 5. Run the Application

```bash
# Run with default config
./run.sh

# Run with custom config
./run.sh --config config/cameras.yaml

# Run with debug logging
./run.sh --log-level DEBUG --log-format text

# Run with editable install (for development)
pip install -e .
kvs-infer --config config/cameras.yaml
```

### 6. Monitor Metrics

While the application is running:

```bash
# View Prometheus metrics
curl http://localhost:9090/metrics

# Or open in browser
open http://localhost:9090/metrics
```

### 7. Docker Deployment

```bash
# Build image
docker build -t kvs-infer:latest .

# Run container
docker run -d \
  --name kvs-infer \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/models:/app/models \
  -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  -e AWS_DEFAULT_REGION="us-east-1" \
  -p 9090:9090 \
  kvs-infer:latest

# View logs
docker logs -f kvs-infer

# Stop container
docker stop kvs-infer
```

### 8. GPU Support (Optional)

If you have NVIDIA GPU:

```bash
# Update config to use GPU
device: cuda:0  # in cameras.yaml

# Run with GPU in Docker
docker run -d \
  --name kvs-infer \
  --gpus all \
  -v $(pwd)/config:/app/config \
  -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  -p 9090:9090 \
  kvs-infer:latest
```

## Project Structure Overview

```
multicam-infer/
├── src/kvs_infer/           # Main application package
│   ├── app.py               # Entry point & process manager
│   ├── config.py            # Configuration models
│   ├── frame_source/        # Video stream readers
│   ├── detectors/           # Detection models
│   ├── publishers/          # Event publishers
│   └── utils/               # Utilities
├── config/                  # Configuration files
│   └── cameras.example.yaml # Example config
├── requirements.txt         # Python dependencies
├── setup.py                 # Package setup
├── run.sh                   # Convenience script
├── Dockerfile               # Docker image
└── README.md                # Documentation
```

## Common Commands

```bash
# Development mode install
pip install -e .

# Run with help
./run.sh --help
kvs-infer --help  # after pip install -e .

# Run with custom config
./run.sh --config config/cameras.yaml

# Run with text logs (easier to read during dev)
./run.sh --log-format text

# Check code structure
tree src/

# Run in Docker
docker build -t kvs-infer . && docker run --rm kvs-infer --help
```

## Testing Individual Components

### Test Configuration Loading

```python
from pathlib import Path
from kvs_infer.config import load_config

config = load_config(Path("config/cameras.example.yaml"))
print(f"Loaded {len(config.cameras)} cameras")
```

### Test Detector

```python
import numpy as np
from kvs_infer.detectors import DetectorRegistry

# Create detector
detector = DetectorRegistry.create(
    "weapon",
    confidence_threshold=0.5,
    device="cpu"
)

# Test with dummy frame
frame = np.zeros((640, 640, 3), dtype=np.uint8)
result = detector.detect(frame)
print(f"Detections: {len(result.detections)}")
```

## Troubleshooting

### Module not found
```bash
# Make sure PYTHONPATH is set
export PYTHONPATH=$(pwd)/src:$PYTHONPATH
# Or use the run.sh script
./run.sh --help
```

### Dependencies missing
```bash
# Reinstall all dependencies
pip install --force-reinstall -r requirements.txt
```

### CUDA errors
```bash
# Check if CUDA is available
python -c "import torch; print(torch.cuda.is_available())"
# If False, use CPU in config: device: cpu
```

## What's Next?

1. **Implement frame processing loop** in `src/kvs_infer/app.py` (`CameraWorker.start()`)
2. **Add custom detector models** by training YOLO on your specific use case
3. **Optimize performance** with frame skipping, ROI filtering, model optimization
4. **Add health checks** and monitoring dashboards
5. **Deploy to production** on EC2, ECS, or EKS

## Support

- Check `README.md` for detailed documentation
- Example config in `config/cameras.example.yaml`
- All modules have docstrings with usage examples

Happy coding! 🚀
