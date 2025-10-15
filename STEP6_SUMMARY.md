# Step 6: Process Manager & CLI - Complete Summary

## Overview

Step 6 implements the main application entry point (`app.py`) with CLI, multi-camera worker management, FastAPI HTTP server, Prometheus metrics, and graceful shutdown handling.

**Validation Status**: ✅ All checks passed (9/9)

## Files Created

### 1. **src/kvs_infer/app.py** (852 lines)
Main application with worker management, metrics, and HTTP server.

### 2. **config/cameras.yaml** (107 lines)
Example configuration file with 3 cameras.

### 3. **validate_step6.py** (542 lines)
Comprehensive validation script.

**Total Lines**: 1,501 lines

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Application                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    HTTP Server (FastAPI)                   │  │
│  │  - GET /healthz  (health check)                           │  │
│  │  - GET /metrics  (Prometheus metrics)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Signal Handlers                         │  │
│  │  - SIGTERM → graceful shutdown                            │  │
│  │  - SIGINT  → graceful shutdown                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Publishers (KDS, S3, DDB)                  │  │
│  │  - KDSClient     (stream events)                          │  │
│  │  - S3Snapshot    (save frames)                            │  │
│  │  - DDBWriter     (persist events)                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Camera 1 │  │ Camera 2 │  │ Camera N │  (CameraWorker)      │
│  │  Worker  │  │  Worker  │  │  Worker  │                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │             │             │                              │
│       ├─ KVS HLS    ├─ KVS HLS    ├─ KVS HLS                    │
│       ├─ Detectors  ├─ Detectors  ├─ Detectors                  │
│       └─ Publishers └─ Publishers └─ Publishers                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## CLI Usage

### Basic Usage

```bash
python -m kvs_infer.app \
  --config config/cameras.yaml \
  --http 0.0.0.0:8080
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--config` | **Yes** | - | Path to YAML configuration file |
| `--http` | No | `0.0.0.0:8080` | HTTP server bind address (host:port) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### Examples

#### Run with custom config
```bash
python -m kvs_infer.app \
  --config /path/to/cameras.yaml \
  --http 0.0.0.0:8080
```

#### Run with debug logging
```bash
LOG_LEVEL=DEBUG python -m kvs_infer.app \
  --config config/cameras.yaml
```

#### Run on different port
```bash
python -m kvs_infer.app \
  --config config/cameras.yaml \
  --http 0.0.0.0:9000
```

---

## Components

### 1. Application Manager

**Class**: `Application`

**Responsibilities**:
- Load YAML configuration
- Initialize AWS publishers (KDS, S3, DDB)
- Start camera workers
- Start HTTP server (FastAPI)
- Handle graceful shutdown

**Key Methods**:

```python
app = Application(config_path="config/cameras.yaml", http_bind="0.0.0.0:8080")

app.load_configuration()          # Load YAML config
app.initialize_publishers()       # Initialize KDS, S3, DDB
app.start_http_server()           # Start FastAPI server
app.start_workers()               # Start camera workers
app.setup_signal_handlers()       # Register SIGTERM/SIGINT
app.shutdown()                    # Graceful shutdown
app.run()                         # Main loop
```

---

### 2. Camera Worker

**Class**: `CameraWorker`

**Responsibilities**:
- Read frames from KVS HLS source
- Run detector pipeline
- Publish events to KDS/S3/DDB
- Track metrics (frames, events, latency)
- Handle errors and reconnection

**Lifecycle**:

```python
worker = CameraWorker(
    camera_id="camera_1",
    camera_config={...},
    global_config={...},
    publishers={kds, s3, ddb}
)

worker.start()  # Start worker thread
# ... processing loop runs ...
worker.stop()   # Stop worker thread
```

**Processing Loop**:

```python
while running:
    # 1. FPS throttling
    if fps_target:
        throttle_to_fps(fps_target)
    
    # 2. Read frame
    frame, ts_ms = frame_source.read_frame()
    
    # 3. Run detectors
    events = run_detectors(frame, ts_ms)
    
    # 4. Track metrics
    frames_total.inc()
    latency_histogram.observe(latency_ms)
    
    # 5. Publish events
    publish_to_kds(events)
    publish_to_ddb(events)
    
    # 6. Save snapshots
    save_to_s3(frame, events)
```

---

### 3. FastAPI HTTP Server

**Endpoints**:

#### Health Check

```bash
GET /healthz
```

**Response**:
```json
{
  "status": "ok",
  "service": "kvs-infer"
}
```

#### Prometheus Metrics

```bash
GET /metrics
```

