#!/usr/bin/env python3
"""
Main application entry point for multi-camera inference system.

Features:
- CLI with config file and HTTP server options
- Multi-camera worker management with separate threads
- Prometheus metrics endpoint
- FastAPI health check endpoint
- Graceful shutdown handling (SIGTERM/SIGINT)
- JSON logging to stdout
"""

import argparse
import logging
import os
import signal
import sys
import time
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

import uvicorn
from fastapi import FastAPI, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)
import boto3

from kvs_infer.config import load_config
from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource
from kvs_infer.detectors import DetectorRegistry
from kvs_infer.publisher import KDSClient, S3Snapshot, DDBWriter


# ============================================================================
# Logging Configuration
# ============================================================================

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "camera_id"):
            log_obj["camera_id"] = record.camera_id
        if hasattr(record, "event_type"):
            log_obj["event_type"] = record.event_type
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = record.latency_ms
        
        return json.dumps(log_obj)


def setup_logging():
    """Configure JSON logging to stdout."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger


logger = setup_logging()


# ============================================================================
# Prometheus Metrics
# ============================================================================

# Create custom registry to avoid conflicts
registry = CollectorRegistry()

# Frame processing metrics
frames_total = Counter(
    "infer_frames_total",
    "Total frames processed",
    ["camera_id"],
    registry=registry
)

events_total = Counter(
    "infer_events_total",
    "Total detection events",
    ["camera_id", "type"],
    registry=registry
)

latency_histogram = Histogram(
    "infer_latency_ms",
    "Inference latency in milliseconds",
    ["camera_id"],
    buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000],
    registry=registry
)

# Publisher metrics
publisher_failures = Counter(
    "publisher_failures_total",
    "Total publisher failures",
    ["sink"],
    registry=registry
)

# Worker health metrics
worker_alive = Gauge(
    "worker_alive",
    "Worker thread alive status (1=alive, 0=dead)",
    ["camera_id"],
    registry=registry
)


# ============================================================================
# FastAPI Application
# ============================================================================

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="KVS Infer", description="Multi-camera inference service")

# Mount static files
try:
    from pathlib import Path
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Web UI Dashboard."""
    try:
        static_dir = Path(__file__).parent / "static"
        dashboard_file = static_dir / "dashboard.html"
        if dashboard_file.exists():
            return FileResponse(dashboard_file)
        else:
            return HTMLResponse("""
                <html>
                    <head><title>KVS Infer</title></head>
                    <body style="font-family: Arial; padding: 40px; text-align: center;">
                        <h1>🎥 KVS Inference System</h1>
                        <p>Web UI not available. Dashboard file not found.</p>
                        <p><a href="/healthz">Health Check</a> | <a href="/metrics">Metrics</a></p>
                    </body>
                </html>
            """)
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>Error loading dashboard</h1><p>{str(e)}</p></body></html>")


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "kvs-infer"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# Camera Worker
# ============================================================================

