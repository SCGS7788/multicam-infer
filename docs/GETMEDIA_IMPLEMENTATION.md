# Step 12: GetMedia Low-Latency Upgrade Plan

## 🎯 Overview

This document outlines the plan to upgrade from HLS-based frame streaming (10-30s latency) to GetMedia API (1-3s latency) for AWS Kinesis Video Streams integration.

**Status:** Planning/Stub Implementation  
**Priority:** Future Enhancement  
**Complexity:** High  
**Estimated Effort:** 3-4 weeks  

## 📊 Latency Comparison

| Mode | Latency | Complexity | Reliability | Use Case |
|------|---------|------------|-------------|----------|
| **HLS** | 10-30s | Low | High | General monitoring, playback |
| **GetMedia** | 1-3s | High | Medium | Real-time alerts, fast response |

## 🏗️ Architecture

### Current: HLS-Based Streaming

```
┌─────────────┐
│ KVS Stream  │
└──────┬──────┘
       │ GetHLSStreamingSessionURL
       ▼
┌─────────────┐
│ HLS Master  │
│  Playlist   │
└──────┬──────┘
       │ .m3u8
       ▼
┌─────────────┐
│ HLS Segments│
│ (.ts files) │
└──────┬──────┘
       │ Download & Decode
       ▼
┌─────────────┐
│   Frames    │
│ (cv2.VideoCapture)│
└─────────────┘

Latency: 10-30 seconds
Pros: Simple, reliable, no parsing
Cons: High latency
```

### Future: GetMedia-Based Streaming

```
┌─────────────┐
│ KVS Stream  │
└──────┬──────┘
       │ GetMedia API
       ▼
┌─────────────┐
│MKV Fragment │
│   Stream    │
└──────┬──────┘
       │ Real-time MKV parsing
       ▼
┌─────────────┐
│ H.264/H.265 │
│ NAL Units   │
└──────┬──────┘
       │ Video decoder
       ▼
┌─────────────┐
│   Frames    │
│ (numpy arrays)│
└─────────────┘

Latency: 1-3 seconds
Pros: Low latency, real-time
Cons: Complex parsing, connection management
```

## 🔧 Implementation Options

### Option 1: GStreamer Pipeline (⭐ Recommended)

**Pros:**
- ✅ Mature and battle-tested
- ✅ Handles all codecs (H.264, H.265, VP8, VP9)
- ✅ Built-in error recovery
- ✅ Hardware acceleration support
- ✅ Active development and community

**Cons:**
- ❌ External dependency (GStreamer 1.0+)
- ❌ Platform-specific installation
- ❌ Larger installation size

**Pipeline:**
```python
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

pipeline = Gst.parse_launch(
    "appsrc name=src ! "
    "matroskademux ! "
    "h264parse ! "
    "avdec_h264 ! "
    "videoconvert ! "
    "video/x-raw,format=RGB ! "
    "appsink name=sink emit-signals=true"
)

# Get elements
appsrc = pipeline.get_by_name('src')
appsink = pipeline.get_by_name('sink')

# Connect signal
appsink.connect('new-sample', on_new_frame_callback)

# Start pipeline
pipeline.set_state(Gst.State.PLAYING)

# Push MKV data from GetMedia
buffer = Gst.Buffer.new_wrapped(mkv_chunk)
appsrc.emit('push-buffer', buffer)
```

**Installation:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    python3-gst-1.0 \
    python3-gi

# macOS
brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav
pip install PyGObject

# Python packages
pip install PyGObject>=3.42.0
```

### Option 2: AWS KVS Parser Library (C++ Binding)

**Pros:**
- ✅ Official AWS solution
- ✅ Optimized for KVS streams
- ✅ Handles KVS-specific metadata

**Cons:**
- ❌ Requires C++ compilation
- ❌ Python bindings needed (pybind11 or ctypes)
- ❌ Less maintained
- ❌ Platform-specific builds

**Implementation:**
```bash
# Clone AWS parser library
git clone https://github.com/awslabs/amazon-kinesis-video-streams-parser-library.git
cd amazon-kinesis-video-streams-parser-library

# Build library
mkdir build && cd build
cmake .. -DBUILD_DEPENDENCIES=ON
make

# Create Python bindings (pybind11)
# See docs/PYTHON_BINDINGS.md
```

**Usage:**
```python
from kvs_parser import KVSStreamParser

parser = KVSStreamParser()
parser.set_callback(on_frame_decoded)

# Feed MKV data from GetMedia
for chunk in getmedia_stream:
    parser.parse(chunk)
```

### Option 3: Custom MKV Parser + FFmpeg

**Pros:**
- ✅ Full control over parsing
- ✅ Lightweight dependencies
- ✅ Cross-platform

**Cons:**
- ❌ Complex implementation
- ❌ Need to handle edge cases
- ❌ Manual EBML/MKV parsing
- ❌ More maintenance burden

**Implementation:**
```python
# EBML/MKV parsing
import struct
from io import BytesIO

