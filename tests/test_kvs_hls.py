"""
Unit tests for KVS HLS frame source.
"""

import time
import unittest
from unittest.mock import Mock, MagicMock, patch, call
import numpy as np
import cv2

from src.kvs_infer.frame_source.kvs_hls import (
    KVSHLSFrameSource,
    FrameSourceError,
    KVSConnectionError,
    HLSStreamError,
    ConnectionState,
    KVSHLSMetrics,
)


class TestKVSHLSMetrics(unittest.TestCase):
    """Test KVSHLSMetrics dataclass."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization with defaults."""
        metrics = KVSHLSMetrics(camera_id="test-cam")
        
        self.assertEqual(metrics.camera_id, "test-cam")
        self.assertEqual(metrics.reconnects_total, 0)
        self.assertEqual(metrics.frames_total, 0)
        self.assertIsNone(metrics.last_frame_timestamp)
        self.assertEqual(metrics.url_refreshes_total, 0)
        self.assertEqual(metrics.read_errors_total, 0)
    
    def test_metrics_to_dict(self):
        """Test metrics conversion to dictionary."""
        metrics = KVSHLSMetrics(
            camera_id="test-cam",
            reconnects_total=5,
            frames_total=1000,
            last_frame_timestamp=1234567890.0,
            url_refreshes_total=10,
            read_errors_total=2,
        )
        
        result = metrics.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["camera_id"], "test-cam")
        self.assertEqual(result["reconnects_total"], 5)
        self.assertEqual(result["frames_total"], 1000)
        self.assertEqual(result["last_frame_timestamp"], 1234567890.0)
        self.assertEqual(result["url_refreshes_total"], 10)
        self.assertEqual(result["read_errors_total"], 2)


class TestKVSHLSFrameSourceInit(unittest.TestCase):
    """Test KVSHLSFrameSource initialization."""
    
    def test_valid_initialization(self):
        """Test valid initialization parameters."""
        source = KVSHLSFrameSource(
            camera_id="test-cam",
            stream_name="test-stream",
            region="us-west-2",
            hls_session_seconds=600,
        )
        
        self.assertEqual(source.camera_id, "test-cam")
        self.assertEqual(source.stream_name, "test-stream")
        self.assertEqual(source.region, "us-west-2")
        self.assertEqual(source.hls_session_seconds, 600)
        self.assertEqual(source.metrics.camera_id, "test-cam")
    
    def test_invalid_camera_id(self):
        """Test initialization with empty camera_id."""
        with self.assertRaises(ValueError) as ctx:
            KVSHLSFrameSource(
                camera_id="",
                stream_name="test-stream",
            )
        self.assertIn("camera_id", str(ctx.exception))
    
    def test_invalid_stream_name(self):
        """Test initialization with empty stream_name."""
        with self.assertRaises(ValueError) as ctx:
            KVSHLSFrameSource(
                camera_id="test-cam",
                stream_name="",
            )
        self.assertIn("stream_name", str(ctx.exception))
    
    def test_invalid_hls_session_seconds(self):
        """Test initialization with invalid hls_session_seconds."""
        # Too low
        with self.assertRaises(ValueError) as ctx:
            KVSHLSFrameSource(
                camera_id="test-cam",
                stream_name="test-stream",
                hls_session_seconds=30,
            )
        self.assertIn("hls_session_seconds", str(ctx.exception))
        
        # Too high
        with self.assertRaises(ValueError) as ctx:
            KVSHLSFrameSource(
                camera_id="test-cam",
                stream_name="test-stream",
                hls_session_seconds=50000,
            )
        self.assertIn("hls_session_seconds", str(ctx.exception))
    
    def test_invalid_url_refresh_margin(self):
        """Test initialization with invalid url_refresh_margin."""
        with self.assertRaises(ValueError) as ctx:
            KVSHLSFrameSource(
                camera_id="test-cam",
                stream_name="test-stream",
                hls_session_seconds=300,
                url_refresh_margin=400,  # Greater than hls_session_seconds
            )
        self.assertIn("url_refresh_margin", str(ctx.exception))