class CameraWorker:
    """
    Worker thread for processing frames from a single camera.
    
    Responsibilities:
    - Read frames from KVS HLS source
    - Run detector pipeline
    - Publish events to KDS/S3/DDB
    - Track metrics
    - Handle errors and reconnection
    """
    
    def __init__(
        self,
        camera_id: str,
        camera_config: Dict[str, Any],
        global_config: Dict[str, Any],
        publishers: Dict[str, Any]
    ):
        """
        Initialize camera worker.
        
        Args:
            camera_id: Camera identifier
            camera_config: Camera-specific configuration
            global_config: Global configuration
            publishers: Dict with kds, s3, ddb publishers
        """
        self.camera_id = camera_id
        self.camera_config = camera_config
        self.global_config = global_config
        self.publishers = publishers
        
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Frame source
        self.frame_source: Optional[KVSHLSFrameSource] = None
        
        # Detector pipeline
        self.detectors: List[Any] = []
        
        # FPS throttling
        self.fps_target = camera_config.get("fps_target")
        self.frame_interval = 1.0 / self.fps_target if self.fps_target else 0
        
        logger.info(
            f"Camera worker initialized: {camera_id}",
            extra={"camera_id": camera_id}
        )
    
    def start(self):
        """Start worker thread."""
        if self.running:
            logger.warning(
                f"Worker already running: {self.camera_id}",
                extra={"camera_id": self.camera_id}
            )
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._run,
            name=f"worker-{self.camera_id}",
            daemon=True
        )
        self.thread.start()
        
        # Set worker alive metric
        worker_alive.labels(camera_id=self.camera_id).set(1)
        
        logger.info(
            f"Worker started: {self.camera_id}",
            extra={"camera_id": self.camera_id}
        )
    
    def stop(self):
        """Stop worker thread."""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        # Cleanup frame source
        if self.frame_source:
            self.frame_source.stop()
            self.frame_source = None
        
        # Set worker alive metric
        worker_alive.labels(camera_id=self.camera_id).set(0)
        
        logger.info(
            f"Worker stopped: {self.camera_id}",
            extra={"camera_id": self.camera_id}
        )
    
    def _initialize_frame_source(self):
        """Initialize KVS HLS frame source."""
        # Support both config formats:
        # 1. kvs_stream_name at camera level (current format)
        # 2. kvs.stream_name nested (old format)
        kvs_config = self.camera_config.get("kvs", {})
        stream_name = (
            self.camera_config.get("kvs_stream_name") or  # New format
            kvs_config.get("stream_name")  # Old format
        )
        
        self.frame_source = KVSHLSFrameSource(
            camera_id=self.camera_id,
            stream_name=stream_name,
            region=kvs_config.get("region", "us-east-1"),
            hls_session_seconds=kvs_config.get("hls_session_seconds", 300),
            reconnect_delay=kvs_config.get("reconnect_delay_sec", 5)
        )
        
        self.frame_source.start()
        
        logger.info(
            f"Frame source initialized: {self.camera_id}",
            extra={
                "camera_id": self.camera_id,
                "stream_name": stream_name
            }
        )
    
    def _initialize_detectors(self):
        """Initialize detector pipeline from config."""
        detector_configs = self.camera_config.get("detectors", [])
        
        for det_config in detector_configs:
            detector_type = det_config.get("type")
            detector_params = det_config.get("params", {})
            
            # Check if detector is registered
            if not DetectorRegistry.is_registered(detector_type):
                logger.error(
                    f"Detector not found: {detector_type}",
                    extra={
                        "camera_id": self.camera_id,
                        "detector_type": detector_type
                    }
                )
                continue
            
            # Create detector instance using registry
            detector = DetectorRegistry.create(detector_type, detector_params)
            self.detectors.append(detector)
            
            logger.info(
                f"Detector initialized: {detector_type}",
                extra={
                    "camera_id": self.camera_id,
                    "detector_type": detector_type
                }
            )
        
        logger.info(
            f"Detector pipeline ready: {len(self.detectors)} detectors",
            extra={
                "camera_id": self.camera_id,
                "detector_count": len(self.detectors)
            }
        )
    
    def _run_detectors(self, frame, ts_ms: int) -> List[Dict[str, Any]]:
        """
        Run detector pipeline on frame.
        
        Args:
            frame: CV2 frame
            ts_ms: Timestamp in milliseconds
        
        Returns:
            List of detection events
        """
        all_events = []
        
        for detector in self.detectors:
            try:
                events = detector.detect(frame, ts_ms)
                all_events.extend(events)
            except Exception as e:
                logger.error(
                    f"Detector error: {e}",
                    extra={
                        "camera_id": self.camera_id,
                        "detector_type": type(detector).__name__
                    },
                    exc_info=True
                )
        
        return all_events
    
    def _publish_events(self, events: List[Dict[str, Any]]):
        """
        Publish events to configured sinks.
        
        Args:
            events: List of detection events
        """
        if not events:
            return
        
        # Publish to KDS
        if self.publishers.get("kds"):
            try:
                for event in events:
                    event_envelope = {
                        "camera_id": self.camera_id,
                        "payload": event
                    }
                    self.publishers["kds"].put_event(
                        event_envelope,
                        partition_key=self.camera_id
                    )
            except Exception as e:
                logger.error(
                    f"KDS publish error: {e}",
                    extra={"camera_id": self.camera_id},
                    exc_info=True
                )
                publisher_failures.labels(sink="kds").inc()
        
        # Publish to DDB (optional)
        if self.publishers.get("ddb"):
            try:
                for event in events:
                    # Create full envelope (KDS client does this, but we need it for DDB)
                    event_envelope = {
                        "camera_id": self.camera_id,
                        "payload": event
                    }
                    # Use KDS client to create proper envelope
                    full_envelope = self.publishers["kds"]._create_event_envelope(
                        event_envelope,
                        "kvs-infer/1.0"
                    )
                    self.publishers["ddb"].put_event(full_envelope)
            except Exception as e:
                logger.error(
                    f"DDB publish error: {e}",
                    extra={"camera_id": self.camera_id},
                    exc_info=True
                )
                publisher_failures.labels(sink="ddb").inc()
    
    def _save_snapshots(self, frame, events: List[Dict[str, Any]], ts_ms: int):
        """
        Save frame snapshots to S3.
        
        Args:
            frame: CV2 frame
            events: Detection events
            ts_ms: Timestamp in milliseconds
        """
        if not self.publishers.get("s3"):
            return
        
        # Only save snapshots if there are events
        if not events:
            return
        
        # Check if snapshots are enabled
        snapshot_config = self.global_config.get("publishers", {}).get("s3", {})
        if not snapshot_config.get("save_snapshots", True):
            return
        
        try:
            # Convert events to detection format for bbox drawing
            detections = []
            for event in events:
                detections.append({
                    "bbox": event["bbox"],
                    "label": event["label"],
                    "conf": event["conf"]
                })
            
            # Save with bounding boxes
            self.publishers["s3"].save_with_bbox(
                frame=frame,
                camera_id=self.camera_id,
                ts_ms=ts_ms,
                detections=detections,
                draw_labels=True
            )
        except Exception as e:
            logger.error(
                f"S3 snapshot error: {e}",
                extra={"camera_id": self.camera_id},
                exc_info=True
            )
            publisher_failures.labels(sink="s3").inc()
    
    def _run(self):
        """Main worker loop."""
        logger.info(
            f"Worker loop starting: {self.camera_id}",
            extra={"camera_id": self.camera_id}
        )
        
        try:
            # Initialize frame source
            self._initialize_frame_source()
            
            # Initialize detectors
            self._initialize_detectors()
            
            # Main processing loop
            last_frame_time = 0
            
            while self.running:
                try:
                    # FPS throttling
                    if self.fps_target:
                        current_time = time.time()
                        elapsed = current_time - last_frame_time
                        
                        if elapsed < self.frame_interval:
                            time.sleep(self.frame_interval - elapsed)
                        
                        last_frame_time = time.time()
                    
                    # Read frame
                    result = self.frame_source.read_frame()
                    
                    # Handle both None and tuple returns
                    if result is None or not isinstance(result, tuple):
                        # No frame available, sleep briefly
                        time.sleep(0.1)
                        continue
                    
                    frame, ts_ms = result
                    
                    if frame is None:
                        # No frame available, sleep briefly
                        time.sleep(0.1)
                        continue
                    
                    # Track frame metric
                    frames_total.labels(camera_id=self.camera_id).inc()
                    
                    # Run detectors
                    start_time = time.time()
                    events = self._run_detectors(frame, ts_ms)
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Track latency metric
                    latency_histogram.labels(camera_id=self.camera_id).observe(latency_ms)
                    
                    # Track event metrics
                    for event in events:
                        events_total.labels(
                            camera_id=self.camera_id,
                            type=event["type"]
                        ).inc()
                    
                    # Log events
                    if events:
                        logger.info(
                            f"Detections: {len(events)} events",
                            extra={
                                "camera_id": self.camera_id,
                                "event_count": len(events),
                                "latency_ms": round(latency_ms, 2)
                            }
                        )
                    
                    # Publish events
                    self._publish_events(events)
                    
                    # Save snapshots
                    self._save_snapshots(frame, events, ts_ms)
                    
                except Exception as e:
                    logger.error(
                        f"Worker loop error: {e}",
                        extra={"camera_id": self.camera_id},
                        exc_info=True
                    )
                    
                    # Sleep briefly before retrying
                    time.sleep(1.0)
        
        except Exception as e:
            logger.error(
                f"Worker fatal error: {e}",
                extra={"camera_id": self.camera_id},
                exc_info=True
            )
        
        finally:
            # Cleanup
            if self.frame_source:
                self.frame_source.stop()
            
            logger.info(
                f"Worker loop ended: {self.camera_id}",
                extra={"camera_id": self.camera_id}
            )


