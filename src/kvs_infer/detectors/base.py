"""
Base detector interface with registry, temporal confirmation, and ROI filtering.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from collections import deque
import logging
import time

import numpy as np


logger = logging.getLogger(__name__)


# ============================================================================
# Event Schema
# ============================================================================

@dataclass
class Event:
    """
    Detection event schema.
    
    Attributes:
        camera_id: Camera identifier
        type: Event type (e.g., "weapon_detected", "fire_detected", "alpr")
        label: Detection class label
        conf: Confidence score (0.0-1.0)
        bbox: Bounding box [x1, y1, x2, y2] in absolute coordinates
        ts_ms: Timestamp in milliseconds since epoch
        extras: Additional detector-specific data
    """
    camera_id: str
    type: str
    label: str
    conf: float
    bbox: List[float]  # [x1, y1, x2, y2]
    ts_ms: int
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def validate(self) -> bool:
        """
        Validate event schema.
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            if not self.camera_id or not self.type or not self.label:
                return False
            
            # Validate confidence
            if not (0.0 <= self.conf <= 1.0):
                return False
            
            # Validate bbox
            if len(self.bbox) != 4:
                return False
            x1, y1, x2, y2 = self.bbox
            if x2 <= x1 or y2 <= y1:
                return False
            
            # Validate timestamp
            if self.ts_ms <= 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Event validation error: {e}")
            return False


# ============================================================================
# Detection Context
# ============================================================================

@dataclass
class DetectionContext:
    """
    Context passed to detector process() method.
    
    Provides information about the current frame and camera configuration.
    """
    camera_id: str
    frame_width: int
    frame_height: int
    roi_polygons: Optional[List[List[Tuple[float, float]]]] = None
    min_box_area: Optional[int] = None
    extras: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Base Detector Interface
# ============================================================================

class Detector(ABC):
    """
    Abstract base class for all detectors.
    
    Subclasses must implement:
    - configure(cfg: dict) - Configure detector from config dict
    - process(frame, ts_ms, ctx) - Process frame and return events
    
    Example:
        class MyDetector(Detector):
            def __init__(self):
                super().__init__()
                self.name = "my_detector"
                
            def configure(self, cfg: dict):
                self.confidence = cfg.get("confidence", 0.5)
                self._configured = True
                
            def process(self, frame, ts_ms, ctx):
                if not self._configured:
                    raise RuntimeError("Detector not configured")
                
                # Run detection
                detections = self._run_detection(frame)
                
                # Convert to events
                events = []
                for det in detections:
                    event = Event(
                        camera_id=ctx.camera_id,
                        type="my_detection",
                        label=det["label"],
                        conf=det["conf"],
                        bbox=det["bbox"],
                        ts_ms=ts_ms,
                    )
                    events.append(event)
                
                return events
    """
    
    def __init__(self):
        """Initialize detector."""
        self.name: str = "base_detector"
        self._configured: bool = False
    
    @abstractmethod
    def configure(self, cfg: Dict[str, Any]):
        """
        Configure detector from configuration dictionary.
        
        Args:
            cfg: Configuration dictionary
            
        Raises:
            ValueError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def process(
        self,
        frame: np.ndarray,
        ts_ms: int,
        ctx: DetectionContext
    ) -> List[Event]:
        """
        Process a frame and return detection events.
        
        Args:
            frame: Input frame (numpy array, BGR format)
            ts_ms: Frame timestamp in milliseconds since epoch
            ctx: Detection context with camera info and ROI
            
        Returns:
            List of Event objects
            
        Raises:
            RuntimeError: If detector not configured
        """
        pass
    
    def is_configured(self) -> bool:
        """Check if detector is configured."""
        return self._configured
    
    def get_name(self) -> str:
        """Get detector name."""
        return self.name


# ============================================================================
# Detector Registry
# ============================================================================

class DetectorRegistry:
    """
    Registry for detector classes.
    
    Provides decorator-based registration and factory methods.
    
    Example:
        @DetectorRegistry.register("weapon")
        class WeaponDetector(Detector):
            pass
        
        # Create detector from config
        detector = DetectorRegistry.create("weapon", config)
    """
    
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str) -> Callable:
        """
        Decorator to register a detector class.
        
        Args:
            name: Detector name (must be unique)
            
        Returns:
            Decorator function
            
        Example:
            @DetectorRegistry.register("my_detector")
            class MyDetector(Detector):
                pass
        """
        def decorator(detector_class: type) -> type:
            if not issubclass(detector_class, Detector):
                raise TypeError(
                    f"Detector class {detector_class.__name__} must inherit from Detector"
                )
            
            if name in cls._registry:
                logger.warning(
                    f"Detector '{name}' already registered, overwriting"
                )
            
            cls._registry[name] = detector_class
            logger.debug(f"Registered detector: {name} -> {detector_class.__name__}")
            
            return detector_class
        
        return decorator
    
    @classmethod
    def create(cls, name: str, cfg: Optional[Dict[str, Any]] = None) -> Detector:
        """
        Create and configure a detector instance.
        
        Args:
            name: Detector name
            cfg: Configuration dictionary (optional)
            
        Returns:
            Configured detector instance
            
        Raises:
            KeyError: If detector not registered
            ValueError: If configuration is invalid
        """
        if name not in cls._registry:
            raise KeyError(
                f"Detector '{name}' not registered. "
                f"Available: {list(cls._registry.keys())}"
            )
        
        detector_class = cls._registry[name]
        detector = detector_class()
        
        if cfg is not None:
            detector.configure(cfg)
        
        return detector
    
    @classmethod
    def list_detectors(cls) -> List[str]:
        """List all registered detector names."""
        return list(cls._registry.keys())
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if detector is registered."""
        return name in cls._registry
    
    @classmethod
    def clear(cls):
        """Clear registry (mainly for testing)."""
        cls._registry.clear()


