"""
Upload snapshots and crops to S3.
"""

import logging
from io import BytesIO
from typing import Optional
from datetime import datetime
import cv2
import numpy as np
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class S3Publisher:
    """
    Upload image snapshots and detection crops to S3.
    
    Handles:
    - Full frame snapshots
    - Detection bounding box crops
    - Organized folder structure by date/camera
    """
    
    def __init__(
        self,
        bucket_name: str,
        prefix: str = "snapshots",
        region: str = "us-east-1",
        image_format: str = "jpg",
        jpeg_quality: int = 90,
    ):
        """
        Initialize S3 publisher.
        
        Args:
            bucket_name: S3 bucket name
            prefix: S3 key prefix (folder path)
            region: AWS region
            image_format: Image format ("jpg" or "png")
            jpeg_quality: JPEG quality (0-100)
        """
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip("/")
        self.region = region
        self.image_format = image_format.lower()
        self.jpeg_quality = jpeg_quality
        
        self.s3_client = boto3.client("s3", region_name=region)
        
        logger.info(
            f"Initialized S3 publisher for bucket: {bucket_name}, "
            f"prefix: {prefix}"
        )
    
    def _encode_image(self, image: np.ndarray) -> bytes:
        """
        Encode image to bytes.
        
        Args:
            image: Image as numpy array (BGR format)
            
        Returns:
            Encoded image bytes
        """
        if self.image_format == "jpg":
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            success, buffer = cv2.imencode(".jpg", image, encode_params)
        elif self.image_format == "png":
            success, buffer = cv2.imencode(".png", image)
        else:
            raise ValueError(f"Unsupported image format: {self.image_format}")
        
        if not success:
            raise RuntimeError("Failed to encode image")
        
        return buffer.tobytes()
    
    def _generate_key(
        self,
        camera_name: str,
        image_type: str,  # "snapshot" or "crop"
        timestamp: Optional[datetime] = None,
        detection_id: Optional[str] = None,
    ) -> str:
        """
        Generate S3 key for an image.
        
        Format: {prefix}/{camera_name}/{date}/{image_type}/{timestamp}[_{detection_id}].{ext}
        
        Args:
            camera_name: Camera name
            image_type: Type of image ("snapshot" or "crop")
            timestamp: Image timestamp
            detection_id: Optional detection ID for crops
            
        Returns:
            S3 key
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Date folder
        date_str = timestamp.strftime("%Y-%m-%d")
        
        # Timestamp in filename
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        
        # Build filename
        if detection_id:
            filename = f"{timestamp_str}_{detection_id}.{self.image_format}"
        else:
            filename = f"{timestamp_str}.{self.image_format}"
        
        # Build full key
        key = f"{self.prefix}/{camera_name}/{date_str}/{image_type}/{filename}"
        
        return key
    
    def upload_snapshot(
        self,
        frame: np.ndarray,
        camera_name: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Upload a full frame snapshot to S3.
        
        Args:
            frame: Frame as numpy array (BGR format)
            camera_name: Camera name
            timestamp: Frame timestamp
            metadata: Optional metadata to attach
            
        Returns:
            S3 key if successful, None otherwise
        """
        try:
            # Generate key
            key = self._generate_key(
                camera_name=camera_name,
                image_type="snapshot",
                timestamp=timestamp,
            )
            
            # Encode image
            image_bytes = self._encode_image(frame)
            
            # Prepare metadata
            s3_metadata = {}
            if metadata:
                # Convert all values to strings
                s3_metadata = {
                    k: str(v) for k, v in metadata.items()
                }
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_bytes,
                ContentType=f"image/{self.image_format}",
                Metadata=s3_metadata,
            )
            
            logger.debug(f"Uploaded snapshot to s3://{self.bucket_name}/{key}")
            
            return key
        
        except ClientError as e:
            logger.error(f"Failed to upload snapshot to S3: {e}", exc_info=True)
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}", exc_info=True)
            return None
    
    def upload_crop(
        self,
        frame: np.ndarray,
        bbox: list[float],
        camera_name: str,
        detection_id: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Upload a detection crop to S3.
        
        Args:
            frame: Full frame as numpy array (BGR format)
            bbox: Bounding box [x1, y1, x2, y2]
            camera_name: Camera name
            detection_id: Detection identifier
            timestamp: Frame timestamp
            metadata: Optional metadata to attach
            
        Returns:
            S3 key if successful, None otherwise
        """
        try:
            # Crop image
            x1, y1, x2, y2 = map(int, bbox)
            h, w = frame.shape[:2]
            
            # Clamp to frame boundaries
            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            
            if x2 <= x1 or y2 <= y1:
                logger.warning("Invalid crop bbox, skipping upload")
                return None
            
            crop = frame[y1:y2, x1:x2]
            
            # Generate key
            key = self._generate_key(
                camera_name=camera_name,
                image_type="crop",
                timestamp=timestamp,
                detection_id=detection_id,
            )
            
            # Encode image
            image_bytes = self._encode_image(crop)
            
            # Prepare metadata
            s3_metadata = {
                "bbox": f"{x1},{y1},{x2},{y2}",
                "detection_id": detection_id,
            }
            if metadata:
                s3_metadata.update({k: str(v) for k, v in metadata.items()})
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_bytes,
                ContentType=f"image/{self.image_format}",
                Metadata=s3_metadata,
            )
            
            logger.debug(f"Uploaded crop to s3://{self.bucket_name}/{key}")
            
            return key
        
        except Exception as e:
            logger.error(f"Failed to upload crop to S3: {e}", exc_info=True)
            return None
    
    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for an S3 object.
        
        Args:
            key: S3 key
            expires_in: URL expiration in seconds
            
        Returns:
            Presigned URL if successful, None otherwise
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                },
                ExpiresIn=expires_in,
            )
            return url
        
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}", exc_info=True)
            return None
