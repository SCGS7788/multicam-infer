"""
KVS GetMedia Frame Source - Low Latency Implementation (STUB)

This module provides a stub implementation for AWS Kinesis Video Streams GetMedia API,
designed for low-latency streaming scenarios. This is a future upgrade path from HLS.

GetMedia provides lower latency (~1-3 seconds) compared to HLS (~10-30 seconds) but
requires parsing MKV (Matroska) container format from the stream.

Implementation Status: STUB/TODO
This file defines the interfaces and provides a roadmap for implementation.

References:
- AWS KVS GetMedia API: https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/API_dataplane_GetMedia.html
- MKV Format: https://www.matroska.org/technical/specs/index.html
"""

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple

import boto3
import numpy as np
from botocore.exceptions import ClientError

from ..config import PlaybackConfig

logger = logging.getLogger(__name__)


class PlaybackMode(str, Enum):
    """Playback mode for KVS stream reading."""
    HLS = "HLS"
    GETMEDIA = "GETMEDIA"


class GetMediaStartSelectorType(str, Enum):
    """Start selector types for GetMedia API."""
    FRAGMENT_NUMBER = "FRAGMENT_NUMBER"
    SERVER_TIMESTAMP = "SERVER_TIMESTAMP"
    PRODUCER_TIMESTAMP = "PRODUCER_TIMESTAMP"
    NOW = "NOW"
    EARLIEST = "EARLIEST"
    CONTINUATION_TOKEN = "CONTINUATION_TOKEN"