**Response** (Prometheus text format):
```
# HELP infer_frames_total Total frames processed
# TYPE infer_frames_total counter
infer_frames_total{camera_id="camera_1"} 1250
infer_frames_total{camera_id="camera_2"} 890

# HELP infer_events_total Total detection events
# TYPE infer_events_total counter
infer_events_total{camera_id="camera_1",type="weapon"} 15
infer_events_total{camera_id="camera_2",type="alpr"} 42

# HELP infer_latency_ms Inference latency in milliseconds
# TYPE infer_latency_ms histogram
infer_latency_ms_bucket{camera_id="camera_1",le="50"} 1120
infer_latency_ms_bucket{camera_id="camera_1",le="100"} 1235
...
```

---

### 4. Prometheus Metrics

**Metrics**:

#### Frame Processing

```python
# Counter: Total frames processed
infer_frames_total{camera_id="camera_1"}

# Counter: Total detection events
infer_events_total{camera_id="camera_1", type="weapon"}

# Histogram: Inference latency (ms)
infer_latency_ms{camera_id="camera_1"}
# Buckets: 10, 50, 100, 200, 500, 1000, 2000, 5000
```

#### Publisher Health

```python
# Counter: Total publisher failures
publisher_failures_total{sink="kds"}
publisher_failures_total{sink="s3"}
publisher_failures_total{sink="ddb"}
```

#### Worker Health

```python
# Gauge: Worker alive status (1=alive, 0=dead)
worker_alive{camera_id="camera_1"} 1
worker_alive{camera_id="camera_2"} 1
```

---

### 5. JSON Logging

**Format**: JSON to stdout

**Features**:
- Structured logging for easy parsing
- Extra fields for context (camera_id, event_type, latency_ms)
- Exception stack traces
- Log level from `LOG_LEVEL` environment variable

**Example Logs**:

```json
{"timestamp":"2024-10-13T10:30:45","level":"INFO","logger":"kvs_infer.app","message":"Application initialized: config=config/cameras.yaml, http=0.0.0.0:8080","module":"app","function":"__init__","line":625}

{"timestamp":"2024-10-13T10:30:46","level":"INFO","logger":"kvs_infer.app","message":"KDS publisher initialized: detection-events","module":"app","function":"initialize_publishers","line":685}

{"timestamp":"2024-10-13T10:30:47","level":"INFO","logger":"kvs_infer.app","message":"Started 2 camera workers","module":"app","function":"start_workers","line":720}

{"timestamp":"2024-10-13T10:30:50","level":"INFO","logger":"kvs_infer.app","message":"Detections: 2 events","module":"app","function":"_run","line":520,"camera_id":"camera_1","event_count":2,"latency_ms":87.5}
```

---

### 6. Graceful Shutdown

**Signal Handling**:

```python
# Register handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown()
```

**Shutdown Sequence**:

1. **Receive Signal** → SIGTERM or SIGINT (Ctrl+C)
2. **Stop Workers** → Set `running = False`, join threads (5s timeout)
3. **Close Frame Sources** → Stop CV2 capture, cleanup resources
4. **Flush Publishers** → Send remaining batches
   - KDS: Flush pending records
   - S3: Complete uploads
   - DDB: Complete writes
5. **Log Final Metrics** → Print publisher metrics
6. **Exit** → Clean application exit

**Example**:

```bash
# Start application
$ python -m kvs_infer.app --config config/cameras.yaml

# ... running ...

# Send shutdown signal (Ctrl+C)
^C
{"level":"INFO","message":"Received signal 2, shutting down..."}
{"level":"INFO","message":"Stopping 2 workers"}
{"level":"INFO","message":"Worker stopped: camera_1"}
{"level":"INFO","message":"Worker stopped: camera_2"}
{"level":"INFO","message":"Flushing publisher batches"}
{"level":"INFO","message":"KDS final metrics: {'published': 1250, 'failed': 0}"}
{"level":"INFO","message":"S3 final metrics: {'saved': 340, 'failed': 0}"}
{"level":"INFO","message":"Graceful shutdown complete"}
```

---

## Configuration

### Example Config (config/cameras.yaml)

