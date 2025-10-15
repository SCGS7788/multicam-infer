"""
Fire and smoke detector using YOLO with temporal confirmation and deduplication.
"""

import logging
import hashlib
from typing import List, Optional, Dict, Any
from collections import deque
import numpy as np

from .base import (
    Detector, 
    Event, 
    DetectionContext, 
    DetectorRegistry,
    TemporalConfirmationHelper,
    filter_detections,
)
from .yolo_common import load_yolo_model, run_yolo
from ..utils import filter_boxes_by_roi, TemporalBuffer, temporal_confirm


logger = logging.getLogger(__name__)


def _bbox_to_grid(bbox: List[float], grid_size: int = 20) -> str:
    """
    Convert bbox to grid cell identifier for deduplication.
    
    Args:
        bbox: Bounding box [x1, y1, x2, y2]
        grid_size: Grid cell size in pixels
        
    Returns:
        Grid cell identifier "x_y"
    """
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2
    grid_x = int(center_x // grid_size)
    grid_y = int(center_y // grid_size)
    return f"{grid_x}_{grid_y}"


def _detection_hash(label: str, bbox: List[float], grid_size: int = 20) -> str:
    """
    Generate hash for detection deduplication.
    
    Args:
        label: Detection label
        bbox: Bounding box [x1, y1, x2, y2]
        grid_size: Grid cell size for spatial quantization
        
    Returns:
        Hash string combining label and grid position
    """
    grid_id = _bbox_to_grid(bbox, grid_size)
    hash_input = f"{label}:{grid_id}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]


@DetectorRegistry.register("fire_smoke")
class FireSmokeDetector(Detector):
    """
    Fire and smoke detector using YOLO with temporal confirmation and deduplication.
    
    Treats "fire" and "smoke" labels separately with configurable thresholds.
    Emits events with type="fire" or type="smoke" based on detection label.
    
    Configuration:
        model_path: str - Path to YOLO model weights
        device: Optional[str] - Device (None = auto-select)
        fire_labels: List[str] - Fire class labels (default: ["fire"])
        smoke_labels: List[str] - Smoke class labels (default: ["smoke"])
        fire_conf_threshold: float - Fire confidence threshold (default: 0.6)
        smoke_conf_threshold: float - Smoke confidence threshold (default: 0.55)
        iou_threshold: float - IoU threshold for NMS (default: 0.5)
        temporal_window: int - Temporal confirmation window frames (default: 5)
        temporal_iou: float - IoU threshold for temporal matching (default: 0.3)
        temporal_min_conf: int - Minimum confirmations required (default: 3)
        dedup_window: int - Deduplication window in frames (default: 30)
        dedup_grid_size: int - Grid size for spatial deduplication (default: 20)
        
    Example:
        cfg = {
            "model_path": "fire_smoke_yolov8n.pt",
            "fire_labels": ["fire", "flame"],
            "smoke_labels": ["smoke"],
            "fire_conf_threshold": 0.65,
            "smoke_conf_threshold": 0.55,
            "temporal_window": 5,
            "temporal_min_conf": 3,
        }
        detector = DetectorRegistry.create("fire_smoke", cfg)
    """
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.fire_labels = ["fire"]
        self.smoke_labels = ["smoke"]
        self.fire_conf_threshold = 0.6
        self.smoke_conf_threshold = 0.55
        self.iou_threshold = 0.5
        self.temporal_helper = None
        self.dedup_window = 30
        self.dedup_grid_size = 20
        self._recent_detections: deque = deque(maxlen=30)  # (frame_count, hash)
        self._frame_count = 0
    
    def configure(self, cfg: Dict[str, Any]) -> None:
        """
        Configure the fire/smoke detector.
        
        Args:
            cfg: Configuration dictionary
            
        Raises:
            ValueError: If required config is missing
        """
        # Required config
        model_path = cfg.get("model_path")
        if not model_path:
            raise ValueError("fire_smoke detector requires 'model_path' in config")
        
        # Detection labels
        self.fire_labels = cfg.get("fire_labels", ["fire"])
        self.smoke_labels = cfg.get("smoke_labels", ["smoke"])
        
        if not self.fire_labels and not self.smoke_labels:
            raise ValueError("At least one of fire_labels or smoke_labels must be specified")
        
        # Load YOLO model
        device = cfg.get("device")
        logger.info(f"Loading fire/smoke detector model: {model_path}")
        self.model = load_yolo_model(model_path, device=device)
        
        # Detection thresholds (separate for fire and smoke)
        self.fire_conf_threshold = cfg.get("fire_conf_threshold", 0.6)
        self.smoke_conf_threshold = cfg.get("smoke_conf_threshold", 0.55)
        self.iou_threshold = cfg.get("iou_threshold", 0.5)
        
        # Temporal confirmation
        temporal_window = cfg.get("temporal_window", 5)
        temporal_iou = cfg.get("temporal_iou", 0.3)
        temporal_min_conf = cfg.get("temporal_min_conf", 3)
        
        self.temporal_helper = TemporalConfirmationHelper(
            window_frames=temporal_window,
            iou_threshold=temporal_iou,
            min_confirmations=temporal_min_conf,
        )
        
        # Deduplication settings
        self.dedup_window = cfg.get("dedup_window", 30)
        self.dedup_grid_size = cfg.get("dedup_grid_size", 20)
        self._recent_detections = deque(maxlen=self.dedup_window)
        
        self._configured = True
        
        logger.info(
            f"Fire/Smoke detector configured: "
            f"fire={self.fire_labels}({self.fire_conf_threshold}), "
            f"smoke={self.smoke_labels}({self.smoke_conf_threshold}), "
            f"temporal=({temporal_window},{temporal_min_conf}), "
            f"dedup={self.dedup_window}"
        )
    
    def _get_threshold_for_label(self, label: str) -> float:
        """Get appropriate confidence threshold for a label."""
        if label in self.fire_labels:
            return self.fire_conf_threshold
        elif label in self.smoke_labels:
            return self.smoke_conf_threshold
        else:
            return max(self.fire_conf_threshold, self.smoke_conf_threshold)
    
    def _get_event_type_for_label(self, label: str) -> str:
        """Get event type (fire or smoke) for a label."""
        if label in self.fire_labels:
            return "fire"
        elif label in self.smoke_labels:
            return "smoke"
        else:
            return "fire_smoke"  # Fallback
    
    def process(
        self,
        frame: np.ndarray,
        ts_ms: int,
        ctx: DetectionContext,
    ) -> List[Event]:
        """
        Process frame and detect fire/smoke.
        
        Args:
            frame: Input frame (BGR format)
            ts_ms: Timestamp in milliseconds
            ctx: Detection context (ROI, min_box_area, etc.)
            
        Returns:
            List of fire/smoke detection events
        """
        if not self.is_configured():
            logger.error("Fire/Smoke detector not configured")
            return []
        
        self._frame_count += 1
        
        # Run YOLO inference with lower threshold (filter later per label)
        min_threshold = min(self.fire_conf_threshold, self.smoke_conf_threshold)
        
        detections = run_yolo(
            self.model,
            frame,
            classes=None,  # Get all classes, filter later
            conf=min_threshold,
            iou=self.iou_threshold,
        )
        
        if not detections:
            return []
        
        # Filter by fire/smoke labels and apply per-label thresholds
        filtered_detections = []
        for label, conf, bbox in detections:
            # Check if label is fire or smoke
            if label not in self.fire_labels and label not in self.smoke_labels:
                continue
            
            # Apply per-label threshold
            threshold = self._get_threshold_for_label(label)
            if conf < threshold:
                continue
            
            filtered_detections.append((label, conf, bbox))
        
        if not filtered_detections:
            return []
        
        # Apply ROI and min_box_area filtering
        filtered_detections = filter_detections(
            filtered_detections,
            roi_polygons=ctx.roi_polygons,
            min_area=ctx.min_box_area,
        )
        
        if not filtered_detections:
            return []
        
        # Temporal confirmation and deduplication
        events = []
        
        for label, conf, bbox in filtered_detections:
            # Check temporal confirmation
            is_confirmed = self.temporal_helper.add_and_check(
                label=label,
                bbox=bbox,
                conf=conf,
                ts_ms=ts_ms,
            )
            
            if not is_confirmed:
                continue
            
            # Check deduplication
            det_hash = _detection_hash(label, bbox, self.dedup_grid_size)
            
            # Check if this detection was recently emitted
            is_duplicate = False
            for frame_num, recent_hash in self._recent_detections:
                if recent_hash == det_hash:
                    # Check if within dedup window
                    if (self._frame_count - frame_num) < self.dedup_window:
                        is_duplicate = True
                        break
            
            if is_duplicate:
                logger.debug(
                    f"Duplicate fire/smoke detection filtered: {label} @ {bbox}"
                )
                continue
            
            # Add to recent detections
            self._recent_detections.append((self._frame_count, det_hash))
            
            # Get event type (fire or smoke)
            event_type = self._get_event_type_for_label(label)
            
            # Create event
            event = Event(
                camera_id=ctx.camera_id,
                type=event_type,
                label=label,
                conf=conf,
                bbox=bbox,
                ts_ms=ts_ms,
                extras={
                    "frame_count": self._frame_count,
                    "det_hash": det_hash,
                    "threshold_used": self._get_threshold_for_label(label),
                },
            )
            
            events.append(event)
            
            logger.warning(
                f"🔥 {event_type.upper()} detected: {label} ({conf:.2f}) @ {bbox} "
                f"[frame={self._frame_count}]"
            )
        
        return events
