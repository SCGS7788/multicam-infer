"""
conftest.py

Pytest configuration and shared fixtures.
"""

import pytest
import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """Get test data directory."""
    return project_root / "tests" / "data"


@pytest.fixture
def mock_frame():
    """Create a mock video frame."""
    import numpy as np
    return np.zeros((640, 640, 3), dtype=np.uint8)


@pytest.fixture
def sample_camera_config():
    """Sample camera configuration."""
    return {
        "camera_id": "test-camera",
        "stream_name": "TestStream",
        "region": "us-east-1",
        "roi": [
            {
                "name": "test-zone",
                "type": "polygon",
                "points": [[100, 100], [200, 100], [200, 200], [100, 200]]
            }
        ]
    }


@pytest.fixture
def sample_yolo_config():
    """Sample YOLO configuration."""
    return {
        "model_path": "yolov8n.pt",
        "confidence_threshold": 0.5,
        "iou_threshold": 0.45,
        "classes": [0, 2, 5, 7],
        "device": "cpu"  # Use CPU for tests
    }


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks after each test."""
    yield
    # Cleanup code here if needed
