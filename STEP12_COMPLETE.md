# Step 12 Complete: GetMedia Low-Latency Upgrade Path (Stub Implementation)

## ✅ Overview

Step 12 has been successfully completed! We've created a comprehensive stub implementation and documentation for upgrading from HLS-based streaming (10-30s latency) to GetMedia API (1-3s latency) for AWS Kinesis Video Streams.

**Status:** Stub Implementation Complete + Comprehensive Documentation  
**Implementation Priority:** Future Enhancement  
**Estimated Full Implementation:** 3-4 weeks  

## 📊 Summary

### What Was Delivered

| Component | Status | Lines | Description |
|-----------|--------|-------|-------------|
| **GetMedia Stub** | ✅ Complete | 606 | Full interface definition with TODOs |
| **Implementation Docs** | ✅ Complete | 480 | Comprehensive implementation guide |
| **Config Example** | ✅ Updated | +50 | GetMedia configuration examples |
| **Architecture Docs** | ✅ Complete | - | Detailed architecture and options |

## 📁 Files Created/Modified

### 1. `src/kvs_infer/frame_source/getmedia_stub.py` (606 lines)

Comprehensive stub implementation with:

**Classes:**
- `PlaybackMode` - Enum for HLS vs GETMEDIA
- `GetMediaStartSelectorType` - Start selector types for GetMedia API
- `KVSGetMediaFrameSource` - Main frame source class (stub)
- `MKVFragment` - Helper class for MKV parsing (stub)
- `H264Decoder` - Helper class for H.264 decoding (stub)

**Key Methods (with TODOs):**
```python
class KVSGetMediaFrameSource:
    def start() -> None:
        """Start GetMedia stream and initialize MKV parser."""
        # TODO: Initialize AWS clients
        # TODO: Get data endpoint
        # TODO: Start GetMedia stream
        # TODO: Initialize MKV parser
        # TODO: Start fragment reader thread
    
    def read_frame() -> Tuple[bool, Optional[np.ndarray]]:
        """Read next decoded frame."""
        # TODO: Pull from frame queue
        # TODO: Calculate latency
        # Returns: (success, frame_array)
    
    def _get_data_endpoint() -> None:
        """Get data endpoint for GetMedia API."""
        # TODO: Call GetDataEndpoint
        # TODO: Initialize kinesis-video-media client
    
    def _start_getmedia_stream() -> None:
        """Start GetMedia stream with start selector."""
        # TODO: Build start selector
        # TODO: Call GetMedia
        # TODO: Store continuation token
    
    def _initialize_parser() -> None:
        """Initialize MKV parser (GStreamer/AWS/Custom)."""
        # TODO: Choose parser implementation
        # TODO: Set up decoding pipeline
    
    def _fragment_reader_loop() -> None:
        """Main loop for reading MKV fragments."""
        # TODO: Read chunks from stream
        # TODO: Push to parser
        # TODO: Handle errors and reconnection
    
    def stop() -> None:
        """Stop stream and cleanup."""
        # TODO: Stop reader thread
        # TODO: Close stream
        # TODO: Cleanup parser
```

**Factory Function:**
```python
def create_frame_source(
    camera_id: str,
    stream_name: str,
    playback_config: PlaybackConfig,
    region: str = "us-east-1"
):
    """
    Create HLS or GetMedia frame source based on config.
    
    Seamlessly switches between modes:
    - playback.mode: "HLS" → KVSHLSFrameSource
    - playback.mode: "GETMEDIA" → KVSGetMediaFrameSource
    """
```

### 2. `docs/GETMEDIA_IMPLEMENTATION.md` (480 lines)

Comprehensive implementation guide covering:

**📋 Contents:**

1. **Overview & Latency Comparison**
   - HLS: 10-30s latency (simple, reliable)
   - GetMedia: 1-3s latency (complex, real-time)

2. **Architecture Diagrams**
   - Current HLS-based flow
   - Future GetMedia-based flow
   - Component interactions

3. **Implementation Options (3 approaches)**

   **Option 1: GStreamer Pipeline** ⭐ (Recommended)
   - Pros: Mature, handles all codecs, hardware acceleration
   - Cons: External dependency
   - Pipeline: `appsrc ! matroskademux ! h264parse ! avdec_h264 ! videoconvert ! appsink`
   - Installation guide for Ubuntu/Debian/macOS
   
   **Option 2: AWS KVS Parser Library**
   - Pros: Official AWS solution
   - Cons: C++ binding required, less maintained
   - Build and integration guide
   
   **Option 3: Custom MKV Parser + FFmpeg**
   - Pros: Lightweight, full control
   - Cons: Complex, manual EBML parsing
   - Implementation guide with av/ffmpeg-python