# ============================================================================
# Temporal Confirmation Helper
# ============================================================================

@dataclass
class TemporalDetection:
    """
    Detection with temporal information.
    """
    label: str
    bbox: List[float]  # [x1, y1, x2, y2]
    conf: float
    timestamp: float
    frame_index: int


class TemporalConfirmationHelper:
    """
    Helper for temporal confirmation of detections across frames.
    
    Maintains a sliding window of recent detections and confirms if the same
    object (label + IoU overlap) appears consistently across N frames.
    
    Example:
        helper = TemporalConfirmationHelper(
            window_frames=5,
            iou_threshold=0.5,
            min_confirmations=3,
        )
        
        # Each frame
        confirmed = helper.add_and_check(
            camera_id="cam-1",
            label="weapon",
            bbox=[100, 100, 200, 200],
            conf=0.9,
            frame_index=frame_idx,
        )
        
        if confirmed:
            # Object confirmed across multiple frames
            trigger_alert()
    """
    
    def __init__(
        self,
        window_frames: int = 5,
        iou_threshold: float = 0.5,
        min_confirmations: int = 3,
    ):
        """
        Initialize temporal confirmation helper.
        
        Args:
            window_frames: Number of recent frames to keep in window
            iou_threshold: IoU threshold for matching detections (0.0-1.0)
            min_confirmations: Minimum confirmations required across window
        """
        if not (1 <= window_frames <= 100):
            raise ValueError("window_frames must be between 1 and 100")
        if not (0.0 <= iou_threshold <= 1.0):
            raise ValueError("iou_threshold must be between 0.0 and 1.0")
        if not (1 <= min_confirmations <= window_frames):
            raise ValueError(
                f"min_confirmations must be between 1 and window_frames ({window_frames})"
            )
        
        self.window_frames = window_frames
        self.iou_threshold = iou_threshold
        self.min_confirmations = min_confirmations
        
        # Per-camera detection history
        # {camera_id: deque of TemporalDetection}
        self._history: Dict[str, deque] = {}
    
    def add_detection(
        self,
        camera_id: str,
        label: str,
        bbox: List[float],
        conf: float,
        frame_index: int,
    ):
        """
        Add a detection to the temporal window.
        
        Args:
            camera_id: Camera identifier
            label: Detection label
            bbox: Bounding box [x1, y1, x2, y2]
            conf: Confidence score
            frame_index: Frame index or timestamp
        """
        if camera_id not in self._history:
            self._history[camera_id] = deque(maxlen=self.window_frames)
        
        detection = TemporalDetection(
            label=label,
            bbox=bbox,
            conf=conf,
            timestamp=time.time(),
            frame_index=frame_index,
        )
        
        self._history[camera_id].append(detection)
    
    def check_confirmation(
        self,
        camera_id: str,
        label: str,
        bbox: List[float],
    ) -> bool:
        """
        Check if detection is confirmed across temporal window.
        
        Args:
            camera_id: Camera identifier
            label: Detection label to check
            bbox: Current bounding box [x1, y1, x2, y2]
            
        Returns:
            True if detection confirmed, False otherwise
        """
        if camera_id not in self._history:
            return False
        
        history = self._history[camera_id]
        if len(history) < self.min_confirmations:
            return False
        
        # Count confirmations (same label + IoU > threshold)
        confirmations = 0
        
        for past_det in history:
            if past_det.label != label:
                continue
            
            iou = calculate_iou(bbox, past_det.bbox)
            if iou >= self.iou_threshold:
                confirmations += 1
        
        return confirmations >= self.min_confirmations
    
    def add_and_check(
        self,
        camera_id: str,
        label: str,
        bbox: List[float],
        conf: float,
        frame_index: int,
    ) -> bool:
        """
        Add detection and immediately check if confirmed.
        
        Convenience method combining add_detection() and check_confirmation().
        
        Args:
            camera_id: Camera identifier
            label: Detection label
            bbox: Bounding box [x1, y1, x2, y2]
            conf: Confidence score
            frame_index: Frame index or timestamp
            
        Returns:
            True if detection confirmed, False otherwise
        """
        # Check before adding (check against history)
        confirmed = self.check_confirmation(camera_id, label, bbox)
        
        # Add to history
        self.add_detection(camera_id, label, bbox, conf, frame_index)
        
        return confirmed
    
    def clear_camera(self, camera_id: str):
        """Clear history for a specific camera."""
        if camera_id in self._history:
            del self._history[camera_id]
    
    def clear_all(self):
        """Clear all history."""
        self._history.clear()
    
    def get_window_size(self, camera_id: str) -> int:
        """Get current window size for camera."""
        if camera_id not in self._history:
            return 0
        return len(self._history[camera_id])


