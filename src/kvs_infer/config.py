"""
Configuration management using Pydantic models.
Loads and validates YAML configuration files with environment variable expansion.
"""

import logging
import os
import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class DetectorType(str, Enum):
    """Available detector types."""
    WEAPON = "weapon"
    FIRE_SMOKE = "fire_smoke"
    ALPR = "alpr"


class PlaybackMode(str, Enum):
    """KVS playback modes."""
    HLS = "HLS"
    GETMEDIA = "GETMEDIA"  # Future: low-latency


class OCREngine(str, Enum):
    """OCR engine options."""
    PADDLEOCR = "paddleocr"
    TESSERACT = "tesseract"


# ============================================================================
# Global Configuration
# ============================================================================

class AWSConfig(BaseModel):
    """AWS-specific configuration."""
    region: str = Field(default="us-east-1", description="Default AWS region")


class GlobalPublishersConfig(BaseModel):
    """Global publisher configuration."""
    kds_stream: Optional[str] = Field(default=None, description="Default Kinesis Data Stream name")
    s3_bucket: Optional[str] = Field(default=None, description="Default S3 bucket for snapshots")
    ddb_table: Optional[str] = Field(default=None, description="Default DynamoDB table for metadata")


class ServiceConfig(BaseModel):
    """Service-level configuration."""
    hls_session_seconds: int = Field(
        default=300,
        ge=60,
        le=43200,
        description="HLS session duration in seconds (max 12 hours)"
    )
    reconnect_delay_seconds: int = Field(
        default=5,
        ge=1,
        le=300,
        description="Delay before reconnecting on error"
    )


class SnapshotsConfig(BaseModel):
    """Global snapshots configuration."""
    enabled: bool = Field(default=True, description="Enable snapshot uploads")
    jpeg_quality: int = Field(default=90, ge=1, le=100, description="JPEG compression quality")
    image_format: Literal["jpg", "png"] = Field(default="jpg", description="Image format")


# ============================================================================
# Camera-specific Configuration
# ============================================================================

class PlaybackConfig(BaseModel):
    """KVS playback configuration."""
    mode: PlaybackMode = Field(default=PlaybackMode.HLS, description="Playback mode")
    retention_required: bool = Field(
        default=True,
        description="Require data retention for HLS playback"
    )


class ResizeConfig(BaseModel):
    """Frame resize configuration."""
    width: int = Field(gt=0, le=3840, description="Target width in pixels")
    height: int = Field(gt=0, le=2160, description="Target height in pixels")
    
    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v):
        if v % 2 != 0:
            raise ValueError("Width and height must be even numbers for video encoding")
        return v


class ROIPolygon(BaseModel):
    """Region of Interest polygon."""
    name: Optional[str] = Field(default=None, description="ROI name for identification")
    points: List[List[int]] = Field(description="Polygon vertices [[x1,y1], [x2,y2], ...]")
    
    @field_validator("points")
    @classmethod
    def validate_points(cls, v):
        if len(v) < 3:
            raise ValueError("ROI polygon must have at least 3 points")
        for point in v:
            if len(point) != 2:
                raise ValueError("Each point must have exactly 2 coordinates [x, y]")
            if not all(isinstance(coord, int) and coord >= 0 for coord in point):
                raise ValueError("Coordinates must be non-negative integers")
        return v


class ROIConfig(BaseModel):
    """Region of Interest configuration."""
    enabled: bool = Field(default=False, description="Enable ROI filtering")
    polygons: List[ROIPolygon] = Field(default_factory=list, description="List of ROI polygons")
    
    @field_validator("polygons")
    @classmethod
    def validate_polygons(cls, v, info):
        if info.data.get("enabled") and not v:
            raise ValueError("At least one polygon must be defined when ROI is enabled")
        return v


# ============================================================================
# Detector Configuration
# ============================================================================

class MinBoxSize(BaseModel):
    """Minimum bounding box size filter."""
    width: int = Field(default=20, ge=1, description="Minimum box width in pixels")
    height: int = Field(default=20, ge=1, description="Minimum box height in pixels")


class TemporalConfirmation(BaseModel):
    """Temporal confirmation settings to reduce false positives."""
    frames: int = Field(default=3, ge=1, le=30, description="Number of frames to confirm")
    iou_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="IoU threshold for tracking"
    )


class WeaponDetectorConfig(BaseModel):
    """Weapon detector specific configuration."""
    yolo_weights: str = Field(description="Path to YOLO weights (s3:// or local path)")
    classes: List[str] = Field(
        default=["gun", "knife"],
        description="Object classes to detect"
    )
    conf_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence threshold")
    nms_iou: float = Field(default=0.5, ge=0.0, le=1.0, description="NMS IoU threshold")
    min_box: MinBoxSize = Field(default_factory=MinBoxSize, description="Minimum box size")
    temporal_confirm: Optional[TemporalConfirmation] = Field(
        default=None,
        description="Temporal confirmation settings"
    )


