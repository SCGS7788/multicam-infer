"""
Roboflow Inference API Detector
Uses Roboflow serverless API for gun detection
"""

import cv2
import numpy as np
import tempfile
import os
import logging
from typing import List, Dict, Any
from inference_sdk import InferenceHTTPClient

from kvs_infer.detectors.base import Detector, Event, DetectionContext


class RoboflowGunDetector(Detector):
    """
    Gun detector using Roboflow Inference API
    Model: cctv-gun-detection-gkc0n/2
    
    Inherits from Detector base class for compatibility with kvs-infer system.
    """
    
    def __init__(self):
        """Initialize detector (config will be set via configure())"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.api_key = None
        self.api_url = "https://serverless.roboflow.com"
        self.model_id = None
        self.confidence_threshold = 0.5
    
    def configure(self, cfg: Dict[str, Any]) -> None:
        """
        Configure detector from config dict
        
        Args:
            cfg: Configuration with keys:
                - api_key: Roboflow API key
                - model_id: Model identifier (e.g., "cctv-gun-detection-gkc0n/2")
                - confidence_threshold: Minimum confidence (optional, default 0.5)
                - api_url: API URL (optional)
        """
        super().configure(cfg)
        
        # Get parameters
        self.api_key = cfg.get('api_key', 'oBQpsjr25DqFZziUSMVN')
        self.model_id = cfg.get('model_id', 'cctv-gun-detection-gkc0n/2')
        self.confidence_threshold = cfg.get('confidence_threshold', 0.5)
        self.api_url = cfg.get('api_url', 'https://serverless.roboflow.com')
        
        # Initialize client
        self.client = InferenceHTTPClient(
            api_url=self.api_url,
            api_key=self.api_key
        )
        
        self.logger.info(f"RoboflowGunDetector configured")
        self.logger.info(f"  Model: {self.model_id}")
        self.logger.info(f"  Confidence threshold: {self.confidence_threshold}")
    
    def detect(self, frame: np.ndarray, ts_ms: int) -> List[Event]:
        """
        Backward compatibility wrapper for process()
        
        Args:
            frame: OpenCV image (BGR format)
            ts_ms: Timestamp in milliseconds
            
        Returns:
            List of Event objects
        """
        # Get frame dimensions
        frame_height, frame_width = frame.shape[:2]
        
        # Create default context (no ROI filtering for Roboflow API)
        ctx = DetectionContext(
            camera_id="unknown",
            frame_width=frame_width,
            frame_height=frame_height,
            roi_polygons=[],
            min_box_area=0
        )
        return self.process(frame, ts_ms, ctx)
    
    def process(
        self,
        frame: np.ndarray,
        ts_ms: int,
        ctx: DetectionContext
    ) -> List[Event]:
        """
        Run detection on frame using Roboflow API
        
        Args:
            frame: OpenCV image (BGR format)
            ts_ms: Timestamp in milliseconds
            ctx: Detection context
            
        Returns:
            List of Event objects
        """
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Save frame to temporary file (Roboflow API requires file path or URL)
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            cv2.imwrite(tmp.name, frame_rgb)
            tmp_path = tmp.name
        
        events = []
        
        try:
            # Call Roboflow API with file path
            result = self.client.infer(tmp_path, model_id=self.model_id)
            
            # Parse results and create Event objects
            if 'predictions' in result:
                for pred in result['predictions']:
                    confidence = pred.get('confidence', 0.0)
                    
                    # Filter by confidence
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Extract bbox
                    x = pred['x']
                    y = pred['y']
                    width = pred['width']
                    height = pred['height']
                    
                    # Convert to x1, y1, x2, y2
                    x1 = float(x - width / 2)
                    y1 = float(y - height / 2)
                    x2 = float(x + width / 2)
                    y2 = float(y + height / 2)
                    
                    # Get class label
                    label = pred.get('class', 'gun')
                    
                    # Create Event
                    event = Event(
                        camera_id=ctx.camera_id,
                        type='weapon_detected',
                        label=label,
                        conf=confidence,
                        bbox=[x1, y1, x2, y2],
                        ts_ms=ts_ms,
                        extras={
                            'detector': 'roboflow_gun',
                            'model_id': self.model_id
                        }
                    )
                    
                    events.append(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Roboflow API error: {e}")
            return []
        
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
