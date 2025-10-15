# KVS HLS Frame Source

## Overview

The `KVSHLSFrameSource` is a robust frame reader for AWS Kinesis Video Streams (KVS) using HLS (HTTP Live Streaming) protocol. It handles automatic URL refresh, graceful reconnection with exponential backoff, comprehensive metrics tracking, and thread-safe operation.

## Features

- **Automatic HLS URL Refresh**: URLs are automatically refreshed before expiry (configurable margin)
- **Graceful Reconnection**: Exponential backoff with jitter for robust reconnection
- **Comprehensive Metrics**: Tracks frames, reconnections, errors, and connection state
- **Thread-Safe**: Thread-safe URL refresh and stream management
- **Prometheus Integration**: Direct integration with Prometheus metrics
- **Configurable Retry Behavior**: Fine-grained control over reconnection strategy
- **Context Manager Support**: Clean resource management with `with` statement

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   KVSHLSFrameSource                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  URL Management  │         │  Connection Mgmt │          │
│  │                  │         │                  │          │
│  │ - Get HLS URL    │         │ - Open stream    │          │
│  │ - Refresh logic  │         │ - Reconnect      │          │
│  │ - Expiry check   │◄────────┤ - Backoff/jitter │          │
│  └──────────────────┘         └──────────────────┘          │
│         │                              │                     │
│         │                              │                     │
│         ▼                              ▼                     │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  Frame Reading   │         │  Metrics         │          │
│  │                  │         │                  │          │
│  │ - read_frame()   │────────►│ - Prometheus     │          │
│  │ - read_frames()  │         │ - Local metrics  │          │
│  │ - Error handling │         │ - Health check   │          │
│  └──────────────────┘         └──────────────────┘          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Usage

```python
from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource

# Create frame source
source = KVSHLSFrameSource(
    camera_id="front-entrance",
    stream_name="my-kvs-stream",
    region="us-east-1",
    hls_session_seconds=300,
)

# Read frames using context manager
with source:
    for frame, timestamp in source.read_frames():
        # Process frame (numpy array in BGR format)
        print(f"Frame shape: {frame.shape}, timestamp: {timestamp}")
```

### Advanced Usage with Configuration

```python
from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource

# Create with custom retry behavior
source = KVSHLSFrameSource(
    camera_id="parking-lot-01",
    stream_name="parking-stream",
    region="us-west-2",
    hls_session_seconds=600,          # 10-minute sessions
    url_refresh_margin=60,            # Refresh 60s before expiry
    reconnect_delay=3,                # Initial 3s delay
    max_reconnect_delay=120,          # Cap at 2 minutes
    backoff_multiplier=2.5,           # Aggressive backoff
    max_consecutive_errors=20,        # Allow more retries
)

# Manual lifecycle management
try:
    source.start()
    
    while True:
        frame_data = source.read_frame()
        if frame_data is None:
            continue
            
        frame, timestamp = frame_data
        
        # Check health
        if not source.is_healthy():
            print("Warning: Frame source unhealthy")
        
        # Get metrics
        metrics = source.get_metrics()
        print(f"Frames read: {metrics['frames_total']}")
        
finally:
    source.release()
```

### Integration with Camera Configuration

```python
from kvs_infer.config import load_yaml
from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource

# Load configuration
config = load_yaml("config/cameras.yaml")

# Create frame sources for all enabled cameras
sources = {}
for camera in config.cameras:
    if not camera.enabled:
        continue
    
    source = KVSHLSFrameSource(
        camera_id=camera.id,
        stream_name=camera.playback.kvs_stream_name,
        region=config.aws.region,
        hls_session_seconds=camera.playback.hls_session_seconds,
    )
    sources[camera.id] = source

# Start reading frames
for camera_id, source in sources.items():
    with source:
        for frame, timestamp in source.read_frames():
            # Process frame
            pass
```

## Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `camera_id` | `str` | **required** | Unique camera identifier (for metrics) |
| `stream_name` | `str` | **required** | KVS stream name |
| `region` | `str` | `"us-east-1"` | AWS region |
| `hls_session_seconds` | `int` | `300` | HLS URL expiry time (60-43200) |
| `url_refresh_margin` | `int` | `30` | Refresh URL N seconds before expiry |
| `reconnect_delay` | `int` | `5` | Initial reconnect delay in seconds |
| `max_reconnect_delay` | `int` | `60` | Maximum backoff delay (cap) |
| `backoff_multiplier` | `float` | `2.0` | Exponential backoff multiplier |
| `max_consecutive_errors` | `int` | `10` | Max errors before raising exception |