# FFmpeg decoding
import av

class MKVParser:
    def __init__(self):
        self.codec = av.CodecContext.create('h264', 'r')
    
    def parse_mkv_chunk(self, data: bytes):
        # Parse EBML header
        # Parse Matroska segments
        # Extract clusters and blocks
        # Yield H.264 NAL units
        pass
    
    def decode_h264(self, nal_units: bytes) -> np.ndarray:
        packet = av.Packet(nal_units)
        frames = self.codec.decode(packet)
        if frames:
            return frames[0].to_ndarray(format='rgb24')
        return None
```

**Dependencies:**
```bash
pip install av>=10.0.0  # FFmpeg bindings
pip install ebml-lite>=0.1.0  # Optional EBML parsing
```

## 📝 Implementation Phases

### Phase 1: Basic GetMedia Connection ✅ (Complete)

- [x] Define interfaces matching `KVSHLSFrameSource`
- [x] Document architecture and options
- [x] Create stub implementation with TODOs
- [ ] Implement AWS client initialization
- [ ] Implement `GetDataEndpoint` call
- [ ] Implement `GetMedia` stream start
- [ ] Implement fragment reader thread

**Files:**
- ✅ `src/kvs_infer/frame_source/getmedia_stub.py` (606 lines)
- ✅ `docs/GETMEDIA_IMPLEMENTATION.md` (this file)

### Phase 2: MKV Parsing ⏳ (Pending)

**Option A: GStreamer** (Recommended)
- [ ] Install GStreamer dependencies
- [ ] Create GStreamer pipeline
- [ ] Implement appsrc data feeding
- [ ] Implement appsink frame extraction
- [ ] Handle pipeline errors and reconnection

**Option B: AWS Parser**
- [ ] Build KVS parser library
- [ ] Create Python bindings
- [ ] Integrate parser callbacks
- [ ] Handle parsing errors

**Option C: Custom Parser**
- [ ] Implement EBML parser
- [ ] Implement Matroska parser
- [ ] Extract H.264 NAL units
- [ ] Integrate FFmpeg decoder

**Timeline:** 1-2 weeks

### Phase 3: Frame Decoding ⏳ (Pending)

- [ ] Extract H.264/H.265 frames from MKV
- [ ] Decode to RGB numpy arrays
- [ ] Implement frame queue (thread-safe)
- [ ] Handle frame timestamps
- [ ] Calculate end-to-end latency
- [ ] Implement frame dropping (if queue full)

**Timeline:** 1 week

### Phase 4: Error Handling & Recovery ⏳ (Pending)

- [ ] Implement reconnection logic with continuation tokens
- [ ] Handle MKV parsing errors gracefully
- [ ] Monitor fragment age and skip stale data
- [ ] Implement health checks
- [ ] Add exponential backoff for retries
- [ ] Handle codec changes mid-stream

**Timeline:** 1 week

### Phase 5: Testing & Optimization ⏳ (Pending)

- [ ] Unit tests with mock GetMedia responses
- [ ] Integration tests with real KVS streams
- [ ] Performance testing and optimization
- [ ] Latency measurements and tuning
- [ ] Memory profiling and optimization
- [ ] Load testing with multiple streams

**Timeline:** 1 week

## 🔧 Configuration

### Current Configuration (HLS only)

```yaml
cameras:
  - id: cam-001
    kvs_stream_name: cam-001-stream
    playback:
      mode: HLS
      retention_required: true
    fps_target: 10
```

### Future Configuration (HLS or GetMedia)

```yaml
cameras:
  - id: cam-001
    kvs_stream_name: cam-001-stream
    playback:
      mode: GETMEDIA  # or HLS
      retention_required: false  # Not needed for GetMedia
      
      # GetMedia-specific settings
      getmedia:
        start_selector: NOW  # NOW, EARLIEST, SERVER_TIMESTAMP, PRODUCER_TIMESTAMP
        max_fragment_age_seconds: 30
        chunk_size: 65536  # Bytes per read (64KB)
        reconnect_delay_seconds: 2
        max_reconnect_attempts: 10
        
        # Parser settings (if using GStreamer)
        parser:
          type: gstreamer  # gstreamer, kvs_parser, custom
          pipeline: "appsrc ! matroskademux ! h264parse ! avdec_h264 ! videoconvert ! appsink"
          
        # Frame queue settings
        frame_queue:
          max_size: 100  # Drop frames if queue full
          timeout_seconds: 1.0
    
    fps_target: 30  # Higher FPS possible with lower latency
```

### Configuration Schema Updates

```python
# src/kvs_infer/config.py

from pydantic import BaseModel, Field
from typing import Optional, Literal