# ============================================================================
# ROI and Filtering Utilities
# ============================================================================

def calculate_iou(box1: List[float], box2: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    
    Args:
        box1: First box [x1, y1, x2, y2]
        box2: Second box [x1, y1, x2, y2]
        
    Returns:
        IoU value (0.0-1.0)
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Calculate union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    if union <= 0:
        return 0.0
    
    return intersection / union


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Check if point is inside polygon using ray casting algorithm.
    
    Args:
        point: (x, y) coordinates
        polygon: List of (x, y) vertices
        
    Returns:
        True if point inside polygon, False otherwise
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside


def bbox_in_roi(
    bbox: List[float],
    roi_polygons: List[List[Tuple[float, float]]],
    require_full_overlap: bool = False,
) -> bool:
    """
    Check if bounding box overlaps with any ROI polygon.
    
    Args:
        bbox: Bounding box [x1, y1, x2, y2]
        roi_polygons: List of ROI polygons (list of (x, y) vertices)
        require_full_overlap: If True, entire bbox must be in ROI
        
    Returns:
        True if bbox overlaps with any ROI, False otherwise
    """
    if not roi_polygons:
        return True  # No ROI = all detections valid
    
    x1, y1, x2, y2 = bbox
    
    # Check center point and corners
    center = ((x1 + x2) / 2, (y1 + y2) / 2)
    corners = [
        (x1, y1),  # Top-left
        (x2, y1),  # Top-right
        (x1, y2),  # Bottom-left
        (x2, y2),  # Bottom-right
    ]
    
    for polygon in roi_polygons:
        if require_full_overlap:
            # All corners must be inside
            if all(point_in_polygon(corner, polygon) for corner in corners):
                return True
        else:
            # Center or any corner inside
            if point_in_polygon(center, polygon):
                return True
            if any(point_in_polygon(corner, polygon) for corner in corners):
                return True
    
    return False


def filter_by_min_box_size(
    bbox: List[float],
    min_area: int,
) -> bool:
    """
    Check if bounding box meets minimum size requirement.
    
    Args:
        bbox: Bounding box [x1, y1, x2, y2]
        min_area: Minimum box area in pixels
        
    Returns:
        True if bbox meets requirement, False otherwise
    """
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    area = width * height
    
    return area >= min_area


def filter_detections(
    detections: List[Tuple[str, float, List[float]]],
    roi_polygons: Optional[List[List[Tuple[float, float]]]] = None,
    min_box_area: Optional[int] = None,
    require_full_overlap: bool = False,
) -> List[Tuple[str, float, List[float]]]:
    """
    Filter detections by ROI and minimum box size.
    
    Args:
        detections: List of (label, conf, bbox) tuples
        roi_polygons: Optional ROI polygons
        min_box_area: Optional minimum box area
        require_full_overlap: Require full bbox overlap with ROI
        
    Returns:
        Filtered list of detections
    """
    filtered = []
    
    for label, conf, bbox in detections:
        # Check ROI
        if roi_polygons is not None:
            if not bbox_in_roi(bbox, roi_polygons, require_full_overlap):
                continue
        
        # Check min box size
        if min_box_area is not None:
            if not filter_by_min_box_size(bbox, min_box_area):
                continue
        
        filtered.append((label, conf, bbox))
    
    return filtered
