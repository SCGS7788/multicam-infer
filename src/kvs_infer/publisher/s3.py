"""
S3 snapshot publisher for saving frame images as JPEG.
"""

import logging
from typing import Optional
from pathlib import Path
import numpy as np
import cv2
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class S3Snapshot:
    """
    S3 snapshot publisher for saving detection frames as JPEG images.
    
    Features:
    - Configurable JPEG quality (0-100)
    - Automatic key generation with timestamp
    - Structured logging for success/failure
    - Metrics tracking (saved, failed)
    - Optional local caching before upload
    
    Configuration:
        bucket: S3 bucket name
        prefix: Key prefix (e.g., "snapshots/camera_1")
        region: AWS region (default: "us-east-1")
        jpeg_quality: JPEG quality 0-100 (default: 90)
        
    Key Format:
        {prefix}/{camera_id}/{ts_ms}.jpg
        Example: snapshots/camera_1/1697123456789.jpg
        
    Example:
        snapshot = S3Snapshot(
            bucket="my-bucket",
            prefix="snapshots",
            jpeg_quality=90
        )
        
        # Save frame
        key = snapshot.save(frame, camera_id="camera_1", ts_ms=1697123456789)
        
        # Returns: "snapshots/camera_1/1697123456789.jpg"
    """
    
    def __init__(
        self,
        bucket: str,
        prefix: str,
        region: str = "us-east-1",
        jpeg_quality: int = 90
    ):
        """
        Initialize S3 snapshot publisher.
        
        Args:
            bucket: S3 bucket name
            prefix: Key prefix
            region: AWS region
            jpeg_quality: JPEG quality (0-100, higher = better quality)
        """
        self.bucket = bucket
        self.prefix = prefix.rstrip('/')  # Remove trailing slash
        self.region = region
        self.jpeg_quality = max(0, min(100, jpeg_quality))
        
        # Initialize boto3 client
        self.client = boto3.client('s3', region_name=region)
        
        # Metrics
        self.metrics = {
            "saved": 0,
            "failed": 0,
            "bytes_uploaded": 0,
        }
        
        logger.info(
            f"S3 snapshot publisher initialized: bucket={bucket}, "
            f"prefix={prefix}, quality={self.jpeg_quality}"
        )
    
    def save(
        self,
        frame: np.ndarray,
        camera_id: str,
        ts_ms: int,
        extra_metadata: Optional[dict] = None
    ) -> Optional[str]:
        """
        Save frame to S3 as JPEG image.
        
        Args:
            frame: Frame to save (BGR format, numpy array)
            camera_id: Camera identifier
            ts_ms: Timestamp in milliseconds
            extra_metadata: Optional metadata to attach to S3 object
            
        Returns:
            S3 key if successful, None if failed
        """
        # Generate key
        key = self._generate_key(camera_id, ts_ms)
        
        try:
            # Encode frame as JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            success, encoded_image = cv2.imencode('.jpg', frame, encode_params)
            
            if not success:
                logger.error(
                    f"Failed to encode frame as JPEG: camera={camera_id}, ts={ts_ms}",
                    extra={
                        "camera_id": camera_id,
                        "ts_ms": ts_ms
                    }
                )
                self.metrics["failed"] += 1
                return None
            
            # Convert to bytes
            image_bytes = encoded_image.tobytes()
            image_size = len(image_bytes)
            
            # Prepare S3 metadata
            metadata = {
                "camera_id": camera_id,
                "timestamp_ms": str(ts_ms),
                "jpeg_quality": str(self.jpeg_quality),
                "frame_shape": f"{frame.shape[0]}x{frame.shape[1]}",
            }
            
            if extra_metadata:
                # Add extra metadata (convert all values to strings)
                for k, v in extra_metadata.items():
                    metadata[k] = str(v)
            
            # Upload to S3
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=image_bytes,
                ContentType='image/jpeg',
                Metadata=metadata
            )
            
            # Update metrics
            self.metrics["saved"] += 1
            self.metrics["bytes_uploaded"] += image_size
            
            logger.info(
                f"S3 snapshot saved: {key} ({image_size} bytes)",
                extra={
                    "bucket": self.bucket,
                    "key": key,
                    "camera_id": camera_id,
                    "ts_ms": ts_ms,
                    "size_bytes": image_size,
                    "jpeg_quality": self.jpeg_quality
                }
            )
            
            return key
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(
                f"S3 client error: {error_code} - {error_message}",
                extra={
                    "error_code": error_code,
                    "error_message": error_message,
                    "bucket": self.bucket,
                    "key": key,
                    "camera_id": camera_id,
                    "ts_ms": ts_ms
                },
                exc_info=True
            )
            
            self.metrics["failed"] += 1
            return None
            
        except Exception as e:
            logger.error(
                f"Unexpected error saving S3 snapshot: {e}",
                extra={
                    "bucket": self.bucket,
                    "key": key,
                    "camera_id": camera_id,
                    "ts_ms": ts_ms
                },
                exc_info=True
            )
            
            self.metrics["failed"] += 1
            return None
    
    def save_with_bbox(
        self,
        frame: np.ndarray,
        camera_id: str,
        ts_ms: int,
        detections: list,
        draw_labels: bool = True
    ) -> Optional[str]:
        """
        Save frame with bounding boxes drawn.
        
        Args:
            frame: Frame to save (BGR format)
            camera_id: Camera identifier
            ts_ms: Timestamp in milliseconds
            detections: List of (label, conf, bbox) tuples
            draw_labels: Whether to draw labels above boxes
            
        Returns:
            S3 key if successful, None if failed
        """
        # Draw bounding boxes on copy
        frame_copy = frame.copy()
        
        for label, conf, bbox in detections:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            
            # Draw rectangle
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            if draw_labels:
                # Draw label background
                label_text = f"{label} {conf:.2f}"
                (text_w, text_h), _ = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1
                )
                cv2.rectangle(
                    frame_copy,
                    (x1, y1 - text_h - 10),
                    (x1 + text_w, y1),
                    (0, 255, 0),
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    frame_copy,
                    label_text,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    1
                )
        
        # Save frame with metadata
        extra_metadata = {
            "detection_count": len(detections),
            "has_bboxes": "true"
        }
        
        return self.save(frame_copy, camera_id, ts_ms, extra_metadata)
    
    def _generate_key(self, camera_id: str, ts_ms: int) -> str:
        """
        Generate S3 key for snapshot.
        
        Format: {prefix}/{camera_id}/{ts_ms}.jpg
        
        Args:
            camera_id: Camera identifier
            ts_ms: Timestamp in milliseconds
            
        Returns:
            S3 key string
        """
        return f"{self.prefix}/{camera_id}/{ts_ms}.jpg"
    
    def get_metrics(self) -> dict:
        """
        Get publisher metrics.
        
        Returns:
            Metrics dict with saved, failed, bytes_uploaded counts
        """
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self.metrics = {
            "saved": 0,
            "failed": 0,
            "bytes_uploaded": 0,
        }
        
        logger.info("S3 snapshot metrics reset")
    
    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for S3 object.
        
        Args:
            key: S3 key
            expires_in: URL expiration in seconds (default: 1 hour)
            
        Returns:
            Presigned URL if successful, None if failed
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            
            logger.debug(
                f"Generated presigned URL: {key}",
                extra={
                    "bucket": self.bucket,
                    "key": key,
                    "expires_in": expires_in
                }
            )
            
            return url
            
        except ClientError as e:
            logger.error(
                f"Failed to generate presigned URL: {e}",
                extra={
                    "bucket": self.bucket,
                    "key": key
                },
                exc_info=True
            )
            
            return None