class KVSGetMediaFrameSource:
    """
    Frame source for AWS Kinesis Video Streams using GetMedia API.
    
    This implementation provides lower latency streaming compared to HLS by:
    1. Using GetMedia API to stream MKV fragments directly
    2. Parsing MKV container format in real-time
    3. Extracting H.264/H.265 frames and decoding to numpy arrays
    
    Architecture:
    ┌─────────────────┐
    │  KVS Stream     │
    └────────┬────────┘
             │ GetMedia API
             ▼
    ┌─────────────────┐
    │ MKV Fragment    │
    │ Stream Parser   │
    └────────┬────────┘
             │ H.264/H.265
             ▼
    ┌─────────────────┐
    │ Video Decoder   │
    │ (GStreamer/FFmpeg)│
    └────────┬────────┘
             │ Frames
             ▼
    ┌─────────────────┐
    │ Frame Queue     │
    │ (numpy arrays)  │
    └─────────────────┘
    
    Implementation Options:
    
    Option 1: GStreamer Pipeline (Recommended)
    - Pros: Robust, handles all codecs, mature
    - Cons: External dependency, requires GStreamer 1.0+
    - Pipeline: appsrc ! matroskademux ! h264parse ! avdec_h264 ! videoconvert ! appsink
    
    Option 2: AWS KVS Parser Library (Python binding)
    - Pros: Official AWS solution, integrated
    - Cons: C++ binding required, less flexible
    - Repo: https://github.com/awslabs/amazon-kinesis-video-streams-parser-library
    
    Option 3: Pure Python MKV Parser + FFmpeg
    - Pros: No heavy dependencies
    - Cons: More complex, manual MKV parsing
    """

    def __init__(
        self,
        camera_id: str,
        stream_name: str,
        region: str = "us-east-1",
        start_selector_type: GetMediaStartSelectorType = GetMediaStartSelectorType.NOW,
        fragment_number: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        max_fragment_age_seconds: int = 30,
    ):
        """
        Initialize GetMedia frame source.
        
        Args:
            camera_id: Unique camera identifier for logging/metrics
            stream_name: KVS stream name
            region: AWS region
            start_selector_type: How to select the starting point in the stream
            fragment_number: Specific fragment number (if using FRAGMENT_NUMBER selector)
            timestamp: Timestamp to start from (if using SERVER/PRODUCER_TIMESTAMP)
            max_fragment_age_seconds: Maximum age of fragments to process (for error recovery)
        """
        self.camera_id = camera_id
        self.stream_name = stream_name
        self.region = region
        self.start_selector_type = start_selector_type
        self.fragment_number = fragment_number
        self.timestamp = timestamp
        self.max_fragment_age_seconds = max_fragment_age_seconds

        # AWS clients
        self._kvs_client: Optional[boto3.client] = None
        self._kvs_media_client: Optional[boto3.client] = None
        self._data_endpoint: Optional[str] = None

        # Stream state
        self._stream: Optional[object] = None  # GetMedia response stream
        self._is_running: bool = False
        self._last_fragment_timestamp: Optional[datetime] = None
        self._continuation_token: Optional[str] = None

        # Metrics
        self._metrics = {
            "frames_read": 0,
            "fragments_processed": 0,
            "bytes_received": 0,
            "parse_errors": 0,
            "decode_errors": 0,
            "connection_resets": 0,
            "last_frame_timestamp": None,
            "latency_ms": 0,
        }

        logger.info(
            f"[{self.camera_id}] Initialized KVSGetMediaFrameSource for stream '{stream_name}' "
            f"in region '{region}' with start_selector={start_selector_type.value}"
        )

    def start(self) -> None:
        """
        Start the GetMedia stream and initialize MKV parser.
        
        TODO: Implementation steps:
        1. Initialize AWS clients (KVS control plane + data plane)
        2. Get data endpoint for GetMedia API
        3. Call GetMedia with start selector
        4. Initialize MKV parser (GStreamer pipeline or custom parser)
        5. Start background thread/async task to read fragments
        6. Start frame decoder and populate frame queue
        """
        if self._is_running:
            logger.warning(f"[{self.camera_id}] GetMedia stream already running")
            return

        try:
            # TODO: Step 1 - Initialize AWS clients
            self._initialize_aws_clients()

            # TODO: Step 2 - Get data endpoint
            self._get_data_endpoint()

            # TODO: Step 3 - Start GetMedia stream
            self._start_getmedia_stream()

            # TODO: Step 4 - Initialize MKV parser
            self._initialize_parser()

            # TODO: Step 5 - Start fragment reader thread
            self._start_fragment_reader()

            self._is_running = True
            logger.info(f"[{self.camera_id}] GetMedia stream started successfully")

        except Exception as e:
            logger.error(f"[{self.camera_id}] Failed to start GetMedia stream: {e}")
            raise

    def _initialize_aws_clients(self) -> None:
        """Initialize AWS KVS clients for control and data plane operations."""
        # TODO: Implement AWS client initialization
        # Control plane client for GetDataEndpoint
        self._kvs_client = boto3.client("kinesisvideo", region_name=self.region)
        logger.debug(f"[{self.camera_id}] Initialized KVS control plane client")

    def _get_data_endpoint(self) -> None:
        """
        Get the data endpoint for GetMedia API.
        
        TODO: Implementation:
        ```python
        response = self._kvs_client.get_data_endpoint(
            StreamName=self.stream_name,
            APIName="GET_MEDIA"
        )
        self._data_endpoint = response['DataEndpoint']
        
        # Initialize data plane client with endpoint
        self._kvs_media_client = boto3.client(
            'kinesis-video-media',
            endpoint_url=self._data_endpoint,
            region_name=self.region
        )
        ```
        """
        logger.debug(f"[{self.camera_id}] TODO: Get data endpoint for GetMedia")
        raise NotImplementedError("GetMedia data endpoint retrieval not implemented")

    def _start_getmedia_stream(self) -> None:
        """
        Start the GetMedia stream with appropriate start selector.
        
        TODO: Implementation:
        ```python
        start_selector = self._build_start_selector()
        
        response = self._kvs_media_client.get_media(
            StreamName=self.stream_name,
            StartSelector=start_selector
        )
        
        # Response contains streaming body with MKV fragments
        self._stream = response['Payload']
        self._continuation_token = response.get('ContinuationToken')
        ```
        
        Start Selector Examples:
        - NOW: Start from current live position (lowest latency)
        - EARLIEST: Start from beginning of retention period
        - SERVER_TIMESTAMP: Start from specific server timestamp
        - PRODUCER_TIMESTAMP: Start from specific producer timestamp
        - FRAGMENT_NUMBER: Resume from specific fragment
        - CONTINUATION_TOKEN: Resume from previous session
        """
        logger.debug(f"[{self.camera_id}] TODO: Start GetMedia stream")
        raise NotImplementedError("GetMedia stream initialization not implemented")

    def _build_start_selector(self) -> dict:
        """
        Build the start selector for GetMedia request.
        
        Returns:
            Start selector dictionary for GetMedia API
        """
        selector = {"StartSelectorType": self.start_selector_type.value}

        if self.start_selector_type == GetMediaStartSelectorType.FRAGMENT_NUMBER:
            if not self.fragment_number:
                raise ValueError("fragment_number required for FRAGMENT_NUMBER selector")
            selector["AfterFragmentNumber"] = self.fragment_number

        elif self.start_selector_type in [
            GetMediaStartSelectorType.SERVER_TIMESTAMP,
            GetMediaStartSelectorType.PRODUCER_TIMESTAMP,
        ]:
            if not self.timestamp:
                raise ValueError(f"timestamp required for {self.start_selector_type.value} selector")
            selector["StartTimestamp"] = self.timestamp

        elif self.start_selector_type == GetMediaStartSelectorType.CONTINUATION_TOKEN:
            if not self._continuation_token:
                raise ValueError("continuation_token required for CONTINUATION_TOKEN selector")
            selector["ContinuationToken"] = self._continuation_token

        return selector

    def _initialize_parser(self) -> None:
        """
        Initialize MKV parser for processing GetMedia stream.
        
        TODO: Choose implementation approach:
        
        Approach 1: GStreamer Pipeline
        ```python
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        
        Gst.init(None)
        
        # Create pipeline: appsrc ! matroskademux ! h264parse ! avdec_h264 ! videoconvert ! appsink
        pipeline = Gst.parse_launch(
            "appsrc name=src ! "
            "matroskademux ! "
            "h264parse ! "
            "avdec_h264 ! "
            "videoconvert ! "
            "video/x-raw,format=RGB ! "
            "appsink name=sink emit-signals=true"
        )
        
        # Get appsrc and appsink elements
        self._appsrc = pipeline.get_by_name('src')
        self._appsink = pipeline.get_by_name('sink')
        
        # Connect to new-sample signal for frame extraction
        self._appsink.connect('new-sample', self._on_new_frame)
        
        # Start pipeline
        pipeline.set_state(Gst.State.PLAYING)
        ```
        
        Approach 2: AWS KVS Parser (C++ binding)
        ```python
        # Requires: pip install amazon-kinesis-video-streams-parser
        from kvs_parser import KVSStreamParser
        
        parser = KVSStreamParser()
        parser.set_callback(self._on_frame_decoded)
        ```
        
        Approach 3: Custom MKV Parser
        ```python
        from mkv_parser import EBMLParser, MatroskaParser
        
        self._ebml_parser = EBMLParser()
        self._mkv_parser = MatroskaParser()
        self._h264_decoder = H264Decoder()  # Using av/ffmpeg-python
        ```
        """
        logger.debug(f"[{self.camera_id}] TODO: Initialize MKV parser")
        raise NotImplementedError("MKV parser initialization not implemented")

    def _start_fragment_reader(self) -> None:
        """
        Start background thread to read MKV fragments from GetMedia stream.
        
        TODO: Implementation:
        ```python
        import threading
        
        self._reader_thread = threading.Thread(
            target=self._fragment_reader_loop,
            name=f"GetMedia-Reader-{self.camera_id}",
            daemon=True
        )
        self._reader_thread.start()
        ```
        """
        logger.debug(f"[{self.camera_id}] TODO: Start fragment reader thread")
        raise NotImplementedError("Fragment reader not implemented")

    def _fragment_reader_loop(self) -> None:
        """
        Main loop for reading MKV fragments from GetMedia stream.
        
        TODO: Implementation:
        ```python
        while self._is_running:
            try:
                # Read chunk from stream
                chunk = self._stream.read(chunk_size=65536)  # 64KB chunks
                
                if not chunk:
                    # Stream ended, reconnect
                    self._reconnect()
                    continue
                
                # Update metrics
                self._metrics['bytes_received'] += len(chunk)
                
                # Push to MKV parser (GStreamer appsrc or custom parser)
                self._push_to_parser(chunk)
                
                # Check fragment age for error recovery
                self._check_fragment_age()
                
            except Exception as e:
                logger.error(f"Error reading fragment: {e}")
                self._handle_read_error(e)
        ```
        """
        pass

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read the next decoded frame from the stream.
        
        Returns:
            Tuple of (success, frame) where frame is a numpy array in RGB format
            
        TODO: Implementation:
        ```python
        # Option 1: Pull from frame queue (populated by parser callback)
        if not self._frame_queue.empty():
            frame = self._frame_queue.get(timeout=1.0)
            self._metrics['frames_read'] += 1
            self._metrics['last_frame_timestamp'] = time.time()
            
            # Calculate latency (current time - frame producer timestamp)
            if hasattr(frame, 'producer_timestamp'):
                latency_ms = (time.time() - frame.producer_timestamp) * 1000
                self._metrics['latency_ms'] = latency_ms
            
            return True, frame.data
        
        return False, None
        ```
        
        Note: This method should match the interface of KVSHLSFrameSource.read_frame()
        for seamless switching between HLS and GetMedia modes.
        """
        # TODO: Implement frame reading from parser queue
        logger.debug(f"[{self.camera_id}] TODO: Read frame from parser queue")
        raise NotImplementedError("Frame reading not implemented")

    def _reconnect(self) -> None:
        """
        Reconnect to GetMedia stream after connection loss.
        
        TODO: Implementation:
        - Use continuation token if available
        - Otherwise use last fragment timestamp
        - Implement exponential backoff
        - Update metrics
        """
        logger.warning(f"[{self.camera_id}] TODO: Reconnect to GetMedia stream")
        self._metrics["connection_resets"] += 1
        raise NotImplementedError("Reconnection logic not implemented")

    def stop(self) -> None:
        """
        Stop the GetMedia stream and cleanup resources.
        
        TODO: Implementation steps:
        1. Set _is_running = False to stop reader thread
        2. Close GetMedia stream
        3. Stop MKV parser/GStreamer pipeline
        4. Join reader thread
        5. Cleanup resources
        """
        if not self._is_running:
            return

        logger.info(f"[{self.camera_id}] Stopping GetMedia stream...")
        self._is_running = False

        # TODO: Implement cleanup
        # - Stop reader thread
        # - Close stream
        # - Stop parser
        # - Clear frame queue

        logger.info(f"[{self.camera_id}] GetMedia stream stopped")

    def get_metrics(self) -> dict:
        """
        Get current metrics for this frame source.
        
        Returns:
            Dictionary containing:
            - frames_read: Total frames decoded
            - fragments_processed: Total MKV fragments processed
            - bytes_received: Total bytes received from GetMedia
            - parse_errors: Number of MKV parsing errors
            - decode_errors: Number of frame decoding errors
            - connection_resets: Number of stream reconnections
            - last_frame_timestamp: Timestamp of last frame
            - latency_ms: Current end-to-end latency in milliseconds
        """
        return self._metrics.copy()

    def is_healthy(self) -> bool:
        """
        Check if the frame source is healthy.
        
        Returns:
            True if receiving frames regularly, False otherwise
        """
        if not self._is_running:
            return False

        # TODO: Implement health checks
        # - Check if frames received in last N seconds
        # - Check error rate
        # - Check latency
        last_frame_time = self._metrics.get("last_frame_timestamp")
        if last_frame_time:
            age_seconds = time.time() - last_frame_time
            return age_seconds < 10  # No frames for 10s = unhealthy

        return False

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def __repr__(self) -> str:
        return (
            f"KVSGetMediaFrameSource(camera_id='{self.camera_id}', "
            f"stream='{self.stream_name}', running={self._is_running})"
        )


# ==============================================================================
# Frame Source Factory - Switch between HLS and GetMedia
# ==============================================================================

def create_frame_source(
    camera_id: str,
    stream_name: str,
    playback_config: PlaybackConfig,
    region: str = "us-east-1",
):
    """
    Factory function to create appropriate frame source based on playback mode.
    
    Args:
        camera_id: Camera identifier
        stream_name: KVS stream name
        playback_config: Playback configuration from cameras.yaml
        region: AWS region
        
    Returns:
        KVSHLSFrameSource or KVSGetMediaFrameSource based on playback_config.mode
        
    Example:
        ```python
        from src.kvs_infer.config import PlaybackConfig
        
        # HLS mode (higher latency, simpler)
        hls_config = PlaybackConfig(
            mode="HLS",
            retention_required=True
        )
        frame_source = create_frame_source("cam-001", "stream-001", hls_config)
        
        # GetMedia mode (lower latency, more complex)
        getmedia_config = PlaybackConfig(
            mode="GETMEDIA",
            retention_required=False
        )
        frame_source = create_frame_source("cam-001", "stream-001", getmedia_config)
        
        # Use the same interface regardless of mode
        with frame_source:
            while True:
                success, frame = frame_source.read_frame()
                if success:
                    # Process frame
                    process_frame(frame)
        ```
    """
    mode = getattr(playback_config, "mode", "HLS").upper()

    if mode == PlaybackMode.GETMEDIA.value:
        logger.info(
            f"[{camera_id}] Creating GetMedia frame source (low latency mode)"
        )
        return KVSGetMediaFrameSource(
            camera_id=camera_id,
            stream_name=stream_name,
            region=region,
            start_selector_type=GetMediaStartSelectorType.NOW,
        )
    else:
        # Default to HLS
        logger.info(
            f"[{camera_id}] Creating HLS frame source (standard latency mode)"
        )
        from .kvs_hls import KVSHLSFrameSource

        return KVSHLSFrameSource(
            camera_id=camera_id,
            stream_name=stream_name,
            region=region,
        )


# ==============================================================================
# Helper Classes for MKV Parsing (Stubs)
# ==============================================================================

class MKVFragment:
    """
    Represents a single MKV fragment from GetMedia stream.
    
    TODO: Implement MKV fragment parsing
    - Track ID (video/audio)
    - Timecode
    - Cluster data
    - Frame boundaries
    """

    def __init__(self, data: bytes):
        self.data = data
        self.track_id: Optional[int] = None
        self.timecode: Optional[int] = None
        self.frames: list = []

    def parse(self) -> None:
        """Parse MKV fragment and extract frames."""
        # TODO: Implement EBML/MKV parsing
        raise NotImplementedError("MKV fragment parsing not implemented")


class H264Decoder:
    """
    H.264 video decoder.
    
    TODO: Implement using av/ffmpeg-python or GStreamer
    """

    def __init__(self):
        pass

    def decode(self, h264_data: bytes) -> np.ndarray:
        """Decode H.264 NAL units to RGB frame."""
        # TODO: Implement H.264 decoding
        raise NotImplementedError("H.264 decoding not implemented")


# ==============================================================================
# Implementation Notes and References
# ==============================================================================

"""
IMPLEMENTATION ROADMAP:

Phase 1: Basic GetMedia Connection
- ✅ Define interfaces matching KVSHLSFrameSource
- ✅ Document architecture and options
- ⏳ Implement AWS client initialization
- ⏳ Implement GetDataEndpoint call
- ⏳ Implement GetMedia stream start
- ⏳ Implement fragment reader thread

Phase 2: MKV Parsing (Choose One Approach)
Option A: GStreamer (Recommended)
- Install: sudo apt-get install python3-gst-1.0 gstreamer1.0-plugins-{base,good,bad,ugly}
- Build pipeline: appsrc ! matroskademux ! h264parse ! avdec_h264 ! videoconvert ! appsink
- Handle callbacks for frame extraction
- Pros: Mature, handles all codecs, battle-tested
- Cons: Heavy dependency, requires GStreamer 1.0+

Option B: AWS KVS Parser Library
- Clone: https://github.com/awslabs/amazon-kinesis-video-streams-parser-library
- Build Python bindings (pybind11 or ctypes)
- Integrate with parser callbacks
- Pros: Official AWS solution
- Cons: Requires C++ compilation, less maintained

Option C: Custom Parser
- Use: ebml-lite or construct for EBML parsing
- Parse Matroska clusters and blocks
- Extract H.264 NAL units
- Decode using av/ffmpeg-python
- Pros: Lightweight, full control
- Cons: Complex, need to handle edge cases