```yaml
# Publisher configuration
publishers:
  kds:
    enabled: true
    region: us-east-1
    stream_name: detection-events
    batch_size: 500
  
  s3:
    enabled: true
    region: us-east-1
    bucket: detection-snapshots
    prefix: snapshots
    jpeg_quality: 90
    save_snapshots: true
  
  ddb:
    enabled: false
    region: us-east-1
    table_name: events-table
    ttl_days: 30

# Camera configurations
cameras:
  camera_1:
    enabled: true
    fps_target: 5  # Process 5 frames per second
    
    kvs:
      stream_name: front-door-camera
      region: us-east-1
      start_fragment_mode: NOW
    
    detectors:
      - type: weapon
        params:
          model_path: models/weapon-yolov8n.pt
          conf_threshold: 0.5
          target_classes: [knife, gun, rifle]
      
      - type: fire_smoke
        params:
          model_path: models/fire-smoke-yolov8n.pt
          fire_conf_threshold: 0.6
          smoke_conf_threshold: 0.55
  
  camera_2:
    enabled: true
    fps_target: 3
    
    kvs:
      stream_name: parking-lot-camera
      region: us-east-1
      start_fragment_mode: NOW
    
    detectors:
      - type: alpr
        params:
          detector_model_path: models/license-plate-yolov8n.pt
          ocr_engine: paddleocr
```

### Configuration Structure

```yaml
publishers:
  kds:
    enabled: bool              # Enable KDS publisher
    region: str                # AWS region
    stream_name: str           # Kinesis stream name
    batch_size: int            # Batch size (max 500)
    max_retries: int           # Max retry attempts
    base_backoff_ms: int       # Base backoff in milliseconds
  
  s3:
    enabled: bool              # Enable S3 publisher
    region: str                # AWS region
    bucket: str                # S3 bucket name
    prefix: str                # S3 key prefix
    jpeg_quality: int          # JPEG quality (0-100)
    save_snapshots: bool       # Save frames with detections
  
  ddb:
    enabled: bool              # Enable DDB publisher
    region: str                # AWS region
    table_name: str            # DynamoDB table name
    ttl_days: int              # TTL in days (optional)

cameras:
  <camera_id>:
    enabled: bool              # Enable camera
    fps_target: int            # Target FPS (optional, for throttling)
    
    kvs:
      stream_name: str         # KVS stream name
      region: str              # AWS region
      start_fragment_mode: str # NOW or START_AT_TIMESTAMP
      max_retries: int         # Max retry attempts
      retry_delay_sec: int     # Retry delay in seconds
    
    detectors:
      - type: str              # Detector type (weapon, fire_smoke, alpr)
        params:
          <detector_params>    # Detector-specific params
```

---

## Deployment

### Docker

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ src/
COPY config/ config/

# Run application
CMD ["python", "-m", "kvs_infer.app", "--config", "config/cameras.yaml"]
```

**Build & Run**:

```bash
# Build image
docker build -t kvs-infer:latest .

# Run container
docker run -d \
  --name kvs-infer \
  -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e LOG_LEVEL=INFO \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/models:/app/models \
  kvs-infer:latest
```

---

### Kubernetes

**Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kvs-infer
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kvs-infer
  template:
    metadata:
      labels:
        app: kvs-infer
    spec:
      containers:
      - name: kvs-infer
        image: kvs-infer:latest
        ports:
        - containerPort: 8080
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: AWS_REGION
          value: "us-east-1"
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: models
          mountPath: /app/models
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: kvs-infer-config
      - name: models
        persistentVolumeClaim:
          claimName: models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: kvs-infer
spec:
  selector:
    app: kvs-infer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

---

### Systemd Service

**systemd unit** (`/etc/systemd/system/kvs-infer.service`):

```ini
[Unit]
Description=KVS Infer - Multi-camera inference service
After=network.target

[Service]
Type=simple
User=kvs-infer
WorkingDirectory=/opt/kvs-infer
ExecStart=/usr/bin/python3 -m kvs_infer.app --config /etc/kvs-infer/cameras.yaml
Restart=always
RestartSec=10
Environment="LOG_LEVEL=INFO"
Environment="AWS_REGION=us-east-1"

[Install]
WantedBy=multi-user.target
```

**Commands**:

```bash
# Enable service
sudo systemctl enable kvs-infer

# Start service
sudo systemctl start kvs-infer

# Check status
sudo systemctl status kvs-infer

# View logs
sudo journalctl -u kvs-infer -f

# Stop service
sudo systemctl stop kvs-infer
```

---

## Monitoring

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'kvs-infer'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard

**Example Queries**:

```promql
# Frame processing rate (frames/sec)
rate(infer_frames_total[5m])

# Event detection rate (events/sec)
rate(infer_events_total[5m])

# Average latency
histogram_quantile(0.95, rate(infer_latency_ms_bucket[5m]))

# Publisher failure rate
rate(publisher_failures_total[5m])