class TestKVSHLSFrameSourceURLManagement(unittest.TestCase):
    """Test URL management methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.source = KVSHLSFrameSource(
            camera_id="test-cam",
            stream_name="test-stream",
            region="us-east-1",
            hls_session_seconds=300,
            url_refresh_margin=30,
        )
    
    @patch("boto3.client")
    def test_get_hls_url_success(self, mock_boto_client):
        """Test successful HLS URL retrieval."""
        # Mock KVS client
        mock_kvs = MagicMock()
        mock_kvs.get_data_endpoint.return_value = {
            "DataEndpoint": "https://test-endpoint.amazonaws.com"
        }
        
        # Mock KVS archived media client
        mock_archived = MagicMock()
        mock_archived.get_hls_streaming_session_url.return_value = {
            "HLSStreamingSessionURL": "https://test-hls-url.m3u8"
        }
        
        # Configure boto3.client to return appropriate mocks
        def client_factory(service, **kwargs):
            if service == "kinesisvideo":
                return mock_kvs
            elif service == "kinesis-video-archived-media":
                return mock_archived
            raise ValueError(f"Unexpected service: {service}")
        
        mock_boto_client.side_effect = client_factory
        
        # Call method
        url = self.source._get_hls_url()
        
        # Assertions
        self.assertEqual(url, "https://test-hls-url.m3u8")
        self.assertEqual(self.source.metrics.url_refreshes_total, 1)
        
        # Verify API calls
        mock_kvs.get_data_endpoint.assert_called_once_with(
            StreamName="test-stream",
            APIName="GET_HLS_STREAMING_SESSION_URL"
        )
        mock_archived.get_hls_streaming_session_url.assert_called_once()
    
    @patch("boto3.client")
    def test_get_hls_url_client_error(self, mock_boto_client):
        """Test HLS URL retrieval with ClientError."""
        from botocore.exceptions import ClientError
        
        mock_kvs = MagicMock()
        mock_kvs.get_data_endpoint.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Stream not found"}},
            "GetDataEndpoint"
        )
        
        mock_boto_client.return_value = mock_kvs
        
        with self.assertRaises(KVSConnectionError) as ctx:
            self.source._get_hls_url()
        
        self.assertIn("ResourceNotFoundException", str(ctx.exception))
    
    def test_should_refresh_url_no_timestamp(self):
        """Test should_refresh_url when no URL exists."""
        self.source._url_timestamp = None
        self.assertTrue(self.source._should_refresh_url())
    
    def test_should_refresh_url_expired(self):
        """Test should_refresh_url when URL is expired."""
        # Set timestamp 280 seconds ago (beyond 270s threshold)
        self.source._url_timestamp = time.time() - 280
        self.assertTrue(self.source._should_refresh_url())
    
    def test_should_refresh_url_valid(self):
        """Test should_refresh_url when URL is still valid."""
        # Set timestamp 100 seconds ago (within 270s threshold)
        self.source._url_timestamp = time.time() - 100
        self.assertFalse(self.source._should_refresh_url())


class TestKVSHLSFrameSourceStreamManagement(unittest.TestCase):
    """Test stream connection management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.source = KVSHLSFrameSource(
            camera_id="test-cam",
            stream_name="test-stream",
            region="us-east-1",
            hls_session_seconds=300,
            reconnect_delay=1,
            max_reconnect_delay=5,
        )
    
    def test_calculate_backoff_delay(self):
        """Test exponential backoff calculation."""
        # First call should be ~1s (with jitter)
        delay1 = self.source._calculate_backoff_delay()
        self.assertGreater(delay1, 0.5)
        self.assertLess(delay1, 2.0)
        
        # Second call should be ~2s (with jitter)
        delay2 = self.source._calculate_backoff_delay()
        self.assertGreater(delay2, 1.0)
        self.assertLess(delay2, 4.0)
        
        # Should increase exponentially
        self.assertGreater(delay2, delay1)
    
    def test_calculate_backoff_delay_capped(self):
        """Test backoff delay is capped at max_reconnect_delay."""
        # Set current backoff to max
        self.source._current_backoff = self.source.max_reconnect_delay * 10
        
        delay = self.source._calculate_backoff_delay()
        
        # Should be capped at max (with jitter applied)
        self.assertLessEqual(delay, self.source.max_reconnect_delay * 1.2)
    
    def test_reset_backoff(self):
        """Test backoff reset."""
        self.source._current_backoff = 100
        self.source._consecutive_errors = 5
        
        self.source._reset_backoff()
        
        self.assertEqual(self.source._current_backoff, self.source.reconnect_delay)
        self.assertEqual(self.source._consecutive_errors, 0)
    
    @patch("cv2.VideoCapture")
    @patch.object(KVSHLSFrameSource, "_get_hls_url")
    def test_open_stream_success(self, mock_get_url, mock_video_capture):
        """Test successful stream opening."""
        mock_get_url.return_value = "https://test-url.m3u8"
        
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_video_capture.return_value = mock_capture
        
        result = self.source._open_stream()
        
        self.assertTrue(result)
        self.assertEqual(self.source._connection_state, ConnectionState.CONNECTED)
        self.assertIsNotNone(self.source._hls_url)
        self.assertIsNotNone(self.source._url_timestamp)
        mock_video_capture.assert_called_once_with("https://test-url.m3u8")
    
    @patch("cv2.VideoCapture")
    @patch.object(KVSHLSFrameSource, "_get_hls_url")
    def test_open_stream_failure(self, mock_get_url, mock_video_capture):
        """Test failed stream opening."""
        mock_get_url.return_value = "https://test-url.m3u8"
        
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = False
        mock_video_capture.return_value = mock_capture
        
        result = self.source._open_stream()
        
        self.assertFalse(result)
        self.assertEqual(self.source._connection_state, ConnectionState.ERROR)


