"""Detector modules for various inference tasks."""

from kvs_infer.detectors.base import Detector, DetectorRegistry

# Import detector implementations to trigger registration
from kvs_infer.detectors import weapon
from kvs_infer.detectors import fire_smoke
from kvs_infer.detectors import alpr

# Register Roboflow detector - lazy import to avoid circular dependency
def _register_roboflow():
    from kvs_infer.detectors.roboflow_gun_detector import RoboflowGunDetector
    DetectorRegistry._registry['roboflow_gun'] = RoboflowGunDetector
    return RoboflowGunDetector

# Register on first use
_register_roboflow()

__all__ = ["Detector", "DetectorRegistry"]
