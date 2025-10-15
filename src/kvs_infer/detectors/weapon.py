"""
Weapon detector using YOLO with temporal confirmation and deduplication.
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


@DetectorRegistry.register("weapon")
class WeaponDetector(Detector):
    """
    Weapon detector using YOLO with temporal confirmation and deduplication.
    
    Configuration:
        model_path: str - Path to YOLO model weights
        device: Optional[str] - Device (None = auto-select)
        classes: List[str] - List of weapon class labels to detect
        conf_threshold: float - Confidence threshold (default: 0.6)
        iou_threshold: float - IoU threshold for NMS (default: 0.5)
        
        # ROI Filtering (new in Step 7)
        roi_filter_mode: str - ROI filtering mode: "center", "any", "all", "overlap" (default: "center")
        roi_min_overlap: float - For "overlap" mode, minimum overlap ratio (default: 0.5)
        
        # Temporal Confirmation (new in Step 7 - uses utils.temporal_confirm)
        temporal_window: int - Temporal confirmation window frames (default: 5)
        temporal_iou: float - IoU threshold for temporal matching (default: 0.3)
        temporal_min_conf: int - Minimum confirmations required (default: 3)
        use_temporal_buffer: bool - Use new TemporalBuffer class (default: False, uses legacy helper)
        
        # Deduplication
        dedup_window: int - Deduplication window in frames (default: 30)
        dedup_grid_size: int - Grid size for spatial deduplication (default: 20)
        
    Example:
        cfg = {
            "model_path": "weapon_yolov8n.pt",
            "classes": ["knife", "gun", "rifle"],
            "conf_threshold": 0.65,
            "temporal_window": 5,
            "temporal_min_conf": 3,
            "roi_filter_mode": "center",  # New: ROI filtering mode
            "use_temporal_buffer": True,   # New: Use utils.TemporalBuffer
        }
        detector = DetectorRegistry.create("weapon", cfg)
    """
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.classes = []
        self.conf_threshold = 0.6
        self.iou_threshold = 0.5
        
        # ROI filtering config (Step 7)
        self.roi_filter_mode = "center"
        self.roi_min_overlap = 0.5
        
        # Temporal confirmation (legacy helper)
        self.temporal_helper = None
        
        # Temporal confirmation (new buffer - Step 7)
        self.use_temporal_buffer = False
        self.temporal_buffer: Optional[TemporalBuffer] = None
        self.temporal_min_conf = 3
        self.temporal_iou = 0.3
        
        # Deduplication
        self.dedup_window = 30
        self.dedup_grid_size = 20
        self._recent_detections: deque = deque(maxlen=30)  # (frame_count, hash)
        self._frame_count = 0
    
    def configure(self, cfg: Dict[str, Any]) -> None:
        """
        Configure the weapon detector.
        
        Args:
            cfg: Configuration dictionary
            
        Raises:
            ValueError: If required config is missing
        """
        # Required config
        model_path = cfg.get("model_path")
        if not model_path:
            raise ValueError("weapon detector requires 'model_path' in config")
        
        self.classes = cfg.get("classes", [])
        if not self.classes:
            logger.warning("No weapon classes specified, will detect all classes")
        
        # Load YOLO model
        device = cfg.get("device")
        logger.info(f"Loading weapon detector model: {model_path}")
        self.model = load_yolo_model(model_path, device=device)
        
        # Detection thresholds
        self.conf_threshold = cfg.get("conf_threshold", 0.6)
        self.iou_threshold = cfg.get("iou_threshold", 0.5)
        
        # ROI filtering configuration (Step 7)
        self.roi_filter_mode = cfg.get("roi_filter_mode", "center")
        self.roi_min_overlap = cfg.get("roi_min_overlap", 0.5)
        
        valid_roi_modes = ["center", "any", "all", "overlap"]
        if self.roi_filter_mode not in valid_roi_modes:
            raise ValueError(
                f"Invalid roi_filter_mode '{self.roi_filter_mode}'. "
                f"Must be one of {valid_roi_modes}"
            )
        
        # Temporal confirmation configuration
        temporal_window = cfg.get("temporal_window", 5)
        self.temporal_iou = cfg.get("temporal_iou", 0.3)
        self.temporal_min_conf = cfg.get("temporal_min_conf", 3)
        self.use_temporal_buffer = cfg.get("use_temporal_buffer", False)
        
        if self.use_temporal_buffer:
            # Use new TemporalBuffer from utils (Step 7)
            self.temporal_buffer = TemporalBuffer(maxlen=temporal_window)
            logger.info("Using new TemporalBuffer for temporal confirmation")
        else:
            # Use legacy TemporalConfirmationHelper from base
            self.temporal_helper = TemporalConfirmationHelper(
                window_frames=temporal_window,
                iou_threshold=self.temporal_iou,
                min_confirmations=self.temporal_min_conf,
            )
            logger.info("Using legacy TemporalConfirmationHelper")
        
        # Deduplication settings
        self.dedup_window = cfg.get("dedup_window", 30)
        self.dedup_grid_size = cfg.get("dedup_grid_size", 20)
        self._recent_detections = deque(maxlen=self.dedup_window)
        
        self._configured = True
        
        logger.info(
            f"Weapon detector configured: "
            f"classes={self.classes}, conf={self.conf_threshold}, "
            f"roi_mode={self.roi_filter_mode}, "
            f"temporal=({temporal_window},{self.temporal_min_conf}), "
            f"use_temporal_buffer={self.use_temporal_buffer}, "
            f"dedup={self.dedup_window}"
        )
    
    def process(
        self,
        frame: np.ndarray,
        ts_ms: int,
        ctx: DetectionContext,
    ) -> List[Event]:
        """
        Process frame and detect weapons.
        
        Args:
            frame: Input frame (BGR format)
            ts_ms: Timestamp in milliseconds
            ctx: Detection context (ROI, min_box_area, etc.)
            
        Returns:
            List of weapon detection events
        """
        if not self.is_configured():
            logger.error("Weapon detector not configured")
            return []
        
        self._frame_count += 1
        
        # Run YOLO inference
        detections = run_yolo(
            self.model,
            frame,
            classes=None,  # Get all classes, filter later
            conf=self.conf_threshold,
            iou=self.iou_threshold,
        )
        
        if not detections:
            return []
        
        # Filter by weapon classes
        if self.classes:
            detections = [
                (label, conf, bbox)
                for label, conf, bbox in detections
                if label in self.classes
            ]
        
        if not detections:
            return []
        
        # Apply ROI filtering using new filter_boxes_by_roi from utils (Step 7)
        if ctx.roi_polygons:
            detections = filter_boxes_by_roi(
                boxes=detections,
                roi_polygons=ctx.roi_polygons,
                mode=self.roi_filter_mode,
                min_overlap=self.roi_min_overlap,
            )
        
        # Apply min_box_area filtering (if configured)
        if ctx.min_box_area:
            detections = [
                (label, conf, bbox)
                for label, conf, bbox in detections
                if ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) >= ctx.min_box_area
            ]
        
        if not detections:
            return []
        
        # Temporal confirmation and deduplication
        events = []
        
        for label, conf, bbox in detections:
            # Temporal confirmation - use new or legacy method
            if self.use_temporal_buffer:
                # Use new temporal_confirm from utils (Step 7)
                is_confirmed = temporal_confirm(
                    buffer=self.temporal_buffer,
                    label=label,
                    bbox=bbox,
                    confidence=conf,
                    min_confirmations=self.temporal_min_conf,
                    iou_threshold=self.temporal_iou,
                    frame_idx=self._frame_count,
                )
            else:
                # Use legacy TemporalConfirmationHelper
                is_confirmed = self.temporal_helper.add_and_check(
                    camera_id=ctx.camera_id,
                    label=label,
                    bbox=bbox,
                    conf=conf,
                    frame_index=self._frame_count,
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
                    f"Duplicate weapon detection filtered: {label} @ {bbox}"
                )
                continue
            
            # Add to recent detections
            self._recent_detections.append((self._frame_count, det_hash))
            
            # Create event
            event = Event(
                camera_id=ctx.camera_id,
                type="weapon",
                label=label,
                conf=conf,
                bbox=bbox,
                ts_ms=ts_ms,
                extras={
                    "frame_count": self._frame_count,
                    "det_hash": det_hash,
                },
            )
            
            events.append(event)
            
            logger.info(
                f"Weapon detected: {label} ({conf:.2f}) @ {bbox} "
                f"[frame={self._frame_count}]"
            )
        
        return events