class FireSmokeDetectorConfig(BaseModel):
    """Fire/smoke detector specific configuration."""
    yolo_weights: str = Field(description="Path to YOLO weights (s3:// or local path)")
    conf_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence threshold")
    nms_iou: float = Field(default=0.5, ge=0.0, le=1.0, description="NMS IoU threshold")
    min_box: MinBoxSize = Field(default_factory=MinBoxSize, description="Minimum box size")


class ALPRDetectorConfig(BaseModel):
    """ALPR detector specific configuration."""
    plate_detector_weights: str = Field(
        description="Path to plate detection YOLO weights"
    )
    ocr_engine: OCREngine = Field(default=OCREngine.PADDLEOCR, description="OCR engine to use")
    ocr_lang: str = Field(default="en", description="OCR language code")
    conf_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence threshold")
    crop_expand: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Crop expansion ratio for OCR"
    )
    min_box: MinBoxSize = Field(default_factory=MinBoxSize, description="Minimum box size")


class DetectorPipelineConfig(BaseModel):
    """Single detector in pipeline."""
    type: DetectorType = Field(description="Detector type")
    enabled: bool = Field(default=True, description="Enable this detector")
    
    # Detector-specific configs (only one should be set based on type)
    weapon: Optional[WeaponDetectorConfig] = None
    fire_smoke: Optional[FireSmokeDetectorConfig] = None
    alpr: Optional[ALPRDetectorConfig] = None
    
    @model_validator(mode="after")
    def validate_detector_config(self):
        """Ensure correct detector config is provided based on type."""
        type_to_field = {
            DetectorType.WEAPON: "weapon",
            DetectorType.FIRE_SMOKE: "fire_smoke",
            DetectorType.ALPR: "alpr",
        }
        
        required_field = type_to_field[self.type]
        config_value = getattr(self, required_field)
        
        if config_value is None:
            raise ValueError(
                f"Detector type '{self.type}' requires '{required_field}' configuration"
            )
        
        # Warn if other configs are set
        for field_name in type_to_field.values():
            if field_name != required_field and getattr(self, field_name) is not None:
                logger.warning(
                    f"Detector type '{self.type}' has unexpected '{field_name}' config (will be ignored)"
                )
        
        return self


# ============================================================================
# Routing Configuration
# ============================================================================

class EventRoutingConfig(BaseModel):
    """Event routing configuration."""
    to_kds: bool = Field(default=True, description="Send events to Kinesis Data Streams")
    kds_stream_override: Optional[str] = Field(
        default=None,
        description="Override global KDS stream name"
    )


class SnapshotRoutingConfig(BaseModel):
    """Snapshot routing configuration."""
    to_s3: bool = Field(default=True, description="Upload snapshots to S3")
    prefix: str = Field(
        default="snaps/${camera_id}/",
        description="S3 key prefix (supports ${camera_id} variable)"
    )
    on_event_only: bool = Field(
        default=True,
        description="Only upload snapshots when detections occur"
    )
    upload_crops: bool = Field(
        default=True,
        description="Upload detection crops in addition to full frames"
    )


class RoutingConfig(BaseModel):
    """Routing configuration for events and snapshots."""
    events: EventRoutingConfig = Field(
        default_factory=EventRoutingConfig,
        description="Event routing"
    )
    snapshot: SnapshotRoutingConfig = Field(
        default_factory=SnapshotRoutingConfig,
        description="Snapshot routing"
    )


# ============================================================================
# Camera Configuration
# ============================================================================

class CameraConfig(BaseModel):
    """Configuration for a single camera."""
    id: str = Field(description="Unique camera identifier")
    kvs_stream_name: str = Field(description="Kinesis Video Stream name")
    enabled: bool = Field(default=True, description="Enable this camera")
    
    # Playback settings
    playback: PlaybackConfig = Field(
        default_factory=PlaybackConfig,
        description="Playback configuration"
    )
    
    # Frame processing
    fps_target: Optional[int] = Field(
        default=None,
        ge=1,
        le=30,
        description="Target FPS for processing (None = process all frames)"
    )
    resize: Optional[ResizeConfig] = Field(
        default=None,
        description="Resize frames before processing"
    )
    
    # ROI
    roi: ROIConfig = Field(
        default_factory=ROIConfig,
        description="Region of Interest configuration"
    )
    
    # Detection pipeline
    pipeline: List[DetectorPipelineConfig] = Field(
        default_factory=list,
        description="Ordered list of detectors"
    )
    
    # Routing
    routing: RoutingConfig = Field(
        default_factory=RoutingConfig,
        description="Event and snapshot routing"
    )
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Camera ID cannot be empty")
        # Ensure ID is safe for use in paths
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Camera ID must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.strip()
    
    @model_validator(mode="after")
    def validate_hls_retention(self):
        """Warn if HLS mode is used without data retention."""
        if (
            self.playback.mode == PlaybackMode.HLS
            and not self.playback.retention_required
        ):
            logger.warning(
                f"Camera '{self.id}': HLS playback mode requires KVS data retention. "
                f"Set retention_required: true or enable retention in KVS console."
            )
        return self


# ============================================================================
# Top-level Configuration
# ============================================================================