4. **Implementation Phases (5 phases)**
   - Phase 1: Basic GetMedia Connection ✅
   - Phase 2: MKV Parsing ⏳
   - Phase 3: Frame Decoding ⏳
   - Phase 4: Error Handling & Recovery ⏳
   - Phase 5: Testing & Optimization ⏳

5. **Configuration Schema**
   ```yaml
   playback:
     mode: GETMEDIA
     getmedia:
       start_selector: NOW
       max_fragment_age_seconds: 30
       chunk_size: 65536
       parser:
         type: gstreamer
       frame_queue:
         max_size: 100
   ```

6. **Migration Path**
   - Development & testing (Weeks 1-3)
   - Staged rollout (Week 4)
   - Production deployment (Week 5+)
   - HLS deprecation (Future)

7. **Success Metrics**
   | Metric | HLS | GetMedia Target |
   |--------|-----|-----------------|
   | Latency | 10-30s | 1-3s |
   | FPS | 5-10 | 15-30 |
   | Stability | 99.9% | 99.5% |

8. **Testing Plan**
   - Unit tests with mocked GetMedia
   - Integration tests with real streams
   - Performance benchmarks
   - Load testing

9. **References**
   - AWS GetMedia API docs
   - MKV/EBML specifications
   - GStreamer documentation
   - Related projects and libraries

### 3. `config/cameras.example.yaml` (Updated)

Added comprehensive GetMedia configuration example:

```yaml
# ============================================================================
# ADVANCED: GetMedia Mode (Low Latency) - Future Implementation
# ============================================================================
# When GetMedia is implemented, use this configuration for real-time streaming:

  - id: realtime-camera
    kvs_stream_name: realtime-stream
    enabled: true
    
    # GetMedia Configuration (Low Latency)
    playback:
      mode: GETMEDIA                 # Use GetMedia API instead of HLS
      retention_required: false      # Not needed for GetMedia (live only)
      
      # GetMedia-specific settings
      getmedia:
        start_selector: NOW          # NOW, EARLIEST, SERVER_TIMESTAMP, etc.
        max_fragment_age_seconds: 30
        chunk_size: 65536            # 64KB chunks
        reconnect_delay_seconds: 2
        max_reconnect_attempts: 10
        
        # Parser configuration
        parser:
          type: gstreamer            # gstreamer, kvs_parser, or custom
          
        # Frame queue settings
        frame_queue:
          max_size: 100              # Backpressure control
          timeout_seconds: 1.0
    
    fps_target: 30                   # Higher FPS with lower latency
    
    pipeline:
      - type: weapon
        enabled: true
        weapon:
          conf_threshold: 0.7
          temporal_confirm:
            frames: 2                # Reduce from 3 due to lower latency
```

## 🎯 Key Features of the Stub

### 1. Interface Compatibility

The `KVSGetMediaFrameSource` class provides the **same interface** as `KVSHLSFrameSource`:

```python
# Both modes use identical interface
with frame_source:  # Context manager
    while running:
        success, frame = frame_source.read_frame()
        if success:
            process_frame(frame)
        
        metrics = frame_source.get_metrics()
        is_healthy = frame_source.is_healthy()
```

### 2. Configuration-Based Switching

```python
from src.kvs_infer.frame_source.getmedia_stub import create_frame_source

# Automatically creates correct frame source based on config
frame_source = create_frame_source(
    camera_id="cam-001",
    stream_name="stream-001",
    playback_config=config.playback,  # mode: HLS or GETMEDIA
    region="us-east-1"
)
```

### 3. Comprehensive Metrics

```python
metrics = frame_source.get_metrics()
# {
#     "frames_read": 1000,
#     "fragments_processed": 150,
#     "bytes_received": 10485760,  # 10MB
#     "parse_errors": 0,
#     "decode_errors": 2,
#     "connection_resets": 1,
#     "last_frame_timestamp": 1697200000.0,
#     "latency_ms": 1500  # 1.5s latency
# }
```

### 4. Multiple Start Selector Types

```python
# Start from live position (lowest latency)
source = KVSGetMediaFrameSource(
    start_selector_type=GetMediaStartSelectorType.NOW
)

# Start from beginning of retention
source = KVSGetMediaFrameSource(
    start_selector_type=GetMediaStartSelectorType.EARLIEST
)

# Start from specific timestamp
source = KVSGetMediaFrameSource(
    start_selector_type=GetMediaStartSelectorType.SERVER_TIMESTAMP,
    timestamp=datetime(2025, 10, 13, 12, 0, 0)
)

# Resume from previous session
source = KVSGetMediaFrameSource(
    start_selector_type=GetMediaStartSelectorType.CONTINUATION_TOKEN
)
```

