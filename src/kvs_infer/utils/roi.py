"""
Region of Interest (ROI) utilities with Shapely-free geometric operations.

Provides:
- Point-in-polygon tests (ray casting algorithm)
- IoU (Intersection over Union) calculations
- ROI filtering for bounding boxes
- Temporal buffering with deque
- Visualization utilities
"""

from typing import List, Tuple, Optional, Union, Deque
from collections import deque
import numpy as np
import cv2


# ============================================================================
# Point-in-Polygon (Ray Casting Algorithm - Shapely-free)
# ============================================================================

def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.
    
    Simple, Shapely-free implementation using basic math.
    
    Algorithm:
        Cast a ray from the point to infinity (horizontally to the right).
        Count how many times the ray intersects polygon edges.
        If odd number of intersections → point is inside
        If even number of intersections → point is outside
    
    Args:
        point: (x, y) coordinates (float or int)
        polygon: List of (x, y) vertices defining the polygon
        
    Returns:
        True if point is inside polygon, False otherwise
        
    Example:
        >>> polygon = [(0, 0), (100, 0), (100, 100), (0, 100)]  # Square
        >>> point_in_polygon((50, 50), polygon)
        True
        >>> point_in_polygon((150, 50), polygon)
        False
    """
    if not polygon or len(polygon) < 3:
        return False
    
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        
        # Check if point is on horizontal ray path
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    # Calculate intersection point
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    
                    # Toggle inside flag if ray crosses edge
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        
        p1x, p1y = p2x, p2y
    
    return inside


# ============================================================================
# IoU (Intersection over Union) - Shapely-free
# ============================================================================

def iou(box1: List[float], box2: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    
    Shapely-free implementation using simple rectangle intersection math.
    
    Args:
        box1: First bounding box [x1, y1, x2, y2]
        box2: Second bounding box [x1, y1, x2, y2]
        
    Returns:
        IoU value in range [0.0, 1.0]
        0.0 = no overlap
        1.0 = perfect overlap
        
    Example:
        >>> box1 = [0, 0, 100, 100]
        >>> box2 = [50, 50, 150, 150]
        >>> iou(box1, box2)
        0.14285714285714285  # ~14% overlap
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Calculate intersection rectangle
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    # Check if boxes don't overlap
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    # Calculate areas
    intersection_area = (x2_i - x1_i) * (y2_i - y1_i)
    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
    
    # Union = area1 + area2 - intersection
    union_area = box1_area + box2_area - intersection_area
    
    if union_area <= 0:
        return 0.0
    
    return intersection_area / union_area


# ============================================================================
# ROI Filtering for Bounding Boxes
# ============================================================================

def filter_boxes_by_roi(
    boxes: List[Tuple[str, float, List[float]]],
    roi_polygons: Optional[List[List[Tuple[float, float]]]] = None,
    mode: str = "center",
    min_overlap: float = 0.5,
) -> List[Tuple[str, float, List[float]]]:
    """
    Filter bounding boxes by ROI polygons.
    
    This is the main ROI filtering function that supports multiple modes:
    - "center": Check if bbox center is inside any ROI polygon
    - "any": Check if any bbox corner is inside any ROI polygon  
    - "all": Check if all bbox corners are inside the same ROI polygon
    - "overlap": Check if bbox overlaps with ROI by min_overlap threshold
    
    Args:
        boxes: List of (label, confidence, bbox) tuples
               where bbox is [x1, y1, x2, y2]
        roi_polygons: Optional list of ROI polygons (each polygon is a list of (x, y) vertices)
                     If None or empty, returns all boxes (no filtering)
        mode: Filtering mode ("center", "any", "all", "overlap")
        min_overlap: For "overlap" mode, minimum overlap ratio (0.0-1.0)
        
    Returns:
        Filtered list of (label, confidence, bbox) tuples
        
    Example:
        >>> boxes = [
        ...     ("person", 0.9, [10, 10, 50, 50]),
        ...     ("person", 0.8, [200, 200, 240, 240]),
        ... ]
        >>> roi = [(0, 0), (100, 0), (100, 100), (0, 100)]  # Left side only
        >>> filtered = filter_boxes_by_roi(boxes, [roi], mode="center")
        >>> len(filtered)
        1  # Only first box passes (center at 30, 30)
    """
    # No ROI = no filtering
    if not roi_polygons:
        return boxes
    
    # Validate mode
    valid_modes = ["center", "any", "all", "overlap"]
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of {valid_modes}")
    
    filtered = []
    
    for label, conf, bbox in boxes:
        x1, y1, x2, y2 = bbox
        
        # Mode: "center" - check if bbox center is in any ROI
        if mode == "center":
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            center = (center_x, center_y)
            
            # Check if center is in any ROI polygon
            in_roi = any(
                point_in_polygon(center, polygon)
                for polygon in roi_polygons
            )
            
            if in_roi:
                filtered.append((label, conf, bbox))
        
        # Mode: "any" - check if any corner is in any ROI
        elif mode == "any":
            corners = [
                (x1, y1),  # Top-left
                (x2, y1),  # Top-right
                (x1, y2),  # Bottom-left
                (x2, y2),  # Bottom-right
            ]
            
            in_roi = any(
                point_in_polygon(corner, polygon)
                for polygon in roi_polygons
                for corner in corners
            )
            
            if in_roi:
                filtered.append((label, conf, bbox))
        
        # Mode: "all" - check if all corners are in the same ROI
        elif mode == "all":
            corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
            
            # Check each ROI polygon
            for polygon in roi_polygons:
                if all(point_in_polygon(corner, polygon) for corner in corners):
                    filtered.append((label, conf, bbox))
                    break
        
        # Mode: "overlap" - check bbox-ROI overlap ratio
        elif mode == "overlap":
            if bbox_overlaps_roi(bbox, roi_polygons, threshold=min_overlap):
                filtered.append((label, conf, bbox))
    
    return filtered


def bbox_overlaps_roi(
    bbox: List[float],
    roi_polygons: List[List[Tuple[float, float]]],
    threshold: float = 0.5,
) -> bool:
    """
    Check if bounding box overlaps with any ROI polygon above threshold.
    
    Uses OpenCV for mask-based overlap calculation.
    
    Args:
        bbox: Bounding box [x1, y1, x2, y2]
        roi_polygons: List of ROI polygons
        threshold: Minimum overlap ratio (0.0-1.0)
        
    Returns:
        True if bbox overlaps with any ROI above threshold
    """
    x1, y1, x2, y2 = map(int, bbox)
    
    if x2 <= x1 or y2 <= y1:
        return False
    
    bbox_area = (x2 - x1) * (y2 - y1)
    if bbox_area == 0:
        return False
    
    # Check each ROI polygon
    for roi_polygon in roi_polygons:
        polygon = np.array(roi_polygon, dtype=np.int32)
        
        # Determine mask size (cover both bbox and polygon)
        poly_x = [p[0] for p in roi_polygon]
        poly_y = [p[1] for p in roi_polygon]
        
        mask_width = max(max(poly_x), x2) + 1
        mask_height = max(max(poly_y), y2) + 1
        
        # Create ROI mask
        roi_mask = np.zeros((mask_height, mask_width), dtype=np.uint8)
        cv2.fillPoly(roi_mask, [polygon], 255)
        
        # Create bbox mask
        bbox_mask = np.zeros((mask_height, mask_width), dtype=np.uint8)
        bbox_mask[y1:y2, x1:x2] = 255
        
        # Calculate overlap
        intersection = cv2.bitwise_and(roi_mask, bbox_mask)
        intersection_area = np.count_nonzero(intersection)
        
        overlap_ratio = intersection_area / bbox_area
        
        if overlap_ratio >= threshold:
            return True
    
    return False


# ============================================================================
# Temporal Buffer Management
# ============================================================================

class TemporalBuffer:
    """
    Temporal buffer for tracking detections over time using deque.
    
    Maintains a sliding window of recent detections with configurable size.
    Useful for temporal smoothing and confirmation logic.
    
    Example:
        >>> buffer = TemporalBuffer(maxlen=10)
        >>> buffer.add("weapon", [100, 100, 200, 200], 0.9, frame_idx=1)
        >>> buffer.add("weapon", [102, 98, 202, 198], 0.88, frame_idx=2)
        >>> 
        >>> # Check if detection is confirmed (appears N times)
        >>> if buffer.count_similar("weapon", [101, 99, 201, 199], iou_threshold=0.5) >= 3:
        ...     print("Detection confirmed!")
    """
    
    def __init__(self, maxlen: int = 30):
        """
        Initialize temporal buffer.
        
        Args:
            maxlen: Maximum buffer size (oldest items auto-removed)
        """
        self.maxlen = maxlen
        self.buffer: Deque[Tuple[str, List[float], float, int]] = deque(maxlen=maxlen)
        self._frame_counter = 0
    
    def add(
        self,
        label: str,
        bbox: List[float],
        confidence: float,
        frame_idx: Optional[int] = None,
    ) -> None:
        """
        Add detection to buffer.
        
        Args:
            label: Detection class label
            bbox: Bounding box [x1, y1, x2, y2]
            confidence: Confidence score (0.0-1.0)
            frame_idx: Optional frame index (auto-increments if None)
        """
        if frame_idx is None:
            frame_idx = self._frame_counter
            self._frame_counter += 1
        
        self.buffer.append((label, bbox, confidence, frame_idx))
    
    def count_similar(
        self,
        label: str,
        bbox: List[float],
        iou_threshold: float = 0.5,
    ) -> int:
        """
        Count how many times a similar detection appears in buffer.
        
        Args:
            label: Detection label to match
            bbox: Bounding box to compare [x1, y1, x2, y2]
            iou_threshold: Minimum IoU to consider detections similar
            
        Returns:
            Count of similar detections
        """
        count = 0
        
        for buf_label, buf_bbox, _, _ in self.buffer:
            if buf_label != label:
                continue
            
            overlap = iou(bbox, buf_bbox)
            if overlap >= iou_threshold:
                count += 1
        
        return count
    
    def get_recent(self, n: int = 5) -> List[Tuple[str, List[float], float, int]]:
        """
        Get N most recent detections.
        
        Args:
            n: Number of recent items to return
            
        Returns:
            List of (label, bbox, confidence, frame_idx) tuples
        """
        return list(self.buffer)[-n:]
    
    def clear(self) -> None:
        """Clear buffer."""
        self.buffer.clear()
        self._frame_counter = 0
    
    def size(self) -> int:
        """Get current buffer size."""
        return len(self.buffer)
    
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self.buffer) == 0


def temporal_confirm(
    buffer: TemporalBuffer,
    label: str,
    bbox: List[float],
    confidence: float,
    min_confirmations: int = 3,
    iou_threshold: float = 0.5,
    frame_idx: Optional[int] = None,
) -> bool:
    """
    Add detection to buffer and check if temporally confirmed.
    
    A detection is "confirmed" if it appears at least min_confirmations times
    in the temporal buffer with sufficient IoU overlap.
    
    Args:
        buffer: TemporalBuffer instance
        label: Detection label
        bbox: Bounding box [x1, y1, x2, y2]
        confidence: Confidence score
        min_confirmations: Minimum number of similar detections required
        iou_threshold: Minimum IoU for matching detections
        frame_idx: Optional frame index
        
    Returns:
        True if detection is confirmed, False otherwise
        
    Example:
        >>> buffer = TemporalBuffer(maxlen=10)
        >>> 
        >>> # Frame 1
        >>> confirmed = temporal_confirm(buffer, "weapon", [100, 100, 200, 200], 0.9, min_confirmations=3)
        >>> # confirmed = False (only 1 detection so far)
        >>> 
        >>> # Frame 2
        >>> confirmed = temporal_confirm(buffer, "weapon", [102, 98, 202, 198], 0.88, min_confirmations=3)
        >>> # confirmed = False (only 2 detections)
        >>> 
        >>> # Frame 3
        >>> confirmed = temporal_confirm(buffer, "weapon", [101, 99, 201, 199], 0.91, min_confirmations=3)
        >>> # confirmed = True (3 similar detections!)
    """
    # Check confirmation BEFORE adding (check against existing history)
    count = buffer.count_similar(label, bbox, iou_threshold)
    
    # Add current detection to buffer
    buffer.add(label, bbox, confidence, frame_idx)
    
    # Return True if we have enough confirmations
    # Note: count is checked BEFORE adding, so we compare with min_confirmations - 1
    return count >= (min_confirmations - 1)


# ============================================================================
# Legacy Functions (for backward compatibility)
# ============================================================================

def bbox_in_roi(
    bbox: List[float],
    roi_polygon: List[List[int]],
    threshold: float = 0.5,
) -> bool:
    """
    Check if a bounding box overlaps with an ROI polygon.
    
    Args:
        bbox: Bounding box [x1, y1, x2, y2]
        roi_polygon: List of [x, y] vertices defining the ROI
        threshold: Minimum overlap ratio (0-1) to consider bbox in ROI
        
    Returns:
        True if bbox overlaps with ROI above threshold, False otherwise
    """
    x1, y1, x2, y2 = map(int, bbox)
    
    # Convert polygon to proper format for OpenCV
    polygon = np.array(roi_polygon, dtype=np.int32)
    
    # Create mask for ROI
    # Get bounding rect of polygon to determine mask size
    poly_x = [p[0] for p in roi_polygon]
    poly_y = [p[1] for p in roi_polygon]
    mask_width = max(poly_x) + 1
    mask_height = max(poly_y) + 1
    
    # Expand mask to include bbox if needed
    mask_width = max(mask_width, x2 + 1)
    mask_height = max(mask_height, y2 + 1)
    
    roi_mask = np.zeros((mask_height, mask_width), dtype=np.uint8)
    cv2.fillPoly(roi_mask, [polygon], 255)
    
    # Create mask for bbox
    bbox_mask = np.zeros((mask_height, mask_width), dtype=np.uint8)
    bbox_mask[y1:y2, x1:x2] = 255
    
    # Calculate overlap
    intersection = cv2.bitwise_and(roi_mask, bbox_mask)
    intersection_area = np.count_nonzero(intersection)
    bbox_area = (x2 - x1) * (y2 - y1)
    
    if bbox_area == 0:
        return False
    
    overlap_ratio = intersection_area / bbox_area
    
    return overlap_ratio >= threshold


def bbox_center_in_roi(
    bbox: List[float],
    roi_polygon: List[List[int]],
) -> bool:
    """
    Check if the center of a bounding box is inside an ROI polygon.
    
    Args:
        bbox: Bounding box [x1, y1, x2, y2]
        roi_polygon: List of [x, y] vertices defining the ROI
        
    Returns:
        True if bbox center is in ROI, False otherwise
    """
    x1, y1, x2, y2 = bbox
    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)
    
    # Convert polygon format
    polygon = [(p[0], p[1]) for p in roi_polygon]
    
    return point_in_polygon((center_x, center_y), polygon)


def draw_roi(
    frame: np.ndarray,
    roi_polygon: List[List[int]],
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    alpha: float = 0.3,
) -> np.ndarray:
    """
    Draw an ROI polygon on a frame.
    
    Args:
        frame: Input frame
        roi_polygon: List of [x, y] vertices
        color: BGR color tuple
        thickness: Line thickness
        alpha: Fill transparency (0-1)
        
    Returns:
        Frame with ROI drawn
    """
    overlay = frame.copy()
    
    # Convert polygon
    polygon = np.array(roi_polygon, dtype=np.int32)
    
    # Fill polygon with transparency
    cv2.fillPoly(overlay, [polygon], color)
    
    # Blend with original
    frame = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)
    
    # Draw polygon border
    cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=thickness)
    
    return frame


def validate_roi_polygon(polygon: List[List[int]]) -> bool:
    """
    Validate an ROI polygon.
    
    Args:
        polygon: List of [x, y] vertices
        
    Returns:
        True if valid, False otherwise
    """
    if not polygon or len(polygon) < 3:
        return False
    
    for point in polygon:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return False
        if not isinstance(point[0], (int, float)) or not isinstance(point[1], (int, float)):
            return False
    
    return True
