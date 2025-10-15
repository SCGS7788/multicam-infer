# Step 6: Process Manager & CLI - Status

**Status**: ✅ COMPLETE  
**Validation**: ✅ All checks passed (9/9)  
**Total Lines**: 1,501 lines

---

## Quick Start

### Run Application

```bash
python -m kvs_infer.app \
  --config config/cameras.yaml \
  --http 0.0.0.0:8080
```

### Environment Variables

```bash
export LOG_LEVEL=INFO
export AWS_REGION=us-east-1
```

### Check Health

```bash
curl http://localhost:8080/healthz
# {"status":"ok","service":"kvs-infer"}
```

### View Metrics

```bash
curl http://localhost:8080/metrics
```

---

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `src/kvs_infer/app.py` | 852 | Main application |
| `config/cameras.yaml` | 107 | Example config |
| `validate_step6.py` | 542 | Validation script |

---

## Key Components

### 1. Application Manager
- Load YAML configuration
- Initialize AWS publishers
- Start camera workers
- Start HTTP server
- Handle graceful shutdown

### 2. Camera Worker
- Read frames from KVS HLS
- Run detector pipeline
- Publish to KDS/S3/DDB
- Track metrics
- Handle errors

### 3. HTTP Server (FastAPI)
- `GET /healthz` → Health check
- `GET /metrics` → Prometheus metrics

### 4. Prometheus Metrics
- `infer_frames_total{camera_id}` → Frames processed
- `infer_events_total{camera_id, type}` → Detection events
- `infer_latency_ms{camera_id}` → Inference latency
- `publisher_failures_total{sink}` → Publisher failures
- `worker_alive{camera_id}` → Worker health (1=alive, 0=dead)

### 5. Signal Handlers
- `SIGTERM` → Graceful shutdown
- `SIGINT` (Ctrl+C) → Graceful shutdown

---

## CLI Options

```bash
python -m kvs_infer.app \
  --config <path>      # Required: YAML config file
  --http <host:port>   # Optional: HTTP bind address (default: 0.0.0.0:8080)
```

---

## Configuration Example

```yaml
publishers:
  kds:
    enabled: true
    stream_name: detection-events
  s3:
    enabled: true
    bucket: detection-snapshots
  ddb:
    enabled: false

cameras:
  camera_1:
    enabled: true
    fps_target: 5
    kvs:
      stream_name: front-door-camera
    detectors:
      - type: weapon
        params: {...}
```

---

## Graceful Shutdown

```
1. Receive signal (SIGTERM/SIGINT)
   ↓
2. Stop workers (join threads)
   ↓
3. Close frame sources
   ↓
4. Flush publishers (KDS/S3/DDB)
   ↓
5. Log final metrics
   ↓
6. Exit cleanly
```

---

## JSON Logging

```json
{
  "timestamp": "2024-10-13T10:30:45",
  "level": "INFO",
  "logger": "kvs_infer.app",
  "message": "Detections: 2 events",
  "camera_id": "camera_1",
  "event_count": 2,
  "latency_ms": 87.5
}
```

---

## Worker Processing Loop

```python
while running:
    # 1. FPS throttling
    throttle(fps_target)
    
    # 2. Read frame
    frame, ts_ms = frame_source.read_frame()
    
    # 3. Run detectors
    events = run_detectors(frame, ts_ms)
    
    # 4. Track metrics
    frames_total.inc()
    latency_histogram.observe(latency_ms)
    
    # 5. Publish events
    kds.put_event(events)
    ddb.put_event(events)
    
    # 6. Save snapshots
    s3.save_with_bbox(frame, events)
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
COPY src/ src/
COPY config/ config/
CMD ["python", "-m", "kvs_infer.app", "--config", "config/cameras.yaml"]
```

```bash
docker run -d \
  -p 8080:8080 \
  -e LOG_LEVEL=INFO \
  -v $(pwd)/config:/app/config \
  kvs-infer:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kvs-infer
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: kvs-infer
        image: kvs-infer:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
```

### Systemd

```ini
[Unit]
Description=KVS Infer
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m kvs_infer.app --config /etc/kvs-infer/cameras.yaml
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Monitoring

### Prometheus Queries

```promql
# Frame processing rate
rate(infer_frames_total[5m])

# Event detection rate
rate(infer_events_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(infer_latency_ms_bucket[5m]))

# Publisher failures
rate(publisher_failures_total[5m])

# Worker health
worker_alive
```

### Alerts

```yaml
- alert: WorkerDown
  expr: worker_alive == 0
  for: 1m

- alert: HighLatency
  expr: histogram_quantile(0.95, rate(infer_latency_ms_bucket[5m])) > 1000
  for: 5m

- alert: PublisherFailures
  expr: rate(publisher_failures_total[5m]) > 0.1
  for: 5m
```

---

## Troubleshooting

### Worker Not Starting

```bash
# Check KVS stream
aws kinesisvideo list-streams

# Check logs
LOG_LEVEL=DEBUG python -m kvs_infer.app --config config/cameras.yaml
```

### High Memory Usage

```yaml
# Reduce FPS
cameras:
  camera_1:
    fps_target: 2  # Lower FPS

# Use smaller model
detectors:
  - type: weapon
    params:
      model_path: models/weapon-yolov8n.pt  # Nano model
```

### Metrics Not Updating

```bash
# Check health
curl http://localhost:8080/healthz

# Check metrics endpoint
curl http://localhost:8080/metrics
```

---

## Performance Tuning

### FPS Throttling

```yaml
cameras:
  camera_1:
    fps_target: 5  # Process 5 frames/sec (reduces CPU by 83%)
```

### Batch Processing

```yaml
publishers:
  kds:
    batch_size: 500  # Max batch (reduces API calls by 99.8%)
```

### Model Size

```
yolov8n: 3.2M params, ~5ms inference
yolov8s: 11.2M params, ~10ms inference
yolov8m: 25.9M params, ~20ms inference
```

---

## Validation

```bash
python3 validate_step6.py
```

**Expected**:
```
✓ App Structure: PASSED
✓ CLI Functionality: PASSED
✓ Worker Management: PASSED
✓ FastAPI Endpoints: PASSED
✓ Prometheus Metrics: PASSED
✓ Signal Handlers: PASSED
✓ Publisher Integration: PASSED
✓ JSON Logging: PASSED
✓ Example Config: PASSED

✓ All checks passed (9/9)
```

---

## Summary

✅ **852-line app.py**: Complete process manager  
✅ **CLI**: `--config`, `--http` arguments  
✅ **Worker Management**: Multi-threaded camera processing  
✅ **FastAPI**: `/healthz`, `/metrics` endpoints  
✅ **Prometheus**: 5 metrics (frames, events, latency, failures, health)  
✅ **JSON Logging**: Structured logs with extra fields  
✅ **Graceful Shutdown**: SIGTERM/SIGINT handlers  
✅ **Publisher Integration**: KDS, S3, DDB with flushing  
✅ **Example Config**: 3-camera YAML configuration  

**Status**: COMPLETE ✅
