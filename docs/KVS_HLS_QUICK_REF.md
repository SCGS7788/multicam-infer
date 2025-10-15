# KVS HLS Reader - Quick Reference

## 📦 Installation

```bash
pip install -e .
```

## 🚀 Quick Start

```python
from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource

# Create and use
source = KVSHLSFrameSource(
    camera_id="cam-1",
    stream_name="my-kvs-stream",
    region="us-east-1",
)

with source:
    for frame, timestamp in source.read_frames():
        # frame: numpy array (BGR)
        # timestamp: Unix timestamp (float)
        print(frame.shape)
```

## ⚙️ Configuration

```python
source = KVSHLSFrameSource(
    camera_id="cam-1",              # Required: Unique ID
    stream_name="my-stream",        # Required: KVS stream name
    region="us-east-1",             # Default: "us-east-1"
    hls_session_seconds=300,        # Range: 60-43200, Default: 300
    url_refresh_margin=30,          # Default: 30 (seconds before expiry)
    reconnect_delay=5,              # Default: 5 (initial retry delay)
    max_reconnect_delay=60,         # Default: 60 (backoff cap)
    backoff_multiplier=2.0,         # Default: 2.0 (exponential)
    max_consecutive_errors=10,      # Default: 10 (fail threshold)
)
```

## 🔧 Common Patterns

### Pattern 1: Basic Usage
```python
with KVSHLSFrameSource(...) as source:
    for frame, timestamp in source.read_frames():
        process(frame)
```

### Pattern 2: Manual Control
```python
source = KVSHLSFrameSource(...)
source.start()

while True:
    frame_data = source.read_frame()
    if frame_data:
        frame, timestamp = frame_data
        process(frame)

source.release()
```

### Pattern 3: With Health Checks
```python
with source:
    for frame, timestamp in source.read_frames():
        if not source.is_healthy():
            alert("Unhealthy source!")
        
        metrics = source.get_metrics()
        if metrics['reconnects_total'] > 10:
            alert("High reconnection rate!")
```

### Pattern 4: FPS Throttling
```python
import time

target_fps = 5
interval = 1.0 / target_fps
last_time = 0

with source:
    for frame, timestamp in source.read_frames():
        # Throttle
        now = time.time()
        if now - last_time < interval:
            time.sleep(interval - (now - last_time))
        last_time = time.time()
        
        process(frame)
```

## 📊 Metrics

### Local Metrics
```python
metrics = source.get_metrics()
# Returns dict:
# {
#   "camera_id": str,
#   "reconnects_total": int,
#   "frames_total": int,
#   "last_frame_timestamp": float | None,
#   "url_refreshes_total": int,
#   "read_errors_total": int,
# }
```

### Prometheus Metrics
```python
# Auto-exported:
# kvs_hls_reconnects_total{camera_id}
# kvs_hls_frames_total{camera_id}
# kvs_hls_last_frame_timestamp{camera_id}
# kvs_hls_url_refreshes_total{camera_id}
# kvs_hls_read_errors_total{camera_id}
# kvs_hls_connection_state{camera_id}  # 0-4
```

## 🛠️ Error Handling

```python
from kvs_infer.frame_source.kvs_hls import (
    FrameSourceError,      # Base exception
    KVSConnectionError,    # KVS API errors
    HLSStreamError,        # Stream reading errors
)

try:
    with source:
        for frame, timestamp in source.read_frames():
            process(frame)
except KVSConnectionError as e:
    # Handle KVS API errors (stream not found, access denied, etc.)
    print(f"KVS error: {e}")
except FrameSourceError as e:
    # Handle fatal errors (max retries exceeded)
    print(f"Fatal error: {e}")
```

## 🔍 Debugging

### Check Connection State
```python
state = source.get_connection_state()
# Returns: "disconnected", "connecting", "connected", "reconnecting", "error"
```

### Health Check
```python
if source.is_healthy():
    print("OK")
else:
    print("Issues detected")
```

### View Metrics
```python
metrics = source.get_metrics()
print(f"Frames: {metrics['frames_total']}")
print(f"Reconnects: {metrics['reconnects_total']}")
print(f"Errors: {metrics['read_errors_total']}")
```

## 🎯 Configuration Presets

### Production (Conservative)
```python
source = KVSHLSFrameSource(
    camera_id="cam-1",
    stream_name="stream-1",
    region="us-east-1",
    hls_session_seconds=1800,    # 30 min
    url_refresh_margin=120,      # 2 min
    reconnect_delay=10,          # 10s
    max_reconnect_delay=300,     # 5 min
    max_consecutive_errors=20,   # Tolerant
)
```

### Testing (Aggressive)
```python
source = KVSHLSFrameSource(
    camera_id="cam-1",
    stream_name="stream-1",
    region="us-east-1",
    hls_session_seconds=60,      # 1 min (min)
    url_refresh_margin=10,       # 10s
    reconnect_delay=1,           # 1s
    max_reconnect_delay=10,      # 10s
    max_consecutive_errors=5,    # Fail fast
)
```

### Default (Balanced)
```python
source = KVSHLSFrameSource(
    camera_id="cam-1",
    stream_name="stream-1",
    region="us-east-1",
    # All other params use defaults
)
```

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/test_kvs_hls.py -v

# With coverage
python -m pytest tests/test_kvs_hls.py --cov=kvs_infer.frame_source.kvs_hls

# Run demo script
python examples/demo_kvs_hls_reader.py \
    --stream-name my-stream \
    --region us-east-1 \
    --max-frames 100
```

## 📚 Reference

- **Full Documentation**: `docs/KVS_HLS_READER.md`
- **Implementation**: `src/kvs_infer/frame_source/kvs_hls.py`
- **Tests**: `tests/test_kvs_hls.py`
- **Demo**: `examples/demo_kvs_hls_reader.py`
- **Summary**: `STEP2_SUMMARY.md`

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ResourceNotFoundException` | Check stream name and region |
| Frequent reconnections | Increase `hls_session_seconds` |
| No frames received | Verify stream has active producer |
| High read errors | Check network bandwidth |
| Max errors reached | Increase `max_consecutive_errors` |

## 💡 Pro Tips

1. **Always use context manager** for automatic cleanup
2. **Monitor reconnect rate** to detect issues early
3. **Use 5-30 min HLS sessions** for production
4. **Implement FPS throttling** to avoid overload
5. **Check `is_healthy()`** periodically
6. **Set appropriate error limits** based on environment

---

**Step 2 Complete** ✅ | 717 lines | 27 tests passing | Production-ready
