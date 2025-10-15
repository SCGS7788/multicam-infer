# kvs-infer

Multi-camera inference pipeline for AWS Kinesis Video Streams. Runs object detection, ALPR, and fire/smoke detection on video streams and publishes events to Kinesis Data Streams with snapshots uploaded to S3.

## Features

- 🎥 **Multi-camera support**: Process multiple KVS streams concurrently
- 🔍 **Multiple detectors**: Weapon detection, fire/smoke detection, ALPR (license plate recognition)
- 🎯 **ROI support**: Define regions of interest for focused detection
- 📊 **Prometheus metrics**: Built-in monitoring and metrics
- 🚀 **GPU support**: CUDA acceleration for faster inference
- 📦 **Event publishing**: Send events to Kinesis Data Streams, upload to S3, store in DynamoDB
- 🔧 **Flexible configuration**: YAML-based per-camera configuration

## Architecture

```
┌─────────────────┐
│  Kinesis Video  │
│     Streams     │
└────────┬────────┘
         │ HLS
         ▼
┌─────────────────┐
│  Frame Source   │
│   (kvs_hls)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Detectors     │
│ YOLO / PaddleOCR│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Publishers    │
│  KDS / S3 / DDB │
└─────────────────┘
```

## Quick Start

### Local Development

1. **Clone and setup**:
```bash
cd multicam-infer
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure cameras**:
```bash
cp config/cameras.example.yaml config/cameras.yaml
# Edit config/cameras.yaml with your camera settings
```

3. **Run the application**:
```bash
python -m kvs_infer.app --config config/cameras.yaml
```

4. **View metrics**:
```bash
# Metrics available at http://localhost:9090/metrics
curl http://localhost:9090/metrics
```

### Docker

1. **Build image**:
```bash
docker build -t kvs-infer:latest .
```

2. **Run container**:
```bash
docker run -d \
  --name kvs-infer \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/models:/app/models \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -p 9090:9090 \
  kvs-infer:latest
```

3. **Run with GPU** (NVIDIA Docker):
```bash
docker run -d \
  --name kvs-infer \
  --gpus all \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/models:/app/models \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -p 9090:9090 \
  kvs-infer:latest
```

## Configuration

### Camera Configuration

Edit `config/cameras.yaml`:

```yaml
aws_region: us-east-1
device: cuda:0  # or "cpu"

cameras:
  - name: front-door
    stream_name: my-kvs-stream
    region: us-east-1
    fps_limit: 5
    
    detectors:
      - type: weapon
        enabled: true
        confidence_threshold: 0.6
    
    publishers:
      kinesis_stream_name: detection-events
      s3_bucket: my-bucket
```

See `config/cameras.example.yaml` for full configuration options.

### Detector Types

- **`weapon`**: Detect guns, knives, weapons
- **`fire_smoke`**: Detect fire and smoke
- **`alpr`**: License plate detection and OCR

### Publishers

- **Kinesis Data Streams**: Publish JSON events
- **S3**: Upload full snapshots and detection crops
- **DynamoDB**: Store detection metadata (optional)

## AWS Requirements

### IAM Permissions

Your IAM role/user needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesisvideo:GetDataEndpoint",
        "kinesisvideo:DescribeStream"
      ],
      "Resource": "arn:aws:kinesisvideo:*:*:stream/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kinesisvideo:GetHLSStreamingSessionURL"
      ],
      "Resource": "arn:aws:kinesisvideo:*:*:stream/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:PutRecord",
        "kinesis:PutRecords"
      ],
      "Resource": "arn:aws:kinesis:*:*:stream/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket/*"
    }
  ]
}
```

## Development

### Project Structure

```
kvs-infer/
├── src/kvs_infer/
│   ├── app.py                    # Main application
│   ├── config.py                 # Configuration management
│   ├── frame_source/             # Video stream readers
│   │   ├── kvs_hls.py            # KVS HLS reader
│   │   └── getmedia_stub.py      # Low-latency path (future)
│   ├── detectors/                # Detection models
│   │   ├── base.py               # Detector interface
│   │   ├── yolo_common.py        # YOLO utilities
│   │   ├── weapon.py             # Weapon detection
│   │   ├── fire_smoke.py         # Fire/smoke detection
│   │   └── alpr.py               # License plate recognition
│   ├── publishers/               # Event publishers
│   │   ├── kds.py                # Kinesis Data Streams
│   │   ├── s3.py                 # S3 uploads
│   │   └── ddb.py                # DynamoDB storage
│   └── utils/                    # Utilities
│       ├── log.py                # Logging
│       ├── metrics.py            # Prometheus metrics
│       ├── roi.py                # ROI utilities
│       └── time.py               # Time utilities
├── config/
│   └── cameras.example.yaml      # Example configuration
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
└── README.md                     # This file
```

### Adding Custom Detectors

1. Create a new detector class in `src/kvs_infer/detectors/`:

```python
from kvs_infer.detectors.base import Detector, DetectorRegistry

@DetectorRegistry.register("my_detector")
class MyDetector(Detector):
    def detect(self, frame):
        # Your detection logic
        pass
    
    def warmup(self):
        # Warmup logic
        pass
```

2. Add to configuration:

```yaml
detectors:
  - type: my_detector
    enabled: true
    confidence_threshold: 0.5
```

## Monitoring

### Prometheus Metrics

Metrics are exposed at `http://localhost:9090/metrics`:

- `kvs_infer_frames_processed_total`: Total frames processed
- `kvs_infer_detections_total`: Total detections by type
- `kvs_infer_inference_seconds`: Inference time histogram
- `kvs_infer_events_published_total`: Published events
- `kvs_infer_stream_errors_total`: Stream errors

### Logs

Structured JSON logs to stdout:

```bash
# View logs
docker logs -f kvs-infer

# Filter by camera
docker logs kvs-infer | grep '"camera_name":"front-door"'
```

## Troubleshooting

### CUDA Out of Memory

Reduce batch size or use smaller model:
```yaml
params:
  model_size: n  # Use nano model instead of large
```

### Stream Connection Issues

Check:
1. KVS stream is active and streaming
2. AWS credentials are valid
3. IAM permissions are correct
4. Network connectivity to AWS

### Low FPS

- Reduce `fps_limit` in config
- Increase `skip_frames` to process fewer frames
- Use GPU instead of CPU
- Use smaller YOLO models (n/s instead of l/x)

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

For issues and questions, please open a GitHub issue.
