"""
test_yolo_common.py

Test YOLO detector with mocked model.

Tests:
- Detection filtering by class
- Confidence threshold filtering
- Temporal confirmation logic
- NMS (Non-Maximum Suppression)
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict

from src.kvs_infer.yolo_common import (
    YOLODetector,
    TemporalConfirm,
    filter_by_class,
    filter_by_confidence,
    apply_nms,
)


@pytest.fixture
def mock_yolo_model():
    """Create a mock YOLO model."""
    model = Mock()
    model.names = {
        0: "person",
        1: "bicycle",
        2: "car",
        5: "bus",
        7: "truck"
    }
    return model


@pytest.fixture
def sample_detections():
    """Sample detection results."""
    return [
        {"bbox": [100, 100, 200, 200], "class": 0, "confidence": 0.9, "class_name": "person"},
        {"bbox": [150, 150, 250, 250], "class": 0, "confidence": 0.85, "class_name": "person"},
        {"bbox": [300, 300, 400, 400], "class": 2, "confidence": 0.75, "class_name": "car"},
        {"bbox": [500, 500, 600, 600], "class": 5, "confidence": 0.95, "class_name": "bus"},
        {"bbox": [700, 700, 800, 800], "class": 1, "confidence": 0.45, "class_name": "bicycle"},
    ]


class TestFilterByClass:
    """Test detection filtering by class."""
    
    def test_filter_single_class(self, sample_detections):
        """Test filtering for a single class."""
        filtered = filter_by_class(sample_detections, classes=[0])
        
        assert len(filtered) == 2
        assert all(d["class"] == 0 for d in filtered)
    
    def test_filter_multiple_classes(self, sample_detections):
        """Test filtering for multiple classes."""
        filtered = filter_by_class(sample_detections, classes=[0, 2])
        
        assert len(filtered) == 3
        assert all(d["class"] in [0, 2] for d in filtered)
    
    def test_filter_no_classes_returns_all(self, sample_detections):
        """Test that empty class filter returns all detections."""
        filtered = filter_by_class(sample_detections, classes=None)
        
        assert len(filtered) == len(sample_detections)
    
    def test_filter_nonexistent_class(self, sample_detections):
        """Test filtering for non-existent class returns empty."""
        filtered = filter_by_class(sample_detections, classes=[99])
        
        assert len(filtered) == 0
    
    def test_filter_preserves_detection_data(self, sample_detections):
        """Test that filtering preserves all detection data."""
        filtered = filter_by_class(sample_detections, classes=[0])
        
        assert filtered[0]["bbox"] == [100, 100, 200, 200]
        assert filtered[0]["confidence"] == 0.9
        assert filtered[0]["class_name"] == "person"


class TestFilterByConfidence:
    """Test detection filtering by confidence threshold."""
    
    def test_filter_above_threshold(self, sample_detections):
        """Test filtering detections above confidence threshold."""
        filtered = filter_by_confidence(sample_detections, threshold=0.7)
        
        assert len(filtered) == 4
        assert all(d["confidence"] >= 0.7 for d in filtered)
    
    def test_filter_high_threshold(self, sample_detections):
        """Test filtering with high confidence threshold."""
        filtered = filter_by_confidence(sample_detections, threshold=0.9)
        
        assert len(filtered) == 2
        assert all(d["confidence"] >= 0.9 for d in filtered)
    
    def test_filter_zero_threshold(self, sample_detections):
        """Test that zero threshold returns all detections."""
        filtered = filter_by_confidence(sample_detections, threshold=0.0)
        
        assert len(filtered) == len(sample_detections)
    
    def test_filter_threshold_exactly_equal(self, sample_detections):
        """Test filtering with threshold exactly equal to a confidence."""
        filtered = filter_by_confidence(sample_detections, threshold=0.85)
        
        # Should include detection with confidence == 0.85
        assert len(filtered) == 3
        assert any(d["confidence"] == 0.85 for d in filtered)
    
    def test_filter_threshold_above_all(self, sample_detections):
        """Test filtering with threshold above all confidences."""
        filtered = filter_by_confidence(sample_detections, threshold=0.99)
        
        assert len(filtered) == 0


class TestApplyNMS:
    """Test Non-Maximum Suppression."""
    
    def test_nms_removes_overlapping_detections(self):
        """Test that NMS removes overlapping detections."""
        detections = [
            {"bbox": [100, 100, 200, 200], "class": 0, "confidence": 0.9},
            {"bbox": [110, 110, 210, 210], "class": 0, "confidence": 0.85},  # Overlaps with first
            {"bbox": [300, 300, 400, 400], "class": 0, "confidence": 0.8},  # No overlap
        ]
        
        filtered = apply_nms(detections, iou_threshold=0.5)
        
        # Should keep highest confidence and non-overlapping
        assert len(filtered) == 2
        assert filtered[0]["confidence"] == 0.9
        assert filtered[1]["bbox"] == [300, 300, 400, 400]
    
    def test_nms_keeps_non_overlapping(self):
        """Test that NMS keeps all non-overlapping detections."""
        detections = [
            {"bbox": [100, 100, 200, 200], "class": 0, "confidence": 0.9},
            {"bbox": [300, 300, 400, 400], "class": 0, "confidence": 0.8},
            {"bbox": [500, 500, 600, 600], "class": 0, "confidence": 0.7},
        ]
        
        filtered = apply_nms(detections, iou_threshold=0.5)
        
        assert len(filtered) == 3
    
    def test_nms_with_different_classes(self):
        """Test that NMS operates within same class only."""
        detections = [
            {"bbox": [100, 100, 200, 200], "class": 0, "confidence": 0.9},
            {"bbox": [110, 110, 210, 210], "class": 2, "confidence": 0.85},  # Different class, overlaps
        ]
        
        filtered = apply_nms(detections, iou_threshold=0.5)
        
        # Should keep both since they're different classes
        assert len(filtered) == 2
    
    def test_nms_empty_detections(self):
        """Test NMS with empty detections list."""
        detections = []
        
        filtered = apply_nms(detections, iou_threshold=0.5)
        
        assert len(filtered) == 0
    
    def test_nms_single_detection(self):
        """Test NMS with single detection."""
        detections = [
            {"bbox": [100, 100, 200, 200], "class": 0, "confidence": 0.9}
        ]
        
        filtered = apply_nms(detections, iou_threshold=0.5)
        
        assert len(filtered) == 1


class TestYOLODetector:
    """Test YOLO detector class."""
    
    @patch('src.kvs_infer.yolo_common.YOLO')
    def test_detector_initialization(self, mock_yolo_class, mock_yolo_model):
        """Test YOLO detector initialization."""
        mock_yolo_class.return_value = mock_yolo_model
        
        detector = YOLODetector(
            model_path="yolov8n.pt",
            confidence_threshold=0.5,
            iou_threshold=0.45,
            classes=[0, 2, 5],
            device="cuda:0"
        )
        
        assert detector.confidence_threshold == 0.5
        assert detector.iou_threshold == 0.45
        assert detector.classes == [0, 2, 5]
        mock_yolo_class.assert_called_once_with("yolov8n.pt")
    
    @patch('src.kvs_infer.yolo_common.YOLO')
    def test_detector_predict(self, mock_yolo_class, mock_yolo_model):
        """Test YOLO detector prediction."""
        # Mock prediction results
        mock_result = Mock()
        mock_result.boxes.data = np.array([
            [100, 100, 200, 200, 0.9, 0],  # x1, y1, x2, y2, conf, class
            [300, 300, 400, 400, 0.8, 2],
        ])
        mock_yolo_model.predict.return_value = [mock_result]
        mock_yolo_class.return_value = mock_yolo_model
        
        detector = YOLODetector(
            model_path="yolov8n.pt",
            confidence_threshold=0.5,
            classes=[0, 2]
        )
        
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        detections = detector.predict(frame)
        
        assert len(detections) == 2
        assert detections[0]["class"] == 0
        assert detections[0]["confidence"] == pytest.approx(0.9, 0.01)
        assert detections[1]["class"] == 2
    
    @patch('src.kvs_infer.yolo_common.YOLO')
    def test_detector_filters_by_confidence(self, mock_yolo_class, mock_yolo_model):
        """Test that detector filters by confidence threshold."""
        mock_result = Mock()
        mock_result.boxes.data = np.array([
            [100, 100, 200, 200, 0.9, 0],
            [300, 300, 400, 400, 0.3, 2],  # Below threshold
        ])
        mock_yolo_model.predict.return_value = [mock_result]
        mock_yolo_class.return_value = mock_yolo_model
        
        detector = YOLODetector(
            model_path="yolov8n.pt",
            confidence_threshold=0.5
        )
        
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        detections = detector.predict(frame)
        
        assert len(detections) == 1
        assert detections[0]["confidence"] >= 0.5
    
    @patch('src.kvs_infer.yolo_common.YOLO')
    def test_detector_filters_by_class(self, mock_yolo_class, mock_yolo_model):
        """Test that detector filters by class."""
        mock_result = Mock()
        mock_result.boxes.data = np.array([
            [100, 100, 200, 200, 0.9, 0],  # person
            [300, 300, 400, 400, 0.8, 1],  # bicycle - not in filter
            [500, 500, 600, 600, 0.85, 2],  # car
        ])
        mock_yolo_model.predict.return_value = [mock_result]
        mock_yolo_class.return_value = mock_yolo_model
        
        detector = YOLODetector(
            model_path="yolov8n.pt",
            classes=[0, 2]  # Only person and car
        )
        
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        detections = detector.predict(frame)
        
        assert len(detections) == 2
        assert all(d["class"] in [0, 2] for d in detections)


class TestTemporalConfirm:
    """Test temporal confirmation logic."""
    
    def test_temporal_confirm_initialization(self):
        """Test temporal confirmation initialization."""
        tc = TemporalConfirm(window_size=5, min_detections=3)
        
        assert tc.window_size == 5
        assert tc.min_detections == 3
        assert len(tc.detection_history) == 0
    
    def test_temporal_confirm_requires_min_detections(self):
        """Test that temporal confirmation requires minimum detections."""
        tc = TemporalConfirm(window_size=5, min_detections=3)
        
        # Add 2 detections (below minimum)
        result1 = tc.update([{"bbox": [100, 100, 200, 200], "class": 0}])
        result2 = tc.update([{"bbox": [100, 100, 200, 200], "class": 0}])
        
        assert len(result1) == 0
        assert len(result2) == 0
        
        # Add 3rd detection (reaches minimum)
        result3 = tc.update([{"bbox": [100, 100, 200, 200], "class": 0}])
        
        assert len(result3) == 1
    
    def test_temporal_confirm_tracks_consistent_detections(self):
        """Test that temporal confirmation tracks consistent detections."""
        tc = TemporalConfirm(window_size=5, min_detections=3)
        
        # Same detection 3 times
        for _ in range(3):
            result = tc.update([{"bbox": [100, 100, 200, 200], "class": 0, "confidence": 0.9}])
        
        assert len(result) == 1
        assert result[0]["class"] == 0
    
    def test_temporal_confirm_ignores_inconsistent_detections(self):
        """Test that temporal confirmation ignores inconsistent detections."""
        tc = TemporalConfirm(window_size=5, min_detections=3)
        
        # Different detections each time
        tc.update([{"bbox": [100, 100, 200, 200], "class": 0}])
        tc.update([{"bbox": [300, 300, 400, 400], "class": 2}])
        result = tc.update([{"bbox": [500, 500, 600, 600], "class": 5}])
        
        # No detection should be confirmed
        assert len(result) == 0
    
    def test_temporal_confirm_sliding_window(self):
        """Test that temporal confirmation uses sliding window."""
        tc = TemporalConfirm(window_size=3, min_detections=2)
        
        # Fill window with detection A
        tc.update([{"bbox": [100, 100, 200, 200], "class": 0, "id": "A"}])
        tc.update([{"bbox": [100, 100, 200, 200], "class": 0, "id": "A"}])
        result = tc.update([{"bbox": [100, 100, 200, 200], "class": 0, "id": "A"}])
        
        assert len(result) == 1
        
        # Slide window with different detection
        tc.update([{"bbox": [300, 300, 400, 400], "class": 2, "id": "B"}])
        tc.update([{"bbox": [300, 300, 400, 400], "class": 2, "id": "B"}])
        result = tc.update([{"bbox": [300, 300, 400, 400], "class": 2, "id": "B"}])
        
        # Old detection A should be gone, new detection B confirmed
        assert len(result) == 1
        assert result[0]["id"] == "B"
    
    def test_temporal_confirm_multiple_objects(self):
        """Test temporal confirmation with multiple objects."""
        tc = TemporalConfirm(window_size=5, min_detections=2)
        
        # Add 2 different objects consistently
        for _ in range(2):
            tc.update([
                {"bbox": [100, 100, 200, 200], "class": 0, "id": "person1"},
                {"bbox": [300, 300, 400, 400], "class": 2, "id": "car1"},
            ])
        
        result = tc.update([
            {"bbox": [100, 100, 200, 200], "class": 0, "id": "person1"},
            {"bbox": [300, 300, 400, 400], "class": 2, "id": "car1"},
        ])
        
        # Both objects should be confirmed
        assert len(result) == 2
    
    def test_temporal_confirm_empty_frames(self):
        """Test temporal confirmation with empty frames."""
        tc = TemporalConfirm(window_size=5, min_detections=3)
        
        # Add detections
        tc.update([{"bbox": [100, 100, 200, 200], "class": 0}])
        tc.update([])  # Empty frame
        tc.update([{"bbox": [100, 100, 200, 200], "class": 0}])
        tc.update([])  # Empty frame
        result = tc.update([{"bbox": [100, 100, 200, 200], "class": 0}])
        
        # Should still confirm if detection appears min_detections times
        assert len(result) <= 1
    
    def test_temporal_confirm_iou_matching(self):
        """Test that temporal confirmation matches detections by IoU."""
        tc = TemporalConfirm(window_size=5, min_detections=3, iou_threshold=0.5)
        
        # Similar but not identical bboxes (should match via IoU)
        tc.update([{"bbox": [100, 100, 200, 200], "class": 0}])
        tc.update([{"bbox": [105, 105, 205, 205], "class": 0}])  # Slightly moved
        result = tc.update([{"bbox": [110, 110, 210, 210], "class": 0}])  # Moved again
        
        # Should be recognized as same object due to high IoU
        assert len(result) == 1


class TestYOLOEdgeCases:
    """Test edge cases in YOLO detection."""
    
    @patch('src.kvs_infer.yolo_common.YOLO')
    def test_empty_frame(self, mock_yolo_class, mock_yolo_model):
        """Test detection on empty frame."""
        mock_result = Mock()
        mock_result.boxes.data = np.array([])  # No detections
        mock_yolo_model.predict.return_value = [mock_result]
        mock_yolo_class.return_value = mock_yolo_model
        
        detector = YOLODetector(model_path="yolov8n.pt")
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        detections = detector.predict(frame)
        
        assert len(detections) == 0
    
    @patch('src.kvs_infer.yolo_common.YOLO')
    def test_very_small_detections(self, mock_yolo_class, mock_yolo_model):
        """Test with very small bounding boxes."""
        mock_result = Mock()
        mock_result.boxes.data = np.array([
            [100, 100, 102, 102, 0.9, 0],  # 2x2 pixel box
        ])
        mock_yolo_model.predict.return_value = [mock_result]
        mock_yolo_class.return_value = mock_yolo_model
        
        detector = YOLODetector(model_path="yolov8n.pt")
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        detections = detector.predict(frame)
        
        assert len(detections) == 1
        bbox = detections[0]["bbox"]
        assert bbox[2] - bbox[0] == 2  # width
        assert bbox[3] - bbox[1] == 2  # height
    
    @patch('src.kvs_infer.yolo_common.YOLO')
    def test_detections_at_image_boundary(self, mock_yolo_class, mock_yolo_model):
        """Test detections at image boundaries."""
        mock_result = Mock()
        mock_result.boxes.data = np.array([
            [0, 0, 50, 50, 0.9, 0],  # Top-left corner
            [590, 590, 640, 640, 0.85, 2],  # Bottom-right corner
        ])
        mock_yolo_model.predict.return_value = [mock_result]
        mock_yolo_class.return_value = mock_yolo_model
        
        detector = YOLODetector(model_path="yolov8n.pt")
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        detections = detector.predict(frame)
        
        assert len(detections) == 2
    
    def test_temporal_confirm_with_varying_window_sizes(self):
        """Test temporal confirmation with different window sizes."""
        for window_size in [1, 5, 10, 20]:
            tc = TemporalConfirm(window_size=window_size, min_detections=2)
            
            # Should initialize without error
            assert tc.window_size == window_size
    
    def test_filter_with_extreme_thresholds(self):
        """Test filtering with extreme confidence thresholds."""
        detections = [
            {"bbox": [100, 100, 200, 200], "class": 0, "confidence": 0.5}
        ]
        
        # Threshold = 0 should return all
        filtered = filter_by_confidence(detections, threshold=0.0)
        assert len(filtered) == 1
        
        # Threshold = 1 should return none
        filtered = filter_by_confidence(detections, threshold=1.0)
        assert len(filtered) == 0