class Config(BaseModel):
    """Top-level application configuration."""
    
    # Global settings
    aws: AWSConfig = Field(default_factory=AWSConfig, description="AWS configuration")
    publishers: GlobalPublishersConfig = Field(
        default_factory=GlobalPublishersConfig,
        description="Global publisher configuration"
    )
    service: ServiceConfig = Field(
        default_factory=ServiceConfig,
        description="Service-level configuration"
    )
    snapshots: SnapshotsConfig = Field(
        default_factory=SnapshotsConfig,
        description="Global snapshots configuration"
    )
    
    # Device settings
    device: str = Field(default="cpu", description="Compute device (cpu, cuda:0, etc.)")
    
    # Cameras
    cameras: List[CameraConfig] = Field(description="Camera configurations")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, ge=1024, le=65535, description="Metrics port")
    metrics_host: str = Field(default="0.0.0.0", description="Metrics host")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: Literal["json", "text"] = Field(default="json", description="Log format")
    
    @field_validator("cameras")
    @classmethod
    def validate_cameras(cls, v):
        if not v:
            raise ValueError("At least one camera must be configured")
        
        # Check for duplicate camera IDs
        ids = [cam.id for cam in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate camera IDs found: {duplicates}")
        
        # Check for duplicate KVS stream names
        streams = [cam.kvs_stream_name for cam in v]
        if len(streams) != len(set(streams)):
            duplicates = [s for s in streams if streams.count(s) > 1]
            logger.warning(
                f"Multiple cameras using same KVS stream: {duplicates}. "
                f"This is allowed but unusual."
            )
        
        return v
    
    @field_validator("device")
    @classmethod
    def validate_device(cls, v):
        valid_patterns = [r'^cpu$', r'^cuda:\d+$', r'^cuda$']
        if not any(re.match(pattern, v) for pattern in valid_patterns):
            raise ValueError(
                f"Invalid device: {v}. Must be 'cpu', 'cuda', or 'cuda:N'"
            )
        return v


# ============================================================================
# Configuration Loader
# ============================================================================

def expand_env_vars(config_dict: Dict[str, Any], context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Recursively expand environment variables and context variables in config.
    
    Supports:
    - ${ENV_VAR} - environment variables
    - ${camera_id} - context variables
    
    Args:
        config_dict: Configuration dictionary
        context: Additional context variables (e.g., camera_id)
        
    Returns:
        Config dict with expanded variables
    """
    if context is None:
        context = {}
    
    def expand_value(value):
        if isinstance(value, str):
            # Expand environment variables
            for match in re.finditer(r'\$\{([^}]+)\}', value):
                var_name = match.group(1)
                
                # Check context first, then environment
                if var_name in context:
                    replacement = context[var_name]
                elif var_name in os.environ:
                    replacement = os.environ[var_name]
                else:
                    logger.warning(f"Variable ${{{var_name}}} not found in context or environment")
                    continue
                
                value = value.replace(match.group(0), replacement)
            
            return value
        
        elif isinstance(value, dict):
            return {k: expand_value(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [expand_value(item) for item in value]
        
        else:
            return value
    
    return expand_value(config_dict)


def load_yaml(config_path: Path) -> Config:
    """
    Load and validate configuration from YAML file.
    
    Performs:
    - YAML parsing
    - Environment variable expansion
    - Pydantic validation
    - Warning checks (HLS retention, etc.)
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Validated Config instance
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
        yaml.YAMLError: If YAML is malformed
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    logger.info(f"Loading configuration from: {config_path}")
    
    # Load YAML
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)
    
    if not isinstance(raw_config, dict):
        raise ValueError("Configuration file must contain a YAML dictionary")
    
    # First pass: expand global environment variables
    raw_config = expand_env_vars(raw_config)
    
    # Second pass: expand camera-specific variables
    if "cameras" in raw_config:
        for camera_config in raw_config["cameras"]:
            camera_id = camera_config.get("id", "unknown")
            context = {"camera_id": camera_id}
            
            # Expand variables in camera config
            if "routing" in camera_config:
                camera_config["routing"] = expand_env_vars(
                    camera_config["routing"],
                    context
                )
    
    # Validate with Pydantic
    try:
        config = Config(**raw_config)
        logger.info(
            f"Configuration loaded successfully: "
            f"{len(config.cameras)} cameras, "
            f"device={config.device}"
        )
        return config
    
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise


# Backward compatibility alias
AppConfig = Config


def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from YAML file and return as dict.
    
    This is a convenience function that loads the YAML file,
    validates it with Pydantic, and returns it as a plain dict
    for easier access without model conversion.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration dict
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    logger.info(f"Loading configuration from: {config_path}")
    
    # Load YAML directly
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)
    
    if not isinstance(raw_config, dict):
        raise ValueError("Configuration file must contain a YAML dictionary")
    
    # Expand environment variables
    config_dict = expand_env_vars(raw_config)
    
    logger.info(
        f"Configuration loaded: "
        f"{len(config_dict.get('cameras', {}))} cameras"
    )
    
    return config_dict


# Alias for Pydantic validation
load_yaml_validated = load_yaml