class TestKVSHLSFrameSourceReading(unittest.TestCase):
    """Test frame reading functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.source = KVSHLSFrameSource(
            camera_id="test-cam",
            stream_name="test-stream",
            region="us-east-1",
            hls_session_seconds=300,
            reconnect_delay=0.1,  # Short delay for tests
            max_consecutive_errors=3,
        )
    
    @patch.object(KVSHLSFrameSource, "_open_stream")
    @patch.object(KVSHLSFrameSource, "_refresh_url_if_needed")
    def test_read_frame_success(self, mock_refresh, mock_open):
        """Test successful frame reading."""
        mock_open.return_value = True
        mock_refresh.return_value = True
        
        # Create mock capture
        mock_capture = MagicMock()
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_capture.read.return_value = (True, test_frame)
        mock_capture.isOpened.return_value = True
        
        self.source._capture = mock_capture
        self.source._connection_state = ConnectionState.CONNECTED
        
        # Read frame
        result = self.source.read_frame()
        
        # Assertions
        self.assertIsNotNone(result)
        frame, timestamp = result
        self.assertIsInstance(frame, np.ndarray)
        self.assertEqual(frame.shape, (480, 640, 3))
        self.assertIsInstance(timestamp, float)
        self.assertEqual(self.source.metrics.frames_total, 1)
        self.assertIsNotNone(self.source.metrics.last_frame_timestamp)
    
    @patch.object(KVSHLSFrameSource, "_open_stream")
    @patch.object(KVSHLSFrameSource, "_refresh_url_if_needed")
    @patch.object(KVSHLSFrameSource, "_handle_reconnect")
    def test_read_frame_failure(self, mock_reconnect, mock_refresh, mock_open):
        """Test frame reading failure."""
        mock_open.return_value = True
        mock_refresh.return_value = True
        mock_reconnect.return_value = False
        
        # Mock capture that returns no frame
        mock_capture = MagicMock()
        mock_capture.read.return_value = (False, None)
        mock_capture.isOpened.return_value = True
        
        self.source._capture = mock_capture
        self.source._connection_state = ConnectionState.CONNECTED
        
        # Read frame
        result = self.source.read_frame()
        
        # Should return None on failure
        self.assertIsNone(result)
        self.assertEqual(self.source.metrics.read_errors_total, 1)
        mock_reconnect.assert_called_once()
    
    @patch.object(KVSHLSFrameSource, "_open_stream")
    @patch.object(KVSHLSFrameSource, "_handle_reconnect")
    @patch("time.sleep")
    def test_read_frame_max_errors(self, mock_sleep, mock_reconnect, mock_open):
        """Test frame reading reaches max consecutive errors."""
        mock_open.return_value = True
        
        # Mock handle_reconnect to raise after max errors
        def raise_on_max_errors():
            self.source._consecutive_errors += 1
            if self.source._consecutive_errors >= self.source.max_consecutive_errors:
                raise FrameSourceError("Max errors reached")
            return False
        
        mock_reconnect.side_effect = raise_on_max_errors
        
        # Mock capture that always fails
        mock_capture = MagicMock()
        mock_capture.read.return_value = (False, None)
        mock_capture.isOpened.return_value = True
        
        self.source._capture = mock_capture
        self.source._connection_state = ConnectionState.CONNECTED
        
        # Read frames until max errors
        with self.assertRaises(FrameSourceError):
            for _ in range(self.source.max_consecutive_errors + 1):
                result = self.source.read_frame()


class TestKVSHLSFrameSourceLifecycle(unittest.TestCase):
    """Test lifecycle management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.source = KVSHLSFrameSource(
            camera_id="test-cam",
            stream_name="test-stream",
            region="us-east-1",
        )
    
    @patch.object(KVSHLSFrameSource, "_open_stream")
    def test_start(self, mock_open):
        """Test start method."""
        mock_open.return_value = True
        
        result = self.source.start()
        
        self.assertTrue(result)
        self.assertTrue(self.source._running)
        mock_open.assert_called_once()
    
    def test_stop(self):
        """Test stop method."""
        self.source._running = True
        
        self.source.stop()
        
        self.assertFalse(self.source._running)
    
    def test_release(self):
        """Test release method."""
        mock_capture = MagicMock()
        self.source._capture = mock_capture
        self.source._running = True
        
        self.source.release()
        
        self.assertFalse(self.source._running)
        mock_capture.release.assert_called_once()
        self.assertIsNone(self.source._capture)
        self.assertEqual(self.source._connection_state, ConnectionState.DISCONNECTED)
    
    @patch.object(KVSHLSFrameSource, "start")
    @patch.object(KVSHLSFrameSource, "release")
    def test_context_manager(self, mock_release, mock_start):
        """Test context manager protocol."""
        with self.source as src:
            self.assertIs(src, self.source)
            mock_start.assert_called_once()
        
        mock_release.assert_called_once()