# Worker health
worker_alive
```

**Alerts**:

```yaml
groups:
  - name: kvs-infer
    rules:
      # Worker down
      - alert: WorkerDown
        expr: worker_alive == 0
        for: 1m
        annotations:
          summary: "Camera worker is down"
      
      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(infer_latency_ms_bucket[5m])) > 1000
        for: 5m
        annotations:
          summary: "Inference latency > 1s"
      
      # Publisher failures
      - alert: PublisherFailures
        expr: rate(publisher_failures_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High publisher failure rate"
```

---

## Troubleshooting

### Issue: Worker thread not starting

**Symptoms**:
- `worker_alive` metric is 0
- No frames being processed

**Solutions**:
1. Check KVS stream exists:
   ```bash
   aws kinesisvideo list-streams
   ```
2. Check IAM permissions for KVS GetDataEndpoint and GetHLSStreamingSessionURL
3. Check logs for initialization errors:
   ```bash
   LOG_LEVEL=DEBUG python -m kvs_infer.app --config config/cameras.yaml
   ```

---

### Issue: High memory usage

**Symptoms**:
- Memory usage growing over time
- OOMKilled in Kubernetes

**Solutions**:
1. Reduce `fps_target` to process fewer frames
2. Reduce YOLO model size (yolov8n → yolov8s)
3. Enable frame skipping in detector configuration
4. Add memory limits in Docker/Kubernetes:
   ```yaml
   resources:
     limits:
       memory: "2Gi"
   ```

---

### Issue: Metrics not updating

**Symptoms**:
- `/metrics` endpoint returns stale data
- Prometheus shows no data

**Solutions**:
1. Check HTTP server is running:
   ```bash
   curl http://localhost:8080/healthz
   ```
2. Check Prometheus scrape config
3. Verify metrics are being tracked in worker loop

---

## Performance Tuning

### 1. FPS Throttling

Control frame processing rate to reduce CPU/GPU usage:

```yaml
cameras:
  camera_1:
    fps_target: 5  # Process 5 frames per second
```

**Calculation**:
- 30 FPS stream, `fps_target: 5` → Process 1 in 6 frames (83% reduction)
- 10 FPS stream, `fps_target: 2` → Process 1 in 5 frames (80% reduction)

---

### 2. Batch Processing

Maximize throughput with batching:

```yaml
publishers:
  kds:
    batch_size: 500  # Max batch size for Kinesis
```

**Impact**:
- 1,000 events/min, `batch_size: 500` → 2 API calls/min (vs 1,000)
- Reduces API costs by 99.8%

---

### 3. Model Optimization

Use smaller models or quantization:

```yaml
detectors:
  - type: weapon
    params:
      model_path: models/weapon-yolov8n.pt  # Nano (smallest)
      # vs yolov8s (small), yolov8m (medium), yolov8l (large)
```

**Model Sizes**:
- YOLOv8n: 3.2M params, ~5ms inference
- YOLOv8s: 11.2M params, ~10ms inference
- YOLOv8m: 25.9M params, ~20ms inference

---

## Testing

### Unit Tests

```bash
pytest tests/test_app.py -v
```

### Integration Tests

```bash
# Start LocalStack for AWS services
docker run -d -p 4566:4566 localstack/localstack

# Run integration tests
pytest tests/integration/test_app_integration.py -v
```

### Load Testing

```bash
# Simulate 10 cameras with 5 FPS each
python scripts/load_test.py --cameras 10 --fps 5 --duration 60
```

---

## Summary

✅ **App Entry Point** (852 lines): CLI, worker management, HTTP server  
✅ **FastAPI Endpoints**: `/healthz`, `/metrics`  
✅ **Prometheus Metrics**: frames_total, events_total, latency_ms, publisher_failures, worker_alive  
✅ **JSON Logging**: Structured logs to stdout with extra fields  
✅ **Graceful Shutdown**: SIGTERM/SIGINT handlers, flush publishers  
✅ **Multi-Camera Workers**: Separate threads with detector pipelines  
✅ **Publisher Integration**: KDS, S3, DDB with batch flushing  
✅ **Example Config**: 3-camera setup with different detectors  
✅ **Validation**: All checks passed (9/9)  

**Total Implementation**: 1,501 lines (852 app + 107 config + 542 validation)

---

**Validation Command**:

```bash
python3 validate_step6.py
```

**Expected Output**:
```
✓ All checks passed (9/9)
Step 6 implementation is complete and valid!
```

---

**Status**: ✅ COMPLETE  
**Date**: October 13, 2025  
**Version**: 1.0
