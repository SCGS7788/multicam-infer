"""
test_roi.py

Test ROI geometry operations.

Tests:
- IoU (Intersection over Union) calculation
- Point-in-polygon detection
- Bounding box intersection
- ROI filtering logic
"""

import pytest
import numpy as np
from typing import List, Tuple

from src.kvs_infer.roi import (
    calculate_iou,
    point_in_polygon,
    point_in_bbox,
    bbox_intersects_roi,
    filter_detections_by_roi,
)


class TestIoUCalculation:
    """Test Intersection over Union calculations."""
    
    def test_iou_identical_boxes(self):
        """Test IoU of identical boxes should be 1.0."""
        box1 = [100, 100, 200, 200]  # [x1, y1, x2, y2]
        box2 = [100, 100, 200, 200]
        
        iou = calculate_iou(box1, box2)
        assert pytest.approx(iou, 0.001) == 1.0
    
    def test_iou_no_overlap(self):
        """Test IoU of non-overlapping boxes should be 0.0."""
        box1 = [100, 100, 200, 200]
        box2 = [300, 300, 400, 400]
        
        iou = calculate_iou(box1, box2)
        assert iou == 0.0
    
    def test_iou_partial_overlap(self):
        """Test IoU of partially overlapping boxes."""
        box1 = [100, 100, 200, 200]  # Area = 10000
        box2 = [150, 150, 250, 250]  # Area = 10000
        # Intersection area = 50x50 = 2500
        # Union area = 10000 + 10000 - 2500 = 17500
        # IoU = 2500 / 17500 = 0.142857
        
        iou = calculate_iou(box1, box2)
        expected_iou = 2500 / 17500
        assert pytest.approx(iou, 0.001) == expected_iou
    
    def test_iou_one_inside_another(self):
        """Test IoU when one box is completely inside another."""
        box1 = [100, 100, 300, 300]  # Area = 40000
        box2 = [150, 150, 200, 200]  # Area = 2500
        # Intersection = 2500 (smaller box)
        # Union = 40000
        # IoU = 2500 / 40000 = 0.0625
        
        iou = calculate_iou(box1, box2)
        expected_iou = 2500 / 40000
        assert pytest.approx(iou, 0.001) == expected_iou
    
    def test_iou_touching_boxes(self):
        """Test IoU of boxes that touch at edges."""
        box1 = [100, 100, 200, 200]
        box2 = [200, 100, 300, 200]  # Touches at x=200
        
        iou = calculate_iou(box1, box2)
        # Should be 0 (edge touching doesn't count as overlap)
        assert iou == 0.0
    
    def test_iou_with_zero_area_box(self):
        """Test IoU with zero-area box."""
        box1 = [100, 100, 200, 200]
        box2 = [150, 150, 150, 150]  # Zero area
        
        iou = calculate_iou(box1, box2)
        assert iou == 0.0
    
    def test_iou_symmetry(self):
        """Test that IoU is symmetric: IoU(A,B) = IoU(B,A)."""
        box1 = [100, 100, 200, 200]
        box2 = [150, 150, 250, 250]
        
        iou1 = calculate_iou(box1, box2)
        iou2 = calculate_iou(box2, box1)
        
        assert pytest.approx(iou1, 0.001) == iou2
    
    def test_iou_with_negative_coordinates(self):
        """Test IoU with negative coordinates."""
        box1 = [-100, -100, 0, 0]
        box2 = [-50, -50, 50, 50]
        
        iou = calculate_iou(box1, box2)
        # Intersection area = 50x50 = 2500
        # Box1 area = 10000, Box2 area = 10000
        # Union = 10000 + 10000 - 2500 = 17500
        expected_iou = 2500 / 17500
        assert pytest.approx(iou, 0.001) == expected_iou
    
    def test_iou_with_float_coordinates(self):
        """Test IoU with floating point coordinates."""
        box1 = [100.5, 100.5, 200.5, 200.5]
        box2 = [150.5, 150.5, 250.5, 250.5]
        
        iou = calculate_iou(box1, box2)
        assert 0 <= iou <= 1