### Parameter Guidelines

**HLS Session Duration** (`hls_session_seconds`):
- **Short (60-300s)**: Better for testing, more API calls
- **Medium (300-1800s)**: Balanced for production
- **Long (1800-43200s)**: Fewer API calls, longer to detect stream changes

**URL Refresh Margin** (`url_refresh_margin`):
- Should be < `hls_session_seconds`
- Recommend 10-20% of session duration
- Example: 300s session → 30-60s margin

**Reconnection Strategy**:
- **Tight reconnect** (`reconnect_delay=1`, `max_reconnect_delay=10`): Quick recovery, more aggressive
- **Standard** (defaults): Good for most use cases
- **Conservative** (`reconnect_delay=10`, `max_reconnect_delay=300`): Reduces API pressure

## Metrics

The frame source tracks comprehensive metrics both locally and via Prometheus.

### Local Metrics (Python)

```python
metrics = source.get_metrics()

# Available metrics:
# - camera_id: str
# - reconnects_total: int
# - frames_total: int
# - last_frame_timestamp: float | None
# - url_refreshes_total: int
# - read_errors_total: int
```

### Prometheus Metrics

All metrics include the `camera_id` label:

| Metric | Type | Description |
|--------|------|-------------|
| `kvs_hls_reconnects_total{camera_id}` | Counter | Total reconnections |
| `kvs_hls_frames_total{camera_id}` | Counter | Total frames read |
| `kvs_hls_last_frame_timestamp{camera_id}` | Gauge | Last frame Unix timestamp |
| `kvs_hls_url_refreshes_total{camera_id}` | Counter | Total URL refreshes |
| `kvs_hls_read_errors_total{camera_id}` | Counter | Total read errors |
| `kvs_hls_connection_state{camera_id}` | Gauge | Connection state (0-4) |

**Connection States**:
- `0`: Disconnected
- `1`: Connecting
- `2`: Connected
- `3`: Reconnecting
- `4`: Error

### Querying Metrics

```promql
# Frame rate per camera (5m rate)
rate(kvs_hls_frames_total[5m])

# Reconnection rate
rate(kvs_hls_reconnects_total[1h])

# Time since last frame
time() - kvs_hls_last_frame_timestamp

# Cameras in error state
kvs_hls_connection_state{camera_id=~".*"} == 4

# Total read errors across all cameras
sum(kvs_hls_read_errors_total)
```

## Error Handling

### Exception Hierarchy

```
FrameSourceError (base)
├── KVSConnectionError (KVS API/connection issues)
└── HLSStreamError (HLS stream reading issues)
```

### Error Scenarios

**1. KVS API Errors**

```python
from kvs_infer.frame_source.kvs_hls import KVSConnectionError

try:
    source = KVSHLSFrameSource(...)
    with source:
        for frame, timestamp in source.read_frames():
            pass
except KVSConnectionError as e:
    # Handle KVS API errors:
    # - Stream not found
    # - Access denied
    # - Region mismatch
    print(f"KVS connection error: {e}")
```

**2. Max Consecutive Errors**

```python
from kvs_infer.frame_source.kvs_hls import FrameSourceError

try:
    source = KVSHLSFrameSource(
        camera_id="cam-1",
        stream_name="stream-1",
        max_consecutive_errors=5,
    )
    
    with source:
        for frame, timestamp in source.read_frames():
            pass
            
except FrameSourceError as e:
    # Raised when max_consecutive_errors exceeded
    print(f"Fatal error: {e}")
```

**3. Graceful Degradation**

```python
while True:
    frame_data = source.read_frame()
    
    if frame_data is None:
        # Temporary failure, reconnection in progress
        time.sleep(0.1)
        continue
    
    frame, timestamp = frame_data
    # Process frame
```

## Connection State Management

### State Transitions