Phase 3: Frame Decoding
- Extract H.264/H.265 frames from MKV
- Decode to RGB numpy arrays
- Populate frame queue
- Handle frame timestamps

Phase 4: Error Handling & Recovery
- Implement reconnection logic with continuation tokens
- Handle MKV parsing errors gracefully
- Monitor fragment age and skip stale data
- Implement health checks

Phase 5: Testing & Optimization
- Unit tests with mock GetMedia responses
- Integration tests with real KVS streams
- Performance testing and optimization
- Latency measurements and tuning

CONFIGURATION MIGRATION:

Current (HLS only):
```yaml
playback:
  mode: HLS
  retention_required: true
```

Future (HLS or GetMedia):
```yaml
playback:
  mode: GETMEDIA  # or HLS
  retention_required: false  # Not needed for GetMedia
  getmedia:
    start_selector: NOW  # NOW, EARLIEST, SERVER_TIMESTAMP, etc.
    max_fragment_age_seconds: 30
    chunk_size: 65536  # Bytes per read
```

LATENCY COMPARISON:

HLS Mode:
- Latency: 10-30 seconds (depends on segment size)
- Pros: Simple, no parsing needed, retry-friendly
- Cons: Higher latency, not suitable for real-time

GetMedia Mode:
- Latency: 1-3 seconds (near real-time)
- Pros: Low latency, real-time capable
- Cons: Complex parsing, connection management

DEPENDENCIES:

For GStreamer approach:
```
apt-get install:
- gstreamer1.0-tools
- gstreamer1.0-plugins-base
- gstreamer1.0-plugins-good
- gstreamer1.0-plugins-bad
- gstreamer1.0-plugins-ugly
- python3-gst-1.0

pip install:
- PyGObject>=3.42.0
```

For custom parser approach:
```
pip install:
- av>=10.0.0  # FFmpeg bindings
- ebml-lite>=0.1.0  # EBML parsing (optional)
```

REFERENCES:
- GetMedia API: https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/API_dataplane_GetMedia.html
- MKV Format: https://www.matroska.org/technical/specs/index.html
- KVS Parser: https://github.com/awslabs/amazon-kinesis-video-streams-parser-library
- GStreamer: https://gstreamer.freedesktop.org/documentation/
"""