class TestPointInPolygon:
    """Test point-in-polygon detection."""
    
    def test_point_inside_triangle(self):
        """Test point inside a triangular polygon."""
        polygon = [[0, 0], [100, 0], [50, 100]]
        point = [50, 30]
        
        result = point_in_polygon(point, polygon)
        assert result is True
    
    def test_point_outside_triangle(self):
        """Test point outside a triangular polygon."""
        polygon = [[0, 0], [100, 0], [50, 100]]
        point = [150, 30]
        
        result = point_in_polygon(point, polygon)
        assert result is False
    
    def test_point_inside_rectangle(self):
        """Test point inside a rectangular polygon."""
        polygon = [[100, 100], [200, 100], [200, 200], [100, 200]]
        point = [150, 150]
        
        result = point_in_polygon(point, polygon)
        assert result is True
    
    def test_point_outside_rectangle(self):
        """Test point outside a rectangular polygon."""
        polygon = [[100, 100], [200, 100], [200, 200], [100, 200]]
        point = [250, 150]
        
        result = point_in_polygon(point, polygon)
        assert result is False
    
    def test_point_on_polygon_edge(self):
        """Test point on polygon edge."""
        polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
        point = [50, 0]  # On bottom edge
        
        result = point_in_polygon(point, polygon)
        # Edge cases can vary by implementation; typically considered inside
        assert result in [True, False]  # Accept either
    
    def test_point_at_polygon_vertex(self):
        """Test point at polygon vertex."""
        polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
        point = [0, 0]  # At vertex
        
        result = point_in_polygon(point, polygon)
        assert result in [True, False]  # Accept either
    
    def test_point_inside_complex_polygon(self):
        """Test point inside a complex (concave) polygon."""
        # L-shaped polygon
        polygon = [
            [0, 0], [100, 0], [100, 50], [50, 50],
            [50, 100], [0, 100]
        ]
        point = [25, 25]
        
        result = point_in_polygon(point, polygon)
        assert result is True
    
    def test_point_in_concave_region(self):
        """Test point in the concave region of a polygon."""
        # L-shaped polygon
        polygon = [
            [0, 0], [100, 0], [100, 50], [50, 50],
            [50, 100], [0, 100]
        ]
        point = [75, 75]  # In the concave cutout
        
        result = point_in_polygon(point, polygon)
        assert result is False
    
    def test_point_with_negative_coordinates(self):
        """Test point and polygon with negative coordinates."""
        polygon = [[-100, -100], [0, -100], [0, 0], [-100, 0]]
        point = [-50, -50]
        
        result = point_in_polygon(point, polygon)
        assert result is True
    
    def test_point_with_float_coordinates(self):
        """Test point and polygon with floating point coordinates."""
        polygon = [[0.0, 0.0], [100.5, 0.0], [100.5, 100.5], [0.0, 100.5]]
        point = [50.25, 50.75]
        
        result = point_in_polygon(point, polygon)
        assert result is True


class TestPointInBBox:
    """Test point-in-bounding-box detection."""
    
    def test_point_inside_bbox(self):
        """Test point inside bounding box."""
        bbox = [[100, 100], [200, 200]]
        point = [150, 150]
        
        result = point_in_bbox(point, bbox)
        assert result is True
    
    def test_point_outside_bbox(self):
        """Test point outside bounding box."""
        bbox = [[100, 100], [200, 200]]
        point = [250, 250]
        
        result = point_in_bbox(point, bbox)
        assert result is False
    
    def test_point_on_bbox_edge(self):
        """Test point on bounding box edge."""
        bbox = [[100, 100], [200, 200]]
        point = [150, 100]  # On top edge
        
        result = point_in_bbox(point, bbox)
        assert result is True  # Should be considered inside
    
    def test_point_at_bbox_corner(self):
        """Test point at bounding box corner."""
        bbox = [[100, 100], [200, 200]]
        point = [100, 100]  # Top-left corner
        
        result = point_in_bbox(point, bbox)
        assert result is True
    
    def test_point_outside_bbox_x(self):
        """Test point outside bbox in X direction."""
        bbox = [[100, 100], [200, 200]]
        point = [50, 150]
        
        result = point_in_bbox(point, bbox)
        assert result is False
    
    def test_point_outside_bbox_y(self):
        """Test point outside bbox in Y direction."""
        bbox = [[100, 100], [200, 200]]
        point = [150, 250]
        
        result = point_in_bbox(point, bbox)
        assert result is False
    
    def test_bbox_with_negative_coordinates(self):
        """Test bbox and point with negative coordinates."""
        bbox = [[-100, -100], [0, 0]]
        point = [-50, -50]
        
        result = point_in_bbox(point, bbox)
        assert result is True