class GetMediaConfig(BaseModel):
    """GetMedia-specific configuration."""
    start_selector: Literal["NOW", "EARLIEST", "SERVER_TIMESTAMP", "PRODUCER_TIMESTAMP"] = "NOW"
    max_fragment_age_seconds: int = Field(default=30, ge=1, le=300)
    chunk_size: int = Field(default=65536, ge=4096, le=1048576)
    reconnect_delay_seconds: int = Field(default=2, ge=1, le=60)
    max_reconnect_attempts: int = Field(default=10, ge=1, le=100)

class PlaybackConfig(BaseModel):
    """Playback configuration."""
    mode: Literal["HLS", "GETMEDIA"] = "HLS"
    retention_required: bool = True
    getmedia: Optional[GetMediaConfig] = None
```

## 🔄 Migration Path

### Step 1: Development & Testing (Weeks 1-3)

1. Implement GetMedia with GStreamer
2. Test with single camera stream
3. Compare latency with HLS mode
4. Identify and fix issues

### Step 2: Staged Rollout (Week 4)

1. Deploy alongside HLS (both modes supported)
2. Enable GetMedia for non-critical cameras
3. Monitor metrics and stability
4. Gradual migration camera by camera

### Step 3: Production (Week 5+)

1. Enable GetMedia for all cameras (if stable)
2. Keep HLS as fallback mode
3. Monitor latency improvements
4. Optimize based on real-world usage

### Step 4: HLS Deprecation (Future)

1. After 3+ months of stable GetMedia
2. Consider deprecating HLS mode
3. Or keep both modes for different use cases

## 📊 Success Metrics

### Performance Metrics

| Metric | HLS Baseline | GetMedia Target |
|--------|--------------|-----------------|
| **End-to-end latency** | 10-30s | 1-3s |
| **Frame processing rate** | 5-10 FPS | 15-30 FPS |
| **Connection stability** | 99.9% | 99.5% |
| **Memory usage per stream** | 50-100 MB | 100-200 MB |
| **CPU usage per stream** | 5-10% | 10-20% |

### Key Performance Indicators (KPIs)

- ✅ **Latency reduction**: >80% improvement (10-30s → 1-3s)
- ✅ **Alert response time**: <5s from detection to alert
- ✅ **Stream reliability**: >99% uptime
- ✅ **Frame loss rate**: <1% of frames dropped
- ✅ **Reconnection time**: <5s after connection loss

## 🧪 Testing Plan

### Unit Tests

```python
# tests/test_getmedia.py

def test_getmedia_initialization():
    """Test GetMedia frame source initialization."""
    source = KVSGetMediaFrameSource(
        camera_id="test-cam",
        stream_name="test-stream",
        region="us-east-1"
    )
    assert source.camera_id == "test-cam"
    assert not source._is_running

def test_start_selector_builder():
    """Test start selector building."""
    source = KVSGetMediaFrameSource(...)
    
    # NOW selector
    selector = source._build_start_selector()
    assert selector["StartSelectorType"] == "NOW"
    
    # TIMESTAMP selector
    source.start_selector_type = GetMediaStartSelectorType.SERVER_TIMESTAMP
    source.timestamp = datetime.now()
    selector = source._build_start_selector()
    assert "StartTimestamp" in selector

@mock_getmedia
def test_getmedia_stream():
    """Test GetMedia stream with mocked responses."""
    # Mock GetMedia API responses
    # Test fragment reading
    # Verify frame extraction
```

### Integration Tests

```python
# tests/integration/test_getmedia_integration.py

def test_real_kvs_stream():
    """Integration test with real KVS stream."""
    # Requires: Real KVS stream with test data
    source = KVSGetMediaFrameSource(
        camera_id="integration-test",
        stream_name=os.environ["TEST_KVS_STREAM"],
        region="us-east-1"
    )
    
    with source:
        frames_read = 0
        start_time = time.time()
        
        while frames_read < 100 and (time.time() - start_time) < 30:
            success, frame = source.read_frame()
            if success:
                frames_read += 1
                assert frame.shape[2] == 3  # RGB
        
        assert frames_read >= 100
        
        # Check latency
        metrics = source.get_metrics()
        assert metrics["latency_ms"] < 3000  # <3s latency
```

### Performance Tests

```python
# tests/performance/test_getmedia_performance.py

def test_latency_measurements():
    """Measure end-to-end latency."""
    source = KVSGetMediaFrameSource(...)
    
    latencies = []
    for _ in range(1000):
        success, frame = source.read_frame()
        if success:
            metrics = source.get_metrics()
            latencies.append(metrics["latency_ms"])
    
    avg_latency = np.mean(latencies)
    p95_latency = np.percentile(latencies, 95)
    p99_latency = np.percentile(latencies, 99)
    
    assert avg_latency < 2000  # Avg <2s
    assert p95_latency < 3000  # P95 <3s
    assert p99_latency < 5000  # P99 <5s

