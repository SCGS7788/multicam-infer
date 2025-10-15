#!/usr/bin/env python3
"""
Demo script for KVS HLS frame source.
Shows how to read frames from Kinesis Video Streams via HLS.

Usage:
    python examples/demo_kvs_hls_reader.py --stream-name my-kvs-stream --region us-east-1

Requirements:
    - AWS credentials configured (via ~/.aws/credentials or environment variables)
    - Active Kinesis Video Stream with live video
"""

import argparse
import logging
import sys
import time
import signal
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource, FrameSourceError
from kvs_infer.utils.metrics import start_metrics_server


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Global flag for graceful shutdown
RUNNING = True


def signal_handler(signum, frame):
    """Handle Ctrl+C for graceful shutdown."""
    global RUNNING
    logger.info("Received shutdown signal, stopping...")
    RUNNING = False


def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(
        description="Demo KVS HLS frame source",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--stream-name",
        required=True,
        help="KVS stream name",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region",
    )
    parser.add_argument(
        "--camera-id",
        default="demo-camera",
        help="Camera ID for metrics",
    )
    parser.add_argument(
        "--hls-session-seconds",
        type=int,
        default=300,
        help="HLS session expiry (60-43200)",
    )
    parser.add_argument(
        "--url-refresh-margin",
        type=int,
        default=30,
        help="Refresh URL N seconds before expiry",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Max frames to read (0=infinite)",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=5.0,
        help="Target FPS for frame reading (throttling)",
    )
    parser.add_argument(
        "--metrics-port",
        type=int,
        default=9090,
        help="Prometheus metrics port",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Don't display frames (headless mode)",
    )
    
    args = parser.parse_args()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start metrics server
    logger.info(f"Starting Prometheus metrics server on port {args.metrics_port}")
    start_metrics_server(port=args.metrics_port)
    
    # Create frame source
    logger.info(f"Initializing KVS HLS frame source for stream: {args.stream_name}")
    source = KVSHLSFrameSource(
        camera_id=args.camera_id,
        stream_name=args.stream_name,
        region=args.region,
        hls_session_seconds=args.hls_session_seconds,
        url_refresh_margin=args.url_refresh_margin,
    )
    
    # Display configuration
    try:
        # Try to import cv2 for display
        import cv2
        cv2_available = True
    except ImportError:
        cv2_available = False
        logger.warning("OpenCV not available, display disabled")
    
    display_enabled = cv2_available and not args.no_display
    
    # Read frames
    frame_count = 0
    start_time = time.time()
    last_print_time = start_time
    print_interval = 10.0  # Print stats every 10 seconds
    
    # FPS throttling
    frame_interval = 1.0 / args.target_fps if args.target_fps > 0 else 0
    last_frame_time = 0
    
    try:
        logger.info("Starting frame reading...")
        logger.info(f"Target FPS: {args.target_fps}")
        logger.info(f"Max frames: {args.max_frames if args.max_frames > 0 else 'unlimited'}")
        logger.info(f"Display: {'enabled' if display_enabled else 'disabled'}")
        logger.info(f"Metrics: http://localhost:{args.metrics_port}/metrics")
        logger.info("Press Ctrl+C to stop")
        logger.info("-" * 80)
        
        with source:
            for frame, timestamp in source.read_frames():
                if not RUNNING:
                    break
                
                # FPS throttling
                if frame_interval > 0:
                    now = time.time()
                    elapsed = now - last_frame_time
                    if elapsed < frame_interval:
                        time.sleep(frame_interval - elapsed)
                    last_frame_time = time.time()
                
                frame_count += 1
                
                # Display frame
                if display_enabled:
                    # Add overlay with info
                    import cv2
                    display_frame = frame.copy()
                    
                    # Add text overlay
                    text_lines = [
                        f"Camera: {args.camera_id}",
                        f"Frame: {frame_count}",
                        f"Shape: {frame.shape[1]}x{frame.shape[0]}",
                        f"State: {source.get_connection_state()}",
                    ]
                    
                    y_offset = 30
                    for line in text_lines:
                        cv2.putText(
                            display_frame,
                            line,
                            (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2,
                        )
                        y_offset += 30
                    
                    cv2.imshow(f"KVS HLS - {args.camera_id}", display_frame)
                    
                    # Handle keyboard input
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:  # q or ESC
                        logger.info("User requested stop")
                        break
                
                # Print stats periodically
                now = time.time()
                if now - last_print_time >= print_interval:
                    elapsed = now - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    metrics = source.get_metrics()
                    logger.info(
                        f"Stats: frames={frame_count}, "
                        f"fps={fps:.2f}, "
                        f"reconnects={metrics['reconnects_total']}, "
                        f"read_errors={metrics['read_errors_total']}, "
                        f"url_refreshes={metrics['url_refreshes_total']}"
                    )
                    last_print_time = now
                
                # Check max frames
                if args.max_frames > 0 and frame_count >= args.max_frames:
                    logger.info(f"Reached max frames: {args.max_frames}")
                    break
        
        # Final stats
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        
        logger.info("-" * 80)
        logger.info("Final Statistics:")
        logger.info(f"  Total frames: {frame_count}")
        logger.info(f"  Duration: {elapsed:.2f}s")
        logger.info(f"  Average FPS: {fps:.2f}")
        
        metrics = source.get_metrics()
        logger.info(f"  Reconnects: {metrics['reconnects_total']}")
        logger.info(f"  Read errors: {metrics['read_errors_total']}")
        logger.info(f"  URL refreshes: {metrics['url_refreshes_total']}")
        logger.info(f"  Connection state: {source.get_connection_state()}")
        logger.info(f"  Healthy: {source.is_healthy()}")
        
    except FrameSourceError as e:
        logger.error(f"Frame source error: {e}")
        return 1
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
        
    finally:
        if display_enabled:
            import cv2
            cv2.destroyAllWindows()
    
    logger.info("Demo complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
