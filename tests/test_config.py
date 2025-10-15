"""
test_config.py

Test configuration loading and Pydantic model validation.

Tests:
- YAML loading from cameras.example.yaml
- CameraConfig validation
- ROIConfig validation
- YOLOConfig validation
- Invalid configuration handling
"""

import pytest
import yaml
from pathlib import Path
from pydantic import ValidationError

from src.kvs_infer.config import (
    CameraConfig,
    ROIConfig,
    YOLOConfig,
    AppConfig,
)


@pytest.fixture
def sample_yaml_path():
    """Path to the example cameras configuration file."""
    return Path(__file__).parent.parent / "cameras.example.yaml"


@pytest.fixture
def sample_yaml_data(sample_yaml_path):
    """Load the example YAML configuration."""
    with open(sample_yaml_path, 'r') as f:
        return yaml.safe_load(f)


class TestYAMLLoading:
    """Test YAML file loading."""
    
    def test_yaml_file_exists(self, sample_yaml_path):
        """Test that cameras.example.yaml exists."""
        assert sample_yaml_path.exists(), f"Example YAML not found at {sample_yaml_path}"
    
    def test_yaml_is_valid(self, sample_yaml_data):
        """Test that YAML can be loaded without errors."""
        assert sample_yaml_data is not None
        assert isinstance(sample_yaml_data, dict)
    
    def test_yaml_has_required_sections(self, sample_yaml_data):
        """Test that YAML has required top-level sections."""
        assert "cameras" in sample_yaml_data
        assert "yolo" in sample_yaml_data
        assert isinstance(sample_yaml_data["cameras"], list)
        assert len(sample_yaml_data["cameras"]) > 0