### 5. Error Recovery Patterns

```python
# Automatic reconnection with continuation tokens
def _reconnect(self) -> None:
    """
    Reconnect with continuation token if available,
    otherwise use last fragment timestamp.
    """
    if self._continuation_token:
        # Seamless resume from exact position
        selector = GetMediaStartSelectorType.CONTINUATION_TOKEN
    elif self._last_fragment_timestamp:
        # Resume from last known timestamp
        selector = GetMediaStartSelectorType.SERVER_TIMESTAMP
    else:
        # Start from NOW (may lose some frames)
        selector = GetMediaStartSelectorType.NOW
```

## 🔧 Implementation Roadmap

### Phase 1: Basic GetMedia Connection ✅ (Complete)

- [x] Define interfaces matching KVSHLSFrameSource
- [x] Document architecture and implementation options
- [x] Create stub implementation with comprehensive TODOs
- [x] Add configuration schema
- [x] Create factory function for mode switching
- [ ] **Next:** Implement AWS client initialization
- [ ] **Next:** Implement GetDataEndpoint call
- [ ] **Next:** Implement GetMedia stream start

**Timeline:** Foundation complete, ready for implementation

### Phase 2: MKV Parsing ⏳ (1-2 weeks)

**Recommended Approach: GStreamer**

```python
# GStreamer pipeline for MKV parsing + H.264 decoding
pipeline = Gst.parse_launch(
    "appsrc name=src ! "                    # Feed MKV data
    "matroskademux ! "                      # Parse MKV
    "h264parse ! "                          # Parse H.264
    "avdec_h264 ! "                         # Decode H.264
    "videoconvert ! "                       # Convert format
    "video/x-raw,format=RGB ! "             # RGB output
    "appsink name=sink emit-signals=true"  # Extract frames
)
```

**Installation:**
```bash
# Ubuntu/Debian
sudo apt-get install -y gstreamer1.0-tools \
    gstreamer1.0-plugins-{base,good,bad,ugly} \
    python3-gst-1.0

# Python
pip install PyGObject>=3.42.0
```

### Phase 3: Frame Decoding ⏳ (1 week)

- Extract frames from GStreamer appsink
- Convert to numpy RGB arrays
- Implement thread-safe frame queue
- Calculate latency metrics

### Phase 4: Error Handling ⏳ (1 week)

- Reconnection with continuation tokens
- Exponential backoff for retries
- Fragment age monitoring
- Codec change handling

### Phase 5: Testing & Optimization ⏳ (1 week)

- Unit tests with mocked GetMedia
- Integration tests with real KVS streams
- Performance benchmarking
- Memory profiling

## 📊 Latency Improvement Expectations

### Current (HLS)

```
Producer → KVS → HLS Segmentation → S3 → Client Download → Decode
    ↓        ↓            ↓            ↓         ↓            ↓
  100ms    2-5s         2-5s        1-3s     1-5s         100ms
  
Total: 10-30 seconds
```

### Future (GetMedia)

```
Producer → KVS → GetMedia Stream → MKV Parse → Decode
    ↓        ↓            ↓            ↓          ↓
  100ms   500ms        500ms       200ms      200ms
  
Total: 1-3 seconds (83-90% improvement)
```

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/test_getmedia.py
def test_getmedia_initialization()
def test_start_selector_builder()
def test_metrics_tracking()
@mock_getmedia
def test_fragment_reading()
```

### Integration Tests

```python
# tests/integration/test_getmedia_integration.py
def test_real_kvs_stream():
    """Test with real KVS stream (requires AWS credentials)."""
    source = KVSGetMediaFrameSource(...)
    with source:
        latencies = []
        for _ in range(1000):
            success, frame = source.read_frame()
            metrics = source.get_metrics()
            latencies.append(metrics["latency_ms"])
        
        assert np.mean(latencies) < 2000  # <2s avg
        assert np.percentile(latencies, 95) < 3000  # <3s P95
```

### Performance Tests

```python
# tests/performance/test_getmedia_performance.py
def test_multi_stream_load():
    """Test 10 concurrent GetMedia streams."""
    sources = [
        KVSGetMediaFrameSource(f"cam-{i}", ...)
        for i in range(10)
    ]
    # Measure CPU, memory, latency
