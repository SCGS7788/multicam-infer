"""
Prometheus metrics endpoint for monitoring.
"""

import logging
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, start_http_server, Info
import threading


logger = logging.getLogger(__name__)


# Metrics
FRAMES_PROCESSED = Counter(
    "kvs_infer_frames_processed_total",
    "Total number of frames processed",
    ["camera_name", "status"]  # status: success/error
)

DETECTIONS_TOTAL = Counter(
    "kvs_infer_detections_total",
    "Total number of detections",
    ["camera_name", "detector_type", "class_name"]
)

INFERENCE_TIME = Histogram(
    "kvs_infer_inference_seconds",
    "Inference time in seconds",
    ["camera_name", "detector_type"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

FRAME_PROCESSING_TIME = Histogram(
    "kvs_infer_frame_processing_seconds",
    "Total frame processing time in seconds",
    ["camera_name"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

EVENTS_PUBLISHED = Counter(
    "kvs_infer_events_published_total",
    "Total number of events published",
    ["camera_name", "publisher_type", "status"]  # status: success/error
)

SNAPSHOTS_UPLOADED = Counter(
    "kvs_infer_snapshots_uploaded_total",
    "Total number of snapshots uploaded to S3",
    ["camera_name", "image_type", "status"]  # image_type: snapshot/crop
)

STREAM_ERRORS = Counter(
    "kvs_infer_stream_errors_total",
    "Total number of stream errors",
    ["camera_name", "error_type"]
)

# KVS HLS-specific metrics
KVS_HLS_RECONNECTS = Counter(
    "kvs_hls_reconnects_total",
    "Total number of KVS HLS reconnections",
    ["camera_id"]
)

KVS_HLS_FRAMES = Counter(
    "kvs_hls_frames_total",
    "Total number of frames read from KVS HLS",
    ["camera_id"]
)

KVS_HLS_LAST_FRAME_TS = Gauge(
    "kvs_hls_last_frame_timestamp",
    "Timestamp of last frame received from KVS HLS",
    ["camera_id"]
)

KVS_HLS_URL_REFRESHES = Counter(
    "kvs_hls_url_refreshes_total",
    "Total number of HLS URL refreshes",
    ["camera_id"]
)

KVS_HLS_READ_ERRORS = Counter(
    "kvs_hls_read_errors_total",
    "Total number of frame read errors",
    ["camera_id"]
)

KVS_HLS_CONNECTION_STATE = Gauge(
    "kvs_hls_connection_state",
    "Current connection state (0=disconnected, 1=connecting, 2=connected, 3=reconnecting, 4=error)",
    ["camera_id"]
)

ACTIVE_CAMERAS = Gauge(
    "kvs_infer_active_cameras",
    "Number of active camera workers"
)

APP_INFO = Info(
    "kvs_infer_app",
    "Application information"
)


def start_metrics_server(
    port: int = 9090,
    host: str = "0.0.0.0",
):
    """
    Start Prometheus metrics HTTP server.
    
    Args:
        port: Port to listen on
        host: Host to bind to
    """
    def _start_server():
        try:
            logger.info(f"Starting metrics server on {host}:{port}")
            start_http_server(port=port, addr=host)
            logger.info(f"Metrics server started at http://{host}:{port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}", exc_info=True)
    
    # Start in background thread
    thread = threading.Thread(target=_start_server, daemon=True)
    thread.start()


def record_frame_processed(camera_name: str, success: bool = True):
    """Record a processed frame."""
    status = "success" if success else "error"
    FRAMES_PROCESSED.labels(camera_name=camera_name, status=status).inc()


def record_detection(camera_name: str, detector_type: str, class_name: str):
    """Record a detection."""
    DETECTIONS_TOTAL.labels(
        camera_name=camera_name,
        detector_type=detector_type,
        class_name=class_name
    ).inc()


def record_inference_time(camera_name: str, detector_type: str, duration_seconds: float):
    """Record inference time."""
    INFERENCE_TIME.labels(
        camera_name=camera_name,
        detector_type=detector_type
    ).observe(duration_seconds)


def record_frame_processing_time(camera_name: str, duration_seconds: float):
    """Record total frame processing time."""
    FRAME_PROCESSING_TIME.labels(camera_name=camera_name).observe(duration_seconds)


def record_kvs_hls_frame(camera_id: str, timestamp: float):
    """Record a frame read from KVS HLS."""
    KVS_HLS_FRAMES.labels(camera_id=camera_id).inc()
    KVS_HLS_LAST_FRAME_TS.labels(camera_id=camera_id).set(timestamp)


def record_kvs_hls_reconnect(camera_id: str):
    """Record a KVS HLS reconnection."""
    KVS_HLS_RECONNECTS.labels(camera_id=camera_id).inc()


def record_kvs_hls_url_refresh(camera_id: str):
    """Record a KVS HLS URL refresh."""
    KVS_HLS_URL_REFRESHES.labels(camera_id=camera_id).inc()


def record_kvs_hls_read_error(camera_id: str):
    """Record a KVS HLS frame read error."""
    KVS_HLS_READ_ERRORS.labels(camera_id=camera_id).inc()


def update_kvs_hls_connection_state(camera_id: str, state: str):
    """
    Update KVS HLS connection state.
    
    Args:
        camera_id: Camera identifier
        state: Connection state (disconnected, connecting, connected, reconnecting, error)
    """
    state_map = {
        "disconnected": 0,
        "connecting": 1,
        "connected": 2,
        "reconnecting": 3,
        "error": 4,
    }
    state_value = state_map.get(state, 4)
    KVS_HLS_CONNECTION_STATE.labels(camera_id=camera_id).set(state_value)


def record_event_published(camera_name: str, publisher_type: str, success: bool = True):
    """Record an event publication."""
    status = "success" if success else "error"
    EVENTS_PUBLISHED.labels(
        camera_name=camera_name,
        publisher_type=publisher_type,
        status=status
    ).inc()


def record_snapshot_uploaded(camera_name: str, image_type: str, success: bool = True):
    """Record a snapshot upload."""
    status = "success" if success else "error"
    SNAPSHOTS_UPLOADED.labels(
        camera_name=camera_name,
        image_type=image_type,
        status=status
    ).inc()


def record_stream_error(camera_name: str, error_type: str):
    """Record a stream error."""
    STREAM_ERRORS.labels(camera_name=camera_name, error_type=error_type).inc()


def set_active_cameras(count: int):
    """Set the number of active cameras."""
    ACTIVE_CAMERAS.set(count)


def set_app_info(version: str, device: str):
    """Set application information."""
    APP_INFO.info({
        "version": version,
        "device": device,
    })
