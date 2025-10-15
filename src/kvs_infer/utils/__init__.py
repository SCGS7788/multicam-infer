"""Utility modules."""

from .roi import (
    # Core geometric functions
    point_in_polygon,
    iou,
    
    # ROI filtering
    filter_boxes_by_roi,
    bbox_overlaps_roi,
    
    # Temporal buffering
    TemporalBuffer,
    temporal_confirm,
    
    # Visualization
    draw_roi,
    
    # Legacy compatibility
    bbox_in_roi,
    bbox_center_in_roi,
    validate_roi_polygon,
)

__all__ = [
    # Core functions
    "point_in_polygon",
    "iou",
    
    # ROI filtering
    "filter_boxes_by_roi",
    "bbox_overlaps_roi",
    
    # Temporal buffering
    "TemporalBuffer",
    "temporal_confirm",
    
    # Visualization
    "draw_roi",
    
    # Legacy
    "bbox_in_roi",
    "bbox_center_in_roi",
    "validate_roi_polygon",
]