```
DISCONNECTED ──start()──> CONNECTING ──success──> CONNECTED
                                │                      │
                                │                      │
                                └──────error──────> ERROR
                                                       │
                                                       │
                            RECONNECTING <─────────────┘
                                    │
                                    │
                            ┌───────┴───────┐
                            │               │
                        success          failure
                            │               │
                            ▼               ▼
                      CONNECTED          ERROR
```

### State Checking

```python
# Get current state
state = source.get_connection_state()
print(f"State: {state}")

# Health check
if source.is_healthy():
    print("Source is healthy")
else:
    print("Source has issues")
    
    # Get detailed metrics
    metrics = source.get_metrics()
    print(f"Reconnects: {metrics['reconnects_total']}")
    print(f"Errors: {metrics['read_errors_total']}")
```

## Reconnection Strategy

### Exponential Backoff with Jitter

The frame source uses exponential backoff with jitter to avoid thundering herd problems:

```python
# Initial delay: 5s
# After 1st failure: 5s * 2.0 = 10s (with jitter: 8-12s)
# After 2nd failure: 10s * 2.0 = 20s (with jitter: 16-24s)
# After 3rd failure: 20s * 2.0 = 40s (with jitter: 32-48s)
# After 4th failure: 40s * 2.0 = 80s → capped at 60s (with jitter: 48-72s)
```

### Jitter Range

- Default jitter: 80-120% of calculated delay
- Helps distribute reconnection attempts across time
- Prevents multiple cameras from reconnecting simultaneously

### Customizing Backoff

```python
source = KVSHLSFrameSource(
    camera_id="cam-1",
    stream_name="stream-1",
    reconnect_delay=2,           # Start with 2s
    max_reconnect_delay=30,      # Cap at 30s
    backoff_multiplier=1.5,      # Slower growth (1.5x)
)
```

## Performance Considerations

### Frame Rate Control

The frame source reads frames as fast as possible. Implement FPS throttling in your application:

```python
import time

target_fps = 5
frame_interval = 1.0 / target_fps
last_frame_time = 0

with source:
    for frame, timestamp in source.read_frames():
        # FPS throttling
        now = time.time()
        elapsed = now - last_frame_time
        if elapsed < frame_interval:
            time.sleep(frame_interval - elapsed)
        last_frame_time = time.time()
        
        # Process frame
        process_frame(frame)
```

### Memory Management

Frames are returned as NumPy arrays. For long-running applications:

```python
import gc

frame_count = 0
gc_interval = 1000

with source:
    for frame, timestamp in source.read_frames():
        # Process frame
        result = detector.detect(frame)
        
        # Periodic garbage collection
        frame_count += 1
        if frame_count % gc_interval == 0:
            gc.collect()
```

### Thread Safety

The frame source is thread-safe for:
- URL refresh operations
- Stream opening/closing
- Metrics updates

However, `read_frame()` should be called from a single thread per instance.

## Troubleshooting

### Problem: "ResourceNotFoundException"

**Cause**: KVS stream doesn't exist or wrong region

**Solution**:
```python
# Verify stream exists
import boto3

kvs = boto3.client("kinesisvideo", region_name="us-east-1")
response = kvs.describe_stream(StreamName="my-stream")
print(response)
```

### Problem: Frequent Reconnections

**Cause**: Network instability, stream interruptions, or URL expiring too quickly

**Solution**:
```python
# Increase HLS session duration
source = KVSHLSFrameSource(
    camera_id="cam-1",
    stream_name="stream-1",
    hls_session_seconds=1800,  # 30 minutes
    url_refresh_margin=120,    # 2-minute margin
)

# Check metrics
metrics = source.get_metrics()
print(f"Reconnects: {metrics['reconnects_total']}")
print(f"URL refreshes: {metrics['url_refreshes_total']}")
```

### Problem: No Frames Received

**Cause**: Stream has no active producer or wrong playback mode

**Solution**:
1. Verify stream has active producer:
   ```bash
   aws kinesisvideo describe-stream --stream-name my-stream
   ```

2. Check stream status in KVS console

3. Try shorter HLS session for testing:
   ```python
   source = KVSHLSFrameSource(
       camera_id="cam-1",
       stream_name="stream-1",
       hls_session_seconds=60,  # Shorter for testing
   )
   ```

### Problem: High Read Errors

**Cause**: Slow network, insufficient bandwidth, or corrupted stream