# ============================================================================
# Application Manager
# ============================================================================

class Application:
    """
    Main application manager.
    
    Responsibilities:
    - Load configuration
    - Initialize AWS clients and publishers
    - Start camera workers
    - Start HTTP server (FastAPI + Prometheus)
    - Handle graceful shutdown
    """
    
    def __init__(self, config_path: str, http_bind: str = "0.0.0.0:8080"):
        """
        Initialize application.
        
        Args:
            config_path: Path to YAML config file
            http_bind: HTTP server bind address (host:port)
        """
        self.config_path = config_path
        self.http_bind = http_bind
        
        # Parse bind address
        host, port = http_bind.split(":")
        self.http_host = host
        self.http_port = int(port)
        
        # Configuration
        self.config: Optional[Dict[str, Any]] = None
        
        # Publishers
        self.publishers: Dict[str, Any] = {}
        
        # Workers
        self.workers: List[CameraWorker] = []
        
        # Shutdown flag
        self.shutdown_event = threading.Event()
        
        logger.info(
            f"Application initialized: config={config_path}, http={http_bind}"
        )
    
    def load_configuration(self):
        """Load YAML configuration."""
        logger.info(f"Loading configuration: {self.config_path}")
        
        self.config = load_config(Path(self.config_path))
        
        logger.info(
            f"Configuration loaded: {len(self.config.get('cameras', {}))} cameras"
        )
    
    def initialize_publishers(self):
        """Initialize AWS publishers (KDS, S3, DDB)."""
        logger.info("Initializing publishers")
        
        publisher_config = self.config.get("publishers", {})
        
        # KDS Publisher
        kds_config = publisher_config.get("kds", {})
        if kds_config.get("enabled", True):
            try:
                self.publishers["kds"] = KDSClient(
                    region=kds_config.get("region", "us-east-1"),
                    stream_name=kds_config["stream_name"],
                    batch_size=kds_config.get("batch_size", 500),
                    max_retries=kds_config.get("max_retries", 3),
                    base_backoff_ms=kds_config.get("base_backoff_ms", 100)
                )
                logger.info(f"KDS publisher initialized: {kds_config['stream_name']}")
            except Exception as e:
                logger.error(f"KDS initialization error: {e}", exc_info=True)
        
        # S3 Publisher
        s3_config = publisher_config.get("s3", {})
        if s3_config.get("enabled", True):
            try:
                self.publishers["s3"] = S3Snapshot(
                    bucket=s3_config["bucket"],
                    prefix=s3_config.get("prefix", "snapshots"),
                    region=s3_config.get("region", "us-east-1"),
                    jpeg_quality=s3_config.get("jpeg_quality", 90)
                )
                logger.info(f"S3 publisher initialized: {s3_config['bucket']}")
            except Exception as e:
                logger.error(f"S3 initialization error: {e}", exc_info=True)
        
        # DDB Publisher (optional)
        ddb_config = publisher_config.get("ddb", {})
        if ddb_config.get("enabled", False):
            try:
                self.publishers["ddb"] = DDBWriter(
                    table_name=ddb_config["table_name"],
                    region=ddb_config.get("region", "us-east-1"),
                    ttl_days=ddb_config.get("ttl_days")
                )
                logger.info(f"DDB publisher initialized: {ddb_config['table_name']}")
            except Exception as e:
                logger.error(f"DDB initialization error: {e}", exc_info=True)
    
    def start_workers(self):
        """Start camera worker threads."""
        logger.info("Starting camera workers")
        
        cameras = self.config.get("cameras", {})
        
        for camera_id, camera_config in cameras.items():
            # Skip disabled cameras
            if not camera_config.get("enabled", True):
                logger.info(f"Skipping disabled camera: {camera_id}")
                continue
            
            # Create worker
            worker = CameraWorker(
                camera_id=camera_id,
                camera_config=camera_config,
                global_config=self.config,
                publishers=self.publishers
            )
            
            # Start worker
            worker.start()
            
            self.workers.append(worker)
        
        logger.info(f"Started {len(self.workers)} camera workers")
    
    def start_http_server(self):
        """Start FastAPI HTTP server in background thread."""
        logger.info(f"Starting HTTP server: {self.http_host}:{self.http_port}")
        
        def run_server():
            uvicorn.run(
                app,
                host=self.http_host,
                port=self.http_port,
                log_level="warning",
                access_log=False
            )
        
        server_thread = threading.Thread(
            target=run_server,
            name="http-server",
            daemon=True
        )
        server_thread.start()
        
        logger.info(f"HTTP server started: http://{self.http_host}:{self.http_port}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Signal handlers registered")
    
    def shutdown(self):
        """Graceful shutdown."""
        if self.shutdown_event.is_set():
            logger.warning("Shutdown already in progress")
            return
        
        logger.info("Starting graceful shutdown")
        self.shutdown_event.set()
        
        # Stop workers
        logger.info(f"Stopping {len(self.workers)} workers")
        for worker in self.workers:
            worker.stop()
        
        # Flush publisher batches
        logger.info("Flushing publisher batches")
        
        if self.publishers.get("kds"):
            try:
                self.publishers["kds"].flush()
                metrics = self.publishers["kds"].get_metrics()
                logger.info(f"KDS final metrics: {metrics}")
            except Exception as e:
                logger.error(f"KDS flush error: {e}", exc_info=True)
        
        # Log final metrics
        if self.publishers.get("s3"):
            try:
                metrics = self.publishers["s3"].get_metrics()
                logger.info(f"S3 final metrics: {metrics}")
            except Exception as e:
                logger.error(f"S3 metrics error: {e}", exc_info=True)
        
        if self.publishers.get("ddb"):
            try:
                metrics = self.publishers["ddb"].get_metrics()
                logger.info(f"DDB final metrics: {metrics}")
            except Exception as e:
                logger.error(f"DDB metrics error: {e}", exc_info=True)
        
        logger.info("Graceful shutdown complete")
    
    def run(self):
        """Run application."""
        try:
            # Load configuration
            self.load_configuration()
            
            # Initialize publishers
            self.initialize_publishers()
            
            # Start HTTP server
            self.start_http_server()
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Start workers
            self.start_workers()
            
            # Main loop - wait for shutdown
            logger.info("Application running, waiting for shutdown signal")
            
            while not self.shutdown_event.is_set():
                time.sleep(1.0)
        
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
            self.shutdown()
        
        finally:
            logger.info("Application exited")


# ============================================================================
# CLI Entry Point
# ============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Multi-camera inference system with KVS integration"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML configuration file"
    )
    
    parser.add_argument(
        "--http",
        type=str,
        default="0.0.0.0:8080",
        help="HTTP server bind address (host:port), default: 0.0.0.0:8080"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Validate config file
    if not Path(args.config).exists():
        logger.error(f"Config file not found: {args.config}")
        sys.exit(1)
    
    # Create application
    application = Application(
        config_path=args.config,
        http_bind=args.http
    )
    
    # Run application
    application.run()


if __name__ == "__main__":
    main()