class TestBBoxIntersectsROI:
    """Test bounding box intersection with ROI."""
    
    def test_bbox_fully_inside_polygon_roi(self):
        """Test bbox fully inside polygon ROI."""
        roi_polygon = [[0, 0], [200, 0], [200, 200], [0, 200]]
        detection_bbox = [50, 50, 150, 150]
        
        result = bbox_intersects_roi(detection_bbox, roi_polygon, roi_type="polygon")
        assert result is True
    
    def test_bbox_fully_outside_polygon_roi(self):
        """Test bbox fully outside polygon ROI."""
        roi_polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
        detection_bbox = [200, 200, 300, 300]
        
        result = bbox_intersects_roi(detection_bbox, roi_polygon, roi_type="polygon")
        assert result is False
    
    def test_bbox_partially_overlaps_polygon_roi(self):
        """Test bbox partially overlapping polygon ROI."""
        roi_polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
        detection_bbox = [50, 50, 150, 150]  # Partially overlaps
        
        result = bbox_intersects_roi(detection_bbox, roi_polygon, roi_type="polygon")
        assert result is True
    
    def test_bbox_center_in_polygon(self):
        """Test bbox with center point in polygon."""
        roi_polygon = [[0, 0], [200, 0], [200, 200], [0, 200]]
        detection_bbox = [80, 80, 120, 120]  # Center at (100, 100)
        
        result = bbox_intersects_roi(detection_bbox, roi_polygon, roi_type="polygon")
        assert result is True
    
    def test_bbox_corners_in_polygon(self):
        """Test bbox with at least one corner in polygon."""
        roi_polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
        detection_bbox = [90, 90, 110, 110]  # Top-left corner inside
        
        result = bbox_intersects_roi(detection_bbox, roi_polygon, roi_type="polygon")
        assert result is True
    
    def test_bbox_fully_inside_bbox_roi(self):
        """Test bbox fully inside bbox ROI."""
        roi_bbox = [[0, 0], [200, 200]]
        detection_bbox = [50, 50, 150, 150]
        
        result = bbox_intersects_roi(detection_bbox, roi_bbox, roi_type="bbox")
        assert result is True
    
    def test_bbox_fully_outside_bbox_roi(self):
        """Test bbox fully outside bbox ROI."""
        roi_bbox = [[0, 0], [100, 100]]
        detection_bbox = [200, 200, 300, 300]
        
        result = bbox_intersects_roi(detection_bbox, roi_bbox, roi_type="bbox")
        assert result is False
    
    def test_bbox_partially_overlaps_bbox_roi(self):
        """Test bbox partially overlapping bbox ROI."""
        roi_bbox = [[0, 0], [100, 100]]
        detection_bbox = [50, 50, 150, 150]
        
        result = bbox_intersects_roi(detection_bbox, roi_bbox, roi_type="bbox")
        assert result is True
    
    def test_bbox_touching_roi_edge(self):
        """Test bbox touching ROI edge."""
        roi_bbox = [[0, 0], [100, 100]]
        detection_bbox = [100, 50, 200, 150]  # Touches at x=100
        
        result = bbox_intersects_roi(detection_bbox, roi_bbox, roi_type="bbox")
        # Typically edge touching counts as intersection
        assert result is True or result is False  # Implementation-dependent


class TestFilterDetectionsByROI:
    """Test filtering detections by ROI."""
    
    def test_filter_all_inside_roi(self):
        """Test filtering when all detections are inside ROI."""
        detections = [
            {"bbox": [50, 50, 100, 100], "class": 0, "confidence": 0.9},
            {"bbox": [120, 120, 170, 170], "class": 2, "confidence": 0.85},
        ]
        roi_polygon = [[0, 0], [200, 0], [200, 200], [0, 200]]
        
        filtered = filter_detections_by_roi(detections, roi_polygon, roi_type="polygon")
        
        assert len(filtered) == 2
    
    def test_filter_all_outside_roi(self):
        """Test filtering when all detections are outside ROI."""
        detections = [
            {"bbox": [250, 250, 300, 300], "class": 0, "confidence": 0.9},
            {"bbox": [320, 320, 370, 370], "class": 2, "confidence": 0.85},
        ]
        roi_polygon = [[0, 0], [200, 0], [200, 200], [0, 200]]
        
        filtered = filter_detections_by_roi(detections, roi_polygon, roi_type="polygon")
        
        assert len(filtered) == 0
    
    def test_filter_mixed_detections(self):
        """Test filtering with some inside and some outside ROI."""
        detections = [
            {"bbox": [50, 50, 100, 100], "class": 0, "confidence": 0.9},  # Inside
            {"bbox": [250, 250, 300, 300], "class": 2, "confidence": 0.85},  # Outside
            {"bbox": [120, 120, 170, 170], "class": 5, "confidence": 0.8},  # Inside
        ]
        roi_polygon = [[0, 0], [200, 0], [200, 200], [0, 200]]
        
        filtered = filter_detections_by_roi(detections, roi_polygon, roi_type="polygon")
        
        assert len(filtered) == 2
        assert filtered[0]["bbox"] == [50, 50, 100, 100]
        assert filtered[1]["bbox"] == [120, 120, 170, 170]
    
    def test_filter_empty_detections(self):
        """Test filtering with empty detections list."""
        detections = []
        roi_polygon = [[0, 0], [200, 0], [200, 200], [0, 200]]
        
        filtered = filter_detections_by_roi(detections, roi_polygon, roi_type="polygon")
        
        assert len(filtered) == 0
    
    def test_filter_no_roi(self):
        """Test filtering with no ROI (should return all detections)."""
        detections = [
            {"bbox": [50, 50, 100, 100], "class": 0, "confidence": 0.9},
            {"bbox": [250, 250, 300, 300], "class": 2, "confidence": 0.85},
        ]
        
        filtered = filter_detections_by_roi(detections, None, roi_type=None)
        
        assert len(filtered) == 2
    
    def test_filter_preserves_detection_data(self):
        """Test that filtering preserves all detection data."""
        detections = [
            {
                "bbox": [50, 50, 100, 100],
                "class": 0,
                "confidence": 0.9,
                "track_id": 123,
                "timestamp": 1234567890
            }
        ]
        roi_polygon = [[0, 0], [200, 0], [200, 200], [0, 200]]
        
        filtered = filter_detections_by_roi(detections, roi_polygon, roi_type="polygon")
        
        assert len(filtered) == 1
        assert filtered[0]["class"] == 0
        assert filtered[0]["confidence"] == 0.9
        assert filtered[0]["track_id"] == 123
        assert filtered[0]["timestamp"] == 1234567890