**Solution**:
```python
# Monitor error rate
import time

start = time.time()
initial_errors = source.metrics.read_errors_total

# Wait 1 minute
time.sleep(60)

error_rate = (source.metrics.read_errors_total - initial_errors) / 60
print(f"Error rate: {error_rate:.2f} errors/sec")

# If error rate > 0.1, investigate:
# - Network bandwidth
# - Stream quality
# - OpenCV version/build
```

### Problem: "Max consecutive errors reached"

**Cause**: Persistent connection issues

**Solution**:
```python
# Increase tolerance
source = KVSHLSFrameSource(
    camera_id="cam-1",
    stream_name="stream-1",
    max_consecutive_errors=50,      # More tolerant
    reconnect_delay=10,             # Slower retry
    max_reconnect_delay=300,        # 5-minute max
)

# Or implement retry logic:
max_retries = 3
for retry in range(max_retries):
    try:
        with source:
            for frame, timestamp in source.read_frames():
                pass
    except FrameSourceError:
        if retry < max_retries - 1:
            print(f"Retry {retry + 1}/{max_retries}")
            time.sleep(60)
        else:
            raise
```

## Testing

### Unit Tests

Run comprehensive unit tests:

```bash
# Run all KVS HLS tests
python -m pytest tests/test_kvs_hls.py -v

# Run specific test class
python -m pytest tests/test_kvs_hls.py::TestKVSHLSFrameSourceURLManagement -v

# Run with coverage
python -m pytest tests/test_kvs_hls.py --cov=src/kvs_infer/frame_source/kvs_hls
```

### Integration Testing

Test with real KVS stream:

```bash
# Run demo script
python examples/demo_kvs_hls_reader.py \
    --stream-name my-test-stream \
    --region us-east-1 \
    --camera-id test-cam \
    --max-frames 100 \
    --target-fps 5

# With display
python examples/demo_kvs_hls_reader.py \
    --stream-name my-test-stream \
    --region us-east-1 \
    --camera-id test-cam

# Headless mode
python examples/demo_kvs_hls_reader.py \
    --stream-name my-test-stream \
    --region us-east-1 \
    --camera-id test-cam \
    --no-display
```

### Load Testing

Test with multiple streams:

```python
import threading
from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource

def read_stream(camera_id, stream_name):
    source = KVSHLSFrameSource(
        camera_id=camera_id,
        stream_name=stream_name,
        region="us-east-1",
    )
    
    with source:
        frame_count = 0
        for frame, timestamp in source.read_frames():
            frame_count += 1
            if frame_count >= 1000:
                break
    
    print(f"{camera_id}: {frame_count} frames")

# Test with 10 concurrent streams
threads = []
for i in range(10):
    t = threading.Thread(
        target=read_stream,
        args=(f"cam-{i}", f"stream-{i}")
    )
    t.start()
    threads.append(t)

for t in threads:
    t.join()
```

## Best Practices

1. **Always Use Context Manager**: Ensures proper resource cleanup
   ```python
   with KVSHLSFrameSource(...) as source:
       for frame, timestamp in source.read_frames():
           pass
   ```

2. **Monitor Metrics**: Track reconnections and errors
   ```python
   if metrics['reconnects_total'] > 10:
       alert("High reconnection rate")
   ```

3. **Configure Appropriate Session Duration**: Balance between API calls and freshness
   ```python
   # Production: 5-30 minutes
   hls_session_seconds=900
   ```

4. **Implement Health Checks**: Monitor source health
   ```python
   if not source.is_healthy():
       # Alert or restart
       pass
   ```

5. **Use Separate Threads**: One thread per camera
   ```python
   def camera_worker(camera_id, stream_name):
       source = KVSHLSFrameSource(...)
       with source:
           for frame, timestamp in source.read_frames():
               process(frame)
   ```

6. **Handle Errors Gracefully**: Don't crash on temporary failures
   ```python
   while True:
       try:
           with source:
               for frame, timestamp in source.read_frames():
                   pass
       except FrameSourceError as e:
           logger.error(f"Error: {e}")
           time.sleep(60)  # Wait before retry
   ```

## See Also

- [Configuration Guide](CONFIG.md)
- [Detector Documentation](DETECTORS.md)
- [Publisher Documentation](PUBLISHERS.md)
- [AWS KVS Documentation](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/what-is-kinesis-video.html)
