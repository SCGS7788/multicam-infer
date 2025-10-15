"""
HLS-based frame source for Kinesis Video Streams.
Handles HLS URL refresh, reconnection, and frame extraction with metrics.
"""

import logging
import time
import threading
import random
from typing import Optional, Tuple, Iterator
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from kvs_infer.utils import metrics as prom_metrics


logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class FrameSourceError(Exception):
    """Base exception for frame source errors."""
    pass


class KVSConnectionError(FrameSourceError):
    """KVS connection or API error."""
    pass


class HLSStreamError(FrameSourceError):
    """HLS stream reading error."""
    pass


# ============================================================================
# Metrics
# ============================================================================

@dataclass
class KVSHLSMetrics:
    """Metrics for KVS HLS frame source."""
    camera_id: str
    reconnects_total: int = 0
    frames_total: int = 0
    last_frame_timestamp: Optional[float] = None
    url_refreshes_total: int = 0
    read_errors_total: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/export."""
        return {
            "camera_id": self.camera_id,
            "reconnects_total": self.reconnects_total,
            "frames_total": self.frames_total,
            "last_frame_timestamp": self.last_frame_timestamp,
            "url_refreshes_total": self.url_refreshes_total,
            "read_errors_total": self.read_errors_total,
        }


# ============================================================================
# Connection State
# ============================================================================

class ConnectionState(Enum):
    """Connection state for HLS stream."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


# ============================================================================
# KVS HLS Frame Source
# ============================================================================