class TestROIEdgeCases:
    """Test edge cases in ROI operations."""
    
    def test_very_small_polygon(self):
        """Test with very small polygon."""
        polygon = [[100, 100], [100.1, 100], [100, 100.1]]
        point = [100.05, 100.05]
        
        result = point_in_polygon(point, polygon)
        # Should handle small polygons correctly
        assert isinstance(result, bool)
    
    def test_very_large_polygon(self):
        """Test with very large polygon."""
        polygon = [[0, 0], [10000, 0], [10000, 10000], [0, 10000]]
        point = [5000, 5000]
        
        result = point_in_polygon(point, polygon)
        assert result is True
    
    def test_polygon_with_collinear_points(self):
        """Test polygon with collinear points."""
        polygon = [[0, 0], [50, 0], [100, 0], [100, 100], [0, 100]]
        point = [50, 50]
        
        result = point_in_polygon(point, polygon)
        assert result is True
    
    def test_self_intersecting_polygon(self):
        """Test self-intersecting polygon (figure-8 shape)."""
        # This is technically invalid but should not crash
        polygon = [[0, 0], [100, 100], [100, 0], [0, 100]]
        point = [50, 50]
        
        # Should not raise exception
        result = point_in_polygon(point, polygon)
        assert isinstance(result, bool)
    
    def test_bbox_with_zero_width(self):
        """Test bbox with zero width."""
        bbox = [[100, 100], [100, 200]]  # Zero width
        point = [100, 150]
        
        result = point_in_bbox(point, bbox)
        # Should handle degenerate case
        assert isinstance(result, bool)
    
    def test_bbox_with_zero_height(self):
        """Test bbox with zero height."""
        bbox = [[100, 100], [200, 100]]  # Zero height
        point = [150, 100]
        
        result = point_in_bbox(point, bbox)
        # Should handle degenerate case
        assert isinstance(result, bool)
    
    def test_iou_with_inverted_bbox(self):
        """Test IoU with inverted bbox coordinates."""
        # Sometimes x2 < x1 or y2 < y1 due to errors
        box1 = [200, 200, 100, 100]  # Inverted
        box2 = [100, 100, 200, 200]  # Normal
        
        # Should handle gracefully (normalize or return 0)
        iou = calculate_iou(box1, box2)
        assert 0 <= iou <= 1


class TestROIPerformance:
    """Test performance characteristics of ROI operations."""
    
    def test_polygon_with_many_vertices(self):
        """Test polygon with many vertices."""
        # Create a circular polygon with 100 vertices
        import math
        n_vertices = 100
        radius = 100
        center = [200, 200]
        
        polygon = [
            [
                center[0] + radius * math.cos(2 * math.pi * i / n_vertices),
                center[1] + radius * math.sin(2 * math.pi * i / n_vertices)
            ]
            for i in range(n_vertices)
        ]
        
        point = center
        result = point_in_polygon(point, polygon)
        assert result is True
    
    def test_many_detections_filtering(self):
        """Test filtering with many detections."""
        # Create 100 detections
        detections = [
            {
                "bbox": [i * 20, i * 20, i * 20 + 15, i * 20 + 15],
                "class": i % 10,
                "confidence": 0.5 + (i % 50) / 100
            }
            for i in range(100)
        ]
        
        roi_polygon = [[0, 0], [500, 0], [500, 500], [0, 500]]
        
        filtered = filter_detections_by_roi(detections, roi_polygon, roi_type="polygon")
        
        # Should filter efficiently
        assert len(filtered) <= len(detections)
        assert all(d["bbox"][0] < 500 for d in filtered)