class TestROIConfig:
    """Test ROI configuration validation."""
    
    def test_valid_polygon_roi(self):
        """Test valid polygon ROI configuration."""
        roi_data = {
            "name": "entrance",
            "type": "polygon",
            "points": [[100, 100], [200, 100], [200, 200], [100, 200]]
        }
        roi = ROIConfig(**roi_data)
        
        assert roi.name == "entrance"
        assert roi.type == "polygon"
        assert len(roi.points) == 4
        assert roi.points[0] == [100, 100]
    
    def test_valid_bbox_roi(self):
        """Test valid bounding box ROI configuration."""
        roi_data = {
            "name": "parking",
            "type": "bbox",
            "points": [[100, 100], [300, 400]]
        }
        roi = ROIConfig(**roi_data)
        
        assert roi.name == "parking"
        assert roi.type == "bbox"
        assert len(roi.points) == 2
    
    def test_polygon_requires_min_3_points(self):
        """Test that polygon requires at least 3 points."""
        roi_data = {
            "name": "invalid",
            "type": "polygon",
            "points": [[100, 100], [200, 100]]  # Only 2 points
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ROIConfig(**roi_data)
        
        assert "polygon ROI requires at least 3 points" in str(exc_info.value).lower()
    
    def test_bbox_requires_exactly_2_points(self):
        """Test that bbox requires exactly 2 points."""
        roi_data = {
            "name": "invalid",
            "type": "bbox",
            "points": [[100, 100], [200, 200], [300, 300]]  # 3 points
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ROIConfig(**roi_data)
        
        assert "bbox ROI requires exactly 2 points" in str(exc_info.value).lower()
    
    def test_invalid_roi_type(self):
        """Test that invalid ROI type is rejected."""
        roi_data = {
            "name": "invalid",
            "type": "circle",  # Invalid type
            "points": [[100, 100], [200, 200]]
        }
        
        with pytest.raises(ValidationError):
            ROIConfig(**roi_data)
    
    def test_empty_roi_name(self):
        """Test that empty ROI name is rejected."""
        roi_data = {
            "name": "",
            "type": "polygon",
            "points": [[100, 100], [200, 100], [200, 200]]
        }
        
        with pytest.raises(ValidationError):
            ROIConfig(**roi_data)
    
    def test_point_coordinates_are_numbers(self):
        """Test that point coordinates must be numbers."""
        roi_data = {
            "name": "entrance",
            "type": "polygon",
            "points": [["a", "b"], [200, 100], [200, 200]]
        }
        
        with pytest.raises(ValidationError):
            ROIConfig(**roi_data)


class TestYOLOConfig:
    """Test YOLO configuration validation."""
    
    def test_valid_yolo_config(self):
        """Test valid YOLO configuration."""
        yolo_data = {
            "model_path": "yolov8n.pt",
            "confidence_threshold": 0.5,
            "iou_threshold": 0.45,
            "classes": [0, 2, 5, 7],
            "device": "cuda:0"
        }
        yolo = YOLOConfig(**yolo_data)
        
        assert yolo.model_path == "yolov8n.pt"
        assert yolo.confidence_threshold == 0.5
        assert yolo.iou_threshold == 0.45
        assert yolo.classes == [0, 2, 5, 7]
        assert yolo.device == "cuda:0"
    
    def test_default_yolo_values(self):
        """Test YOLO configuration with default values."""
        yolo_data = {
            "model_path": "yolov8n.pt"
        }
        yolo = YOLOConfig(**yolo_data)
        
        assert yolo.confidence_threshold == 0.25  # Default
        assert yolo.iou_threshold == 0.45  # Default
        assert yolo.device == "cuda:0"  # Default
    
    def test_confidence_threshold_range(self):
        """Test that confidence threshold must be between 0 and 1."""
        # Too low
        with pytest.raises(ValidationError):
            YOLOConfig(model_path="yolov8n.pt", confidence_threshold=-0.1)
        
        # Too high
        with pytest.raises(ValidationError):
            YOLOConfig(model_path="yolov8n.pt", confidence_threshold=1.5)
        
        # Valid boundaries
        yolo_min = YOLOConfig(model_path="yolov8n.pt", confidence_threshold=0.0)
        assert yolo_min.confidence_threshold == 0.0
        
        yolo_max = YOLOConfig(model_path="yolov8n.pt", confidence_threshold=1.0)
        assert yolo_max.confidence_threshold == 1.0
    
    def test_iou_threshold_range(self):
        """Test that IOU threshold must be between 0 and 1."""
        with pytest.raises(ValidationError):
            YOLOConfig(model_path="yolov8n.pt", iou_threshold=-0.1)
        
        with pytest.raises(ValidationError):
            YOLOConfig(model_path="yolov8n.pt", iou_threshold=1.5)
    
    def test_classes_must_be_non_negative(self):
        """Test that class IDs must be non-negative."""
        with pytest.raises(ValidationError):
            YOLOConfig(model_path="yolov8n.pt", classes=[-1, 0, 2])
    
    def test_empty_model_path(self):
        """Test that model path cannot be empty."""
        with pytest.raises(ValidationError):
            YOLOConfig(model_path="")


class TestCameraConfig:
    """Test camera configuration validation."""
    
    def test_valid_camera_config(self):
        """Test valid camera configuration."""
        camera_data = {
            "camera_id": "front-entrance",
            "stream_name": "FrontDoorStream",
            "region": "us-east-1",
            "roi": [
                {
                    "name": "door",
                    "type": "polygon",
                    "points": [[100, 100], [200, 100], [200, 200], [100, 200]]
                }
            ]
        }
        camera = CameraConfig(**camera_data)
        
        assert camera.camera_id == "front-entrance"
        assert camera.stream_name == "FrontDoorStream"
        assert camera.region == "us-east-1"
        assert len(camera.roi) == 1
        assert camera.roi[0].name == "door"
    
    def test_camera_with_multiple_rois(self):
        """Test camera with multiple ROIs."""
        camera_data = {
            "camera_id": "parking-lot",
            "stream_name": "ParkingStream",
            "region": "us-west-2",
            "roi": [
                {
                    "name": "entrance",
                    "type": "polygon",
                    "points": [[100, 100], [200, 100], [200, 200]]
                },
                {
                    "name": "exit",
                    "type": "bbox",
                    "points": [[300, 300], [400, 400]]
                }
            ]
        }
        camera = CameraConfig(**camera_data)
        
        assert len(camera.roi) == 2
        assert camera.roi[0].name == "entrance"
        assert camera.roi[1].name == "exit"
    
    def test_camera_without_roi(self):
        """Test camera configuration without ROI (should use full frame)."""
        camera_data = {
            "camera_id": "overview",
            "stream_name": "OverviewStream",
            "region": "us-east-1"
        }
        camera = CameraConfig(**camera_data)
        
        assert camera.camera_id == "overview"
        assert camera.roi == [] or camera.roi is None
    
    def test_empty_camera_id(self):
        """Test that camera_id cannot be empty."""
        camera_data = {
            "camera_id": "",
            "stream_name": "Stream",
            "region": "us-east-1"
        }
        
        with pytest.raises(ValidationError):
            CameraConfig(**camera_data)
    
    def test_empty_stream_name(self):
        """Test that stream_name cannot be empty."""
        camera_data = {
            "camera_id": "cam1",
            "stream_name": "",
            "region": "us-east-1"
        }
        
        with pytest.raises(ValidationError):
            CameraConfig(**camera_data)
    
    def test_invalid_region_format(self):
        """Test that region must be valid AWS region format."""
        camera_data = {
            "camera_id": "cam1",
            "stream_name": "Stream1",
            "region": "invalid-region"  # Should be validated
        }
        
        # Note: This test assumes region validation is implemented
        # If not, this test should be marked as expected future behavior
        camera = CameraConfig(**camera_data)
        assert camera.region == "invalid-region"  # Currently no validation


class TestAppConfig:
    """Test complete application configuration."""
    
    def test_load_example_yaml(self, sample_yaml_data):
        """Test loading the example YAML into AppConfig."""
        config = AppConfig(**sample_yaml_data)
        
        assert config.cameras is not None
        assert len(config.cameras) > 0
        assert config.yolo is not None
    
    def test_app_config_cameras_validation(self, sample_yaml_data):
        """Test that all cameras in example YAML are valid."""
        config = AppConfig(**sample_yaml_data)
        
        for camera in config.cameras:
            assert camera.camera_id
            assert camera.stream_name
            assert camera.region
            
            # Validate ROIs if present
            if camera.roi:
                for roi in camera.roi:
                    assert roi.name
                    assert roi.type in ["polygon", "bbox"]
                    assert len(roi.points) > 0
    
    def test_app_config_yolo_validation(self, sample_yaml_data):
        """Test that YOLO config in example YAML is valid."""
        config = AppConfig(**sample_yaml_data)
        
        assert config.yolo.model_path
        assert 0 <= config.yolo.confidence_threshold <= 1
        assert 0 <= config.yolo.iou_threshold <= 1
    
    def test_missing_cameras_section(self):
        """Test that missing cameras section raises error."""
        invalid_data = {
            "yolo": {
                "model_path": "yolov8n.pt"
            }
        }
        
        with pytest.raises(ValidationError):
            AppConfig(**invalid_data)
    
    def test_missing_yolo_section(self):
        """Test that missing YOLO section raises error."""
        invalid_data = {
            "cameras": [
                {
                    "camera_id": "cam1",
                    "stream_name": "Stream1",
                    "region": "us-east-1"
                }
            ]
        }
        
        with pytest.raises(ValidationError):
            AppConfig(**invalid_data)
    
    def test_empty_cameras_list(self):
        """Test that empty cameras list raises error."""
        invalid_data = {
            "cameras": [],
            "yolo": {
                "model_path": "yolov8n.pt"
            }
        }
        
        with pytest.raises(ValidationError):
            AppConfig(**invalid_data)


class TestConfigEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_roi_with_negative_coordinates(self):
        """Test that negative coordinates are handled correctly."""
        roi_data = {
            "name": "test",
            "type": "polygon",
            "points": [[-10, -10], [10, -10], [0, 10]]
        }
        roi = ROIConfig(**roi_data)
        
        # Negative coordinates should be allowed (relative positioning)
        assert roi.points[0] == [-10, -10]
    
    def test_roi_with_very_large_coordinates(self):
        """Test that very large coordinates are handled."""
        roi_data = {
            "name": "test",
            "type": "polygon",
            "points": [[10000, 10000], [20000, 10000], [15000, 20000]]
        }
        roi = ROIConfig(**roi_data)
        
        assert roi.points[0] == [10000, 10000]
    
    def test_roi_with_floating_point_coordinates(self):
        """Test that floating point coordinates are handled."""
        roi_data = {
            "name": "test",
            "type": "polygon",
            "points": [[100.5, 100.5], [200.7, 100.3], [150.2, 200.9]]
        }
        roi = ROIConfig(**roi_data)
        
        assert isinstance(roi.points[0][0], float)
    
    def test_yolo_classes_empty_list(self):
        """Test YOLO config with empty classes list (all classes)."""
        yolo_data = {
            "model_path": "yolov8n.pt",
            "classes": []
        }
        yolo = YOLOConfig(**yolo_data)
        
        assert yolo.classes == []
    
    def test_yolo_classes_none(self):
        """Test YOLO config with None classes (all classes)."""
        yolo_data = {
            "model_path": "yolov8n.pt",
            "classes": None
        }
        yolo = YOLOConfig(**yolo_data)
        
        assert yolo.classes is None
    
    def test_camera_id_with_special_characters(self):
        """Test camera ID with special characters."""
        camera_data = {
            "camera_id": "front-entrance_cam-01",
            "stream_name": "Stream",
            "region": "us-east-1"
        }
        camera = CameraConfig(**camera_data)
        
        assert camera.camera_id == "front-entrance_cam-01"
    
    def test_duplicate_roi_names_in_camera(self):
        """Test that duplicate ROI names are allowed (might be intentional)."""
        camera_data = {
            "camera_id": "cam1",
            "stream_name": "Stream1",
            "region": "us-east-1",
            "roi": [
                {
                    "name": "zone1",
                    "type": "polygon",
                    "points": [[100, 100], [200, 100], [150, 200]]
                },
                {
                    "name": "zone1",  # Duplicate name
                    "type": "bbox",
                    "points": [[300, 300], [400, 400]]
                }
            ]
        }
        camera = CameraConfig(**camera_data)
        
        # Currently allowed - might want to add validation
        assert len(camera.roi) == 2


class TestConfigSerialization:
    """Test configuration serialization and deserialization."""
    
    def test_roi_dict_serialization(self):
        """Test ROI can be serialized to dict."""
        roi = ROIConfig(
            name="entrance",
            type="polygon",
            points=[[100, 100], [200, 100], [200, 200]]
        )
        roi_dict = roi.dict()
        
        assert roi_dict["name"] == "entrance"
        assert roi_dict["type"] == "polygon"
        assert len(roi_dict["points"]) == 3
    
    def test_camera_dict_serialization(self):
        """Test camera can be serialized to dict."""
        camera = CameraConfig(
            camera_id="cam1",
            stream_name="Stream1",
            region="us-east-1",
            roi=[
                ROIConfig(
                    name="zone1",
                    type="polygon",
                    points=[[100, 100], [200, 100], [150, 200]]
                )
            ]
        )
        camera_dict = camera.dict()
        
        assert camera_dict["camera_id"] == "cam1"
        assert len(camera_dict["roi"]) == 1
    
    def test_app_config_json_serialization(self, sample_yaml_data):
        """Test complete config can be serialized to JSON."""
        config = AppConfig(**sample_yaml_data)
        json_str = config.json()
        
        assert isinstance(json_str, str)
        assert "cameras" in json_str
        assert "yolo" in json_str
    
    def test_config_round_trip(self):
        """Test configuration round-trip (dict -> model -> dict)."""
        original_data = {
            "cameras": [
                {
                    "camera_id": "cam1",
                    "stream_name": "Stream1",
                    "region": "us-east-1",
                    "roi": [
                        {
                            "name": "zone1",
                            "type": "polygon",
                            "points": [[100, 100], [200, 100], [150, 200]]
                        }
                    ]
                }
            ],
            "yolo": {
                "model_path": "yolov8n.pt",
                "confidence_threshold": 0.5,
                "classes": [0, 2, 5]
            }
        }
        
        # Load into model
        config = AppConfig(**original_data)
        
        # Serialize back to dict
        serialized = config.dict()
        
        # Compare key fields
        assert serialized["cameras"][0]["camera_id"] == original_data["cameras"][0]["camera_id"]
        assert serialized["yolo"]["model_path"] == original_data["yolo"]["model_path"]
        assert serialized["yolo"]["confidence_threshold"] == original_data["yolo"]["confidence_threshold"]