```

## 📚 Documentation Provided

### 1. Implementation Guide (`docs/GETMEDIA_IMPLEMENTATION.md`)
- Complete architecture explanation
- 3 implementation options with pros/cons
- Step-by-step implementation phases
- Configuration examples
- Testing strategies
- Performance benchmarks

### 2. Code Documentation (Inline)
- Every method has comprehensive docstrings
- TODO comments with implementation hints
- Code examples in docstrings
- References to AWS documentation

### 3. Configuration Examples
- HLS mode (current)
- GetMedia mode (future)
- All GetMedia-specific settings

## 🚀 How to Use (When Implemented)

### 1. Update Configuration

```yaml
# cameras.yaml
cameras:
  - id: my-camera
    playback:
      mode: GETMEDIA  # Switch from HLS to GETMEDIA
      getmedia:
        start_selector: NOW
```

### 2. No Code Changes Required

```python
# Application code stays the same
from src.kvs_infer.frame_source.getmedia_stub import create_frame_source

# Automatically uses GetMedia if mode=GETMEDIA
frame_source = create_frame_source(
    camera_id=config.id,
    stream_name=config.kvs_stream_name,
    playback_config=config.playback,  # Uses mode from config
    region=config.aws.region
)

# Same interface as HLS
with frame_source:
    while True:
        success, frame = frame_source.read_frame()
        if success:
            process_frame(frame)
```

### 3. Monitor Metrics

```python
metrics = frame_source.get_metrics()
print(f"Latency: {metrics['latency_ms']}ms")
print(f"Frames: {metrics['frames_read']}")
print(f"Errors: {metrics['parse_errors']}")
```

## ⚠️ Important Notes

### 1. Implementation Required
- This is a **stub implementation** with interfaces defined
- Full implementation requires 3-4 weeks of development
- See `docs/GETMEDIA_IMPLEMENTATION.md` for roadmap

### 2. Dependencies
- GStreamer 1.0+ (recommended approach)
- Or AWS KVS Parser Library (C++ binding)
- Or custom MKV parser with av/ffmpeg-python

### 3. Resource Requirements
- Higher CPU usage (parsing + decoding)
- More memory (frame queues)
- More AWS API calls (GetMedia connections)

### 4. Testing Required
- Comprehensive testing before production
- Performance benchmarking
- Load testing with multiple streams

## ✅ Deliverables Checklist

- ✅ **GetMedia stub implementation** (606 lines)
  - Complete class structure
  - All methods defined with TODOs
  - Comprehensive docstrings
  - Helper classes (MKVFragment, H264Decoder)
  - Factory function for mode switching

- ✅ **Implementation documentation** (480 lines)
  - Architecture diagrams
  - 3 implementation options
  - 5-phase roadmap
  - Configuration guide
  - Testing strategy
  - Performance benchmarks

- ✅ **Configuration examples**
  - HLS mode (current)
  - GetMedia mode (future)
  - All settings documented

- ✅ **Interface compatibility**
  - Matches KVSHLSFrameSource interface
  - Seamless mode switching
  - Same metrics structure

## 📈 Success Metrics (When Implemented)

| Metric | Current (HLS) | Target (GetMedia) | Improvement |
|--------|---------------|-------------------|-------------|
| **Latency** | 10-30s | 1-3s | 83-90% |
| **FPS** | 5-10 | 15-30 | 100-200% |
| **Alert Response** | 10-30s | <5s | >80% |
| **Stability** | 99.9% | 99.5% | -0.4% |

## 🎯 Next Steps

### For Immediate Use:
1. Continue using HLS mode (current implementation)
2. Review GetMedia documentation
3. Evaluate use cases requiring low latency

### When Ready to Implement:
1. **Week 1:** Install GStreamer, implement AWS clients
2. **Week 2:** Implement MKV parsing with GStreamer
3. **Week 3:** Implement frame decoding and error handling
4. **Week 4:** Testing, optimization, staged rollout

### Decision Points:
- **Use HLS** for: General monitoring, playback, stable deployments
- **Use GetMedia** for: Real-time alerts, fast response, critical events

## 📝 Summary

✅ **Step 12 Complete!**

We've created a comprehensive foundation for GetMedia low-latency streaming:

1. **Stub Implementation** (606 lines)
   - Complete interface matching HLS mode
   - All methods defined with implementation TODOs
   - Factory function for seamless mode switching

2. **Documentation** (480 lines)
   - Complete implementation guide
   - 3 implementation options (GStreamer recommended)
   - 5-phase roadmap with timelines
   - Configuration examples
   - Testing strategies

3. **Configuration Examples**
   - Updated cameras.example.yaml
   - GetMedia-specific settings
   - Migration guide

**The foundation is complete and ready for full implementation when low-latency streaming is required.**

---

**Step 12: GetMedia Upgrade Path - COMPLETE** ✅  
**Implementation Status:** Stub + Documentation  
**Ready for:** Full implementation when needed  
**Timeline:** 3-4 weeks for complete implementation