def test_multi_stream_load():
    """Test multiple concurrent GetMedia streams."""
    num_streams = 10
    sources = []
    
    for i in range(num_streams):
        source = KVSGetMediaFrameSource(
            camera_id=f"load-test-{i}",
            stream_name=f"test-stream-{i}",
            region="us-east-1"
        )
        sources.append(source)
    
    # Start all streams
    for source in sources:
        source.start()
    
    # Read frames from all streams
    # Measure CPU/memory usage
    # Verify no crashes or hangs
    
    # Cleanup
    for source in sources:
        source.stop()
```

## 📚 References

### AWS Documentation

- [GetMedia API Reference](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/API_dataplane_GetMedia.html)
- [KVS Data Plane APIs](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/API_Operations_Amazon_Kinesis_Video_Streams_Media.html)
- [KVS Stream Parser Library](https://github.com/awslabs/amazon-kinesis-video-streams-parser-library)

### Video Format Documentation

- [Matroska (MKV) Specification](https://www.matroska.org/technical/specs/index.html)
- [EBML Specification](https://github.com/ietf-wg-cellar/ebml-specification)
- [H.264 Specification (ITU-T)](https://www.itu.int/rec/T-REC-H.264)
- [H.265/HEVC Specification](https://www.itu.int/rec/T-REC-H.265)

### Library Documentation

- [GStreamer Documentation](https://gstreamer.freedesktop.org/documentation/)
- [PyGObject Documentation](https://pygobject.readthedocs.io/)
- [PyAV (FFmpeg) Documentation](https://pyav.org/)

### Related Projects

- [Amazon KVS WebRTC SDK](https://github.com/awslabs/amazon-kinesis-video-streams-webrtc-sdk-c)
- [GStreamer KVS Sink Plugin](https://github.com/awslabs/amazon-kinesis-video-streams-producer-sdk-cpp)

## 🚀 Quick Start (When Implemented)

### 1. Install Dependencies

```bash
# GStreamer (Ubuntu/Debian)
sudo apt-get install -y gstreamer1.0-tools gstreamer1.0-plugins-{base,good,bad,ugly} python3-gst-1.0

# Python packages
pip install PyGObject>=3.42.0
```

### 2. Update Configuration

```yaml
# cameras.yaml
cameras:
  - id: cam-001
    playback:
      mode: GETMEDIA  # Switch to GetMedia
      getmedia:
        start_selector: NOW
```

### 3. Run Application

```bash
python -m src.kvs_infer.main --config cameras.yaml
```

### 4. Monitor Metrics

```bash
# Check Prometheus metrics
curl http://localhost:9090/metrics | grep kvs_getmedia

# Key metrics:
# - kvs_getmedia_latency_ms: End-to-end latency
# - kvs_getmedia_frames_read: Frames processed
# - kvs_getmedia_connection_resets: Reconnections
# - kvs_getmedia_parse_errors: Parsing errors
```

## ⚠️ Known Limitations & Considerations

### 1. **No Data Retention Required**
- GetMedia streams from live position
- Cannot seek to historical data
- Must handle stream interruptions

### 2. **Connection Management**
- GetMedia connections can drop
- Need robust reconnection logic
- Use continuation tokens for seamless resume

### 3. **Parsing Complexity**
- MKV format is complex
- Need to handle codec changes
- Different streams may use different codecs

### 4. **Resource Usage**
- Higher CPU usage (parsing + decoding)
- More memory (frame queues)
- More network connections (one per camera)

### 5. **Codec Support**
- H.264 most common (widely supported)
- H.265/HEVC (needs specific decoder)
- VP8/VP9 (less common in KVS)

## 📋 Checklist Before Production

- [ ] Comprehensive unit tests (>80% coverage)
- [ ] Integration tests with real KVS streams
- [ ] Performance benchmarking (latency, CPU, memory)
- [ ] Error handling and recovery tested
- [ ] Documentation complete
- [ ] Configuration migration guide
- [ ] Monitoring and alerting setup
- [ ] Rollback plan documented
- [ ] Load testing completed
- [ ] Security review (IAM permissions, data handling)

## 🎯 Success Criteria

✅ **Must Have:**
- Latency <3s (vs 10-30s with HLS)
- Stability >99.5% uptime
- Graceful error recovery
- Matching feature parity with HLS mode
- Clear documentation

⭐ **Nice to Have:**
- Latency <1s
- Support for multiple codecs (H.264, H.265, VP8)
- Automatic quality adjustment based on bandwidth
- Frame interpolation for missing frames
- Hardware-accelerated decoding

---

**Document Status:** Complete  
**Last Updated:** October 13, 2025  
**Next Review:** When Phase 1 implementation begins