class TestKVSHLSFrameSourceMetrics(unittest.TestCase):
    """Test metrics and status methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.source = KVSHLSFrameSource(
            camera_id="test-cam",
            stream_name="test-stream",
            region="us-east-1",
        )
    
    def test_get_metrics(self):
        """Test get_metrics method."""
        self.source.metrics.frames_total = 100
        self.source.metrics.reconnects_total = 5
        
        metrics = self.source.get_metrics()
        
        self.assertIsInstance(metrics, dict)
        self.assertEqual(metrics["camera_id"], "test-cam")
        self.assertEqual(metrics["frames_total"], 100)
        self.assertEqual(metrics["reconnects_total"], 5)
    
    def test_get_connection_state(self):
        """Test get_connection_state method."""
        self.source._connection_state = ConnectionState.CONNECTED
        
        state = self.source.get_connection_state()
        
        self.assertEqual(state, "connected")
    
    def test_is_healthy(self):
        """Test is_healthy method."""
        # Healthy state
        self.source._connection_state = ConnectionState.CONNECTED
        self.source._consecutive_errors = 0
        self.assertTrue(self.source.is_healthy())
        
        # Not connected
        self.source._connection_state = ConnectionState.ERROR
        self.assertFalse(self.source.is_healthy())
        
        # Too many errors
        self.source._connection_state = ConnectionState.CONNECTED
        self.source._consecutive_errors = 100
        self.assertFalse(self.source.is_healthy())


if __name__ == "__main__":
    unittest.main()