class KVSHLSFrameSource:
    """
    Read frames from Kinesis Video Streams via HLS with automatic refresh and reconnection.
    
    Features:
    - Automatic HLS URL refresh before expiry
    - Graceful reconnection with exponential backoff and jitter
    - Comprehensive metrics tracking
    - Thread-safe URL refresh
    - Configurable retry behavior
    
    Example:
        >>> source = KVSHLSFrameSource(
        ...     camera_id="front-entrance",
        ...     stream_name="my-kvs-stream",
        ...     region="us-east-1",
        ...     hls_session_seconds=300
        ... )
        >>> 
        >>> with source:
        ...     for frame, timestamp in source.read_frames():
        ...         # Process frame
        ...         pass
    """
    
    # Default configuration
    DEFAULT_URL_REFRESH_MARGIN = 30  # Refresh 30s before expiry
    DEFAULT_RECONNECT_DELAY = 5  # Initial reconnect delay
    DEFAULT_MAX_RECONNECT_DELAY = 60  # Max backoff delay
    DEFAULT_BACKOFF_MULTIPLIER = 2.0  # Exponential backoff
    DEFAULT_JITTER_RANGE = (0.8, 1.2)  # Jitter 80-120%
    
    def __init__(
        self,
        camera_id: str,
        stream_name: str,
        region: str = "us-east-1",
        hls_session_seconds: int = 300,
        url_refresh_margin: int = DEFAULT_URL_REFRESH_MARGIN,
        reconnect_delay: int = DEFAULT_RECONNECT_DELAY,
        max_reconnect_delay: int = DEFAULT_MAX_RECONNECT_DELAY,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
        max_consecutive_errors: int = 10,
    ):
        """
        Initialize KVS HLS frame source.
        
        Args:
            camera_id: Unique camera identifier (for metrics)
            stream_name: KVS stream name
            region: AWS region
            hls_session_seconds: HLS URL expiry time (60-43200)
            url_refresh_margin: Seconds before expiry to refresh URL
            reconnect_delay: Initial reconnect delay in seconds
            max_reconnect_delay: Maximum reconnect delay (backoff cap)
            backoff_multiplier: Exponential backoff multiplier
            max_consecutive_errors: Max errors before raising exception
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate parameters
        if not camera_id or not camera_id.strip():
            raise ValueError("camera_id cannot be empty")
        if not stream_name or not stream_name.strip():
            raise ValueError("stream_name cannot be empty")
        if not (60 <= hls_session_seconds <= 43200):
            raise ValueError("hls_session_seconds must be between 60 and 43200")
        if url_refresh_margin >= hls_session_seconds:
            raise ValueError("url_refresh_margin must be less than hls_session_seconds")
        
        # Configuration
        self.camera_id = camera_id
        self.stream_name = stream_name
        self.region = region
        self.hls_session_seconds = hls_session_seconds
        self.url_refresh_margin = url_refresh_margin
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_consecutive_errors = max_consecutive_errors
        
        # AWS clients
        self._kvs_client: Optional[boto3.client] = None
        self._kvs_archived_media_client: Optional[boto3.client] = None
        
        # State
        self._hls_url: Optional[str] = None
        self._url_timestamp: Optional[float] = None
        self._capture: Optional[cv2.VideoCapture] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._consecutive_errors = 0
        self._current_backoff = reconnect_delay
        
        # Metrics
        self.metrics = KVSHLSMetrics(camera_id=camera_id)
        
        # Thread safety
        self._lock = threading.RLock()
        self._running = False
        
        logger.info(
            f"Initialized KVS HLS frame source: camera={camera_id}, "
            f"stream={stream_name}, region={region}, "
            f"hls_session={hls_session_seconds}s"
        )
    
    # ========================================================================
    # AWS Client Management
    # ========================================================================
    
    def _get_kvs_client(self) -> boto3.client:
        """Get or create KVS client."""
        if self._kvs_client is None:
            self._kvs_client = boto3.client("kinesisvideo", region_name=self.region)
        return self._kvs_client
    
    def _get_kvs_archived_media_client(self, endpoint: str) -> boto3.client:
        """
        Get or create KVS archived media client.
        
        Args:
            endpoint: Data endpoint URL
            
        Returns:
            KVS archived media client
        """
        # Create new client with endpoint
        return boto3.client(
            "kinesis-video-archived-media",
            endpoint_url=endpoint,
            region_name=self.region
        )
    
    # ========================================================================
    # HLS URL Management
    # ========================================================================
    
    def _get_hls_url(self) -> str:
        """
        Get HLS streaming URL from KVS.
        
        Returns:
            HLS streaming URL
            
        Raises:
            KVSConnectionError: If unable to get URL
        """
        try:
            logger.info(
                f"Getting HLS URL for stream: {self.stream_name} "
                f"(camera: {self.camera_id})"
            )
            
            # Step 1: Get data endpoint
            kvs_client = self._get_kvs_client()
            response = kvs_client.get_data_endpoint(
                StreamName=self.stream_name,
                APIName="GET_HLS_STREAMING_SESSION_URL"
            )
            endpoint = response["DataEndpoint"]
            
            logger.debug(f"Got data endpoint: {endpoint}")
            
            # Step 2: Get HLS streaming session URL
            kvs_archived_media = self._get_kvs_archived_media_client(endpoint)
            response = kvs_archived_media.get_hls_streaming_session_url(
                StreamName=self.stream_name,
                PlaybackMode="LIVE",
                HLSFragmentSelector={
                    "FragmentSelectorType": "SERVER_TIMESTAMP",
                },
                ContainerFormat="FRAGMENTED_MP4",
                DiscontinuityMode="ALWAYS",
                DisplayFragmentTimestamp="ALWAYS",
                Expires=self.hls_session_seconds,
            )
            
            hls_url = response["HLSStreamingSessionURL"]
            
            logger.info(
                f"Got HLS URL for camera {self.camera_id} "
                f"(expires in {self.hls_session_seconds}s)"
            )
            
            # Update metrics
            self.metrics.url_refreshes_total += 1
            prom_metrics.record_kvs_hls_url_refresh(self.camera_id)
            
            return hls_url
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                f"KVS API error for camera {self.camera_id}: "
                f"{error_code} - {error_msg}"
            )
            raise KVSConnectionError(
                f"Failed to get HLS URL: {error_code} - {error_msg}"
            ) from e
            
        except BotoCoreError as e:
            logger.error(f"Boto3 error for camera {self.camera_id}: {e}")
            raise KVSConnectionError(f"Boto3 error: {e}") from e
            
        except Exception as e:
            logger.error(
                f"Unexpected error getting HLS URL for camera {self.camera_id}: {e}",
                exc_info=True
            )
            raise KVSConnectionError(f"Unexpected error: {e}") from e
    
    def _should_refresh_url(self) -> bool:
        """
        Check if HLS URL should be refreshed.
        
        Returns:
            True if URL needs refresh, False otherwise
        """
        if self._url_timestamp is None:
            return True
        
        elapsed = time.time() - self._url_timestamp
        refresh_threshold = self.hls_session_seconds - self.url_refresh_margin
        
        return elapsed >= refresh_threshold
    
    def _refresh_url_if_needed(self) -> bool:
        """
        Refresh HLS URL if needed.
        
        Returns:
            True if refresh succeeded or not needed, False on error
        """
        if not self._should_refresh_url():
            return True
        
        try:
            with self._lock:
                # Double-check after acquiring lock
                if not self._should_refresh_url():
                    return True
                
                logger.info(f"Refreshing HLS URL for camera {self.camera_id}")
                self._hls_url = self._get_hls_url()
                self._url_timestamp = time.time()
                
                # Need to reopen capture with new URL
                self._connection_state = ConnectionState.RECONNECTING
                return True
                
        except KVSConnectionError as e:
            logger.error(f"Failed to refresh URL: {e}")
            return False
    
    # ========================================================================
    # Stream Connection Management
    # ========================================================================
    
    def _calculate_backoff_delay(self) -> float:
        """
        Calculate backoff delay with jitter.
        
        Returns:
            Delay in seconds with jitter applied
        """
        # Apply exponential backoff
        delay = min(self._current_backoff, self.max_reconnect_delay)
        
        # Apply jitter
        jitter_min, jitter_max = self.DEFAULT_JITTER_RANGE
        jitter = random.uniform(jitter_min, jitter_max)
        delay_with_jitter = delay * jitter
        
        # Update current backoff for next time
        self._current_backoff = min(
            self._current_backoff * self.backoff_multiplier,
            self.max_reconnect_delay
        )
        
        return delay_with_jitter
    
    def _reset_backoff(self):
        """Reset backoff to initial delay."""
        self._current_backoff = self.reconnect_delay
        self._consecutive_errors = 0
    
    def _open_stream(self) -> bool:
        """
        Open or reopen the HLS stream.
        
        Returns:
            True if stream opened successfully, False otherwise
        """
        try:
            with self._lock:
                self._connection_state = ConnectionState.CONNECTING
                prom_metrics.update_kvs_hls_connection_state(
                    self.camera_id, 
                    ConnectionState.CONNECTING.value
                )
                
                # Get or refresh HLS URL
                if self._hls_url is None or self._should_refresh_url():
                    self._hls_url = self._get_hls_url()
                    self._url_timestamp = time.time()
                
                # Close existing capture
                if self._capture is not None:
                    try:
                        self._capture.release()
                    except Exception as e:
                        logger.warning(f"Error releasing capture: {e}")
                    self._capture = None
                
                # Open new capture
                logger.info(f"Opening HLS stream for camera {self.camera_id}")
                self._capture = cv2.VideoCapture(self._hls_url)
                
                if not self._capture.isOpened():
                    logger.error(
                        f"Failed to open HLS stream for camera {self.camera_id}"
                    )
                    self._connection_state = ConnectionState.ERROR
                    prom_metrics.update_kvs_hls_connection_state(
                        self.camera_id,
                        ConnectionState.ERROR.value
                    )
                    return False
                
                logger.info(
                    f"Successfully opened HLS stream for camera {self.camera_id}"
                )
                self._connection_state = ConnectionState.CONNECTED
                prom_metrics.update_kvs_hls_connection_state(
                    self.camera_id,
                    ConnectionState.CONNECTED.value
                )
                self._reset_backoff()
                
                return True
                
        except KVSConnectionError as e:
            logger.error(f"KVS connection error: {e}")
            self._connection_state = ConnectionState.ERROR
            prom_metrics.update_kvs_hls_connection_state(
                self.camera_id,
                ConnectionState.ERROR.value
            )
            return False
            
        except Exception as e:
            logger.error(
                f"Unexpected error opening stream for camera {self.camera_id}: {e}",
                exc_info=True
            )
            self._connection_state = ConnectionState.ERROR
            prom_metrics.update_kvs_hls_connection_state(
                self.camera_id,
                ConnectionState.ERROR.value
            )
            return False
    
    def _handle_reconnect(self) -> bool:
        """
        Handle reconnection with backoff and jitter.
        
        Returns:
            True if reconnection succeeded, False otherwise
            
        Raises:
            FrameSourceError: If max consecutive errors reached
        """
        self._consecutive_errors += 1
        
        # Check if we've hit max errors
        if self._consecutive_errors >= self.max_consecutive_errors:
            error_msg = (
                f"Max consecutive errors ({self.max_consecutive_errors}) reached "
                f"for camera {self.camera_id}"
            )
            logger.error(error_msg)
            raise FrameSourceError(error_msg)
        
        # Calculate backoff delay
        delay = self._calculate_backoff_delay()
        
        logger.warning(
            f"Reconnecting camera {self.camera_id} in {delay:.2f}s "
            f"(attempt {self._consecutive_errors}/{self.max_consecutive_errors})"
        )
        
        time.sleep(delay)
        
        # Update metrics
        self.metrics.reconnects_total += 1
        prom_metrics.record_kvs_hls_reconnect(self.camera_id)
        
        # Attempt reconnection
        return self._open_stream()
    
    # ========================================================================
    # Frame Reading
    # ========================================================================
    
    def read_frame(self) -> Optional[Tuple[np.ndarray, float]]:
        """
        Read next frame from stream.
        
        Returns:
            Tuple of (frame, timestamp) if successful, None otherwise.
            Frame is a numpy array in BGR format.
            Timestamp is Unix timestamp (seconds since epoch).
            
        Raises:
            FrameSourceError: If fatal error occurs (max retries exceeded)
        """
        # Ensure stream is open
        if self._connection_state not in (ConnectionState.CONNECTED, ConnectionState.RECONNECTING):
            if not self._open_stream():
                if not self._handle_reconnect():
                    return None
        
        # Refresh URL if needed
        if not self._refresh_url_if_needed():
            if not self._handle_reconnect():
                return None
        
        # Read frame
        try:
            with self._lock:
                if self._capture is None or not self._capture.isOpened():
                    logger.warning(f"Capture not open for camera {self.camera_id}")
                    if not self._handle_reconnect():
                        return None
                    return None
                
                ret, frame = self._capture.read()
            
            if not ret or frame is None:
                logger.warning(
                    f"Failed to read frame from camera {self.camera_id}"
                )
                self.metrics.read_errors_total += 1
                prom_metrics.record_kvs_hls_read_error(self.camera_id)
                
                # Attempt reconnection
                if not self._handle_reconnect():
                    return None
                return None
            
            # Successful read
            timestamp = time.time()
            
            # Update metrics
            self.metrics.frames_total += 1
            self.metrics.last_frame_timestamp = timestamp
            prom_metrics.record_kvs_hls_frame(self.camera_id, timestamp)
            
            # Reset error count on success
            self._reset_backoff()
            
            return frame, timestamp
            
        except Exception as e:
            logger.error(
                f"Error reading frame from camera {self.camera_id}: {e}",
                exc_info=True
            )
            self.metrics.read_errors_total += 1
            prom_metrics.record_kvs_hls_read_error(self.camera_id)
            
            if not self._handle_reconnect():
                return None
            return None
    
    def read_frames(self) -> Iterator[Tuple[np.ndarray, float]]:
        """
        Generator that yields frames continuously.
        
        Yields:
            Tuple of (frame, timestamp)
            
        Raises:
            FrameSourceError: If fatal error occurs
        """
        self._running = True
        
        try:
            while self._running:
                frame_data = self.read_frame()
                if frame_data is not None:
                    yield frame_data
        finally:
            self._running = False
    
    # ========================================================================
    # Lifecycle Management
    # ========================================================================
    
    def start(self) -> bool:
        """
        Start the frame source (open initial connection).
        
        Returns:
            True if started successfully, False otherwise
        """
        logger.info(f"Starting frame source for camera {self.camera_id}")
        self._running = True
        return self._open_stream()
    
    def stop(self):
        """Stop the frame source."""
        logger.info(f"Stopping frame source for camera {self.camera_id}")
        self._running = False
    
    def release(self):
        """Release all resources."""
        logger.info(f"Releasing frame source for camera {self.camera_id}")
        
        self._running = False
        
        with self._lock:
            if self._capture is not None:
                try:
                    self._capture.release()
                except Exception as e:
                    logger.warning(f"Error releasing capture: {e}")
                self._capture = None
            
            self._connection_state = ConnectionState.DISCONNECTED
            prom_metrics.update_kvs_hls_connection_state(
                self.camera_id,
                ConnectionState.DISCONNECTED.value
            )
        
        logger.info(
            f"Released frame source for camera {self.camera_id}. "
            f"Final metrics: {self.metrics.to_dict()}"
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
    
    # ========================================================================
    # Metrics & Status
    # ========================================================================
    
    def get_metrics(self) -> dict:
        """
        Get current metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics.to_dict()
    
    def get_connection_state(self) -> str:
        """
        Get current connection state.
        
        Returns:
            Connection state as string
        """
        return self._connection_state.value
    
    def is_healthy(self) -> bool:
        """
        Check if frame source is healthy.
        
        Returns:
            True if connected and reading frames, False otherwise
        """
        return (
            self._connection_state == ConnectionState.CONNECTED and
            self._consecutive_errors < self.max_consecutive_errors
        )
