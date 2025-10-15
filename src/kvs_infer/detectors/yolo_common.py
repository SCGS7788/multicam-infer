"""
Shared YOLO model loader and utilities with lazy loading and device selection.
"""

import logging
from typing import Optional, List, Tuple
import torch
import numpy as np


logger = logging.getLogger(__name__)


# Global model cache for lazy loading
# {model_path: YOLO instance}
_MODEL_CACHE = {}


def select_device() -> str:
    """
    Auto-select compute device: CUDA:0 if available, else CPU.
    
    Returns:
        Device string ("cuda:0" or "cpu")
    """
    if torch.cuda.is_available():
        device = "cuda:0"
        logger.info(
            f"CUDA available: Using {device} "
            f"({torch.cuda.get_device_name(0)})"
        )
    else:
        device = "cpu"
        logger.info("CUDA not available: Using CPU")
    
    return device


def get_cached_models() -> List[str]:
    """
    Get list of cached model keys.
    
    Returns:
        List of cache keys (format: "model_path:device")
    """
    return list(_MODEL_CACHE.keys())


def load_yolo_model(
    model_path: str,
    device: Optional[str] = None,
) -> "YOLO":
    """
    Load a YOLO model with lazy loading and caching.
    
    Models are cached by (model_path, device) key to avoid reloading.
    
    Args:
        model_path: Path to YOLO model weights (e.g., "yolov8n.pt")
        device: Device to load model on (None = auto-select)
        
    Returns:
        Loaded YOLO model instance
        
    Example:
        model = load_yolo_model("yolov8n.pt")
        model = load_yolo_model("custom.pt", device="cuda:0")
    """
    try:
        from ultralytics import YOLO
    except ImportError as e:
        logger.error("ultralytics not installed: pip install ultralytics")
        raise ImportError(
            "ultralytics package required. "
            "Install with: pip install ultralytics"
        ) from e
    
    # Auto-select device if not specified
    if device is None:
        device = select_device()
    
    # Check cache
    cache_key = f"{model_path}:{device}"
    if cache_key in _MODEL_CACHE:
        logger.debug(f"Using cached YOLO model: {cache_key}")
        return _MODEL_CACHE[cache_key]
    
    # Load model
    logger.info(f"Loading YOLO model: {model_path} on {device}")
    model = YOLO(model_path)
    model.to(device)
    
    # Cache model
    _MODEL_CACHE[cache_key] = model
    logger.info(f"YOLO model loaded and cached: {cache_key}")
    
    return model


def run_yolo(
    model: "YOLO",
    frame: np.ndarray,
    classes: Optional[List[int]] = None,
    conf: float = 0.5,
    iou: float = 0.5,
) -> List[Tuple[str, float, List[float]]]:
    """
    Run YOLO inference on a frame.
    
    Args:
        model: YOLO model instance
        frame: Input frame (numpy array, BGR format)
        classes: Optional list of class IDs to detect (None = all classes)
        conf: Confidence threshold (0.0-1.0)
        iou: IoU threshold for NMS (0.0-1.0)
        
    Returns:
        List of (label, confidence, bbox) tuples
        - label: Class name (str)
        - confidence: Confidence score (float)
        - bbox: Bounding box [x1, y1, x2, y2] as floats
        
    Example:
        model = load_yolo_model("yolov8n.pt")
        detections = run_yolo(model, frame, conf=0.6)
        for label, conf, bbox in detections:
            print(f"{label}: {conf:.2f} @ {bbox}")
    """
    # Run inference
    results = model.predict(
        frame,
        conf=conf,
        iou=iou,
        classes=classes,
        verbose=False,
    )
    
    # Extract detections
    detections = []
    
    if len(results) == 0:
        return detections
    
    result = results[0]  # First result (single image)
    
    if result.boxes is None or len(result.boxes) == 0:
        return detections
    
    # Process each detection
    boxes = result.boxes
    for i in range(len(boxes)):
        # Get bounding box (xyxy format)
        bbox_tensor = boxes.xyxy[i]
        bbox = bbox_tensor.cpu().numpy().tolist()
        
        # Get confidence
        conf_val = float(boxes.conf[i].cpu().numpy())
        
        # Get class ID and name
        class_id = int(boxes.cls[i].cpu().numpy())
        label = result.names[class_id]
        
        detections.append((label, conf_val, bbox))
    
    return detections


def clear_model_cache():
    """
    Clear the model cache.
    
    Useful for releasing GPU memory or reloading models with different settings.
    """
    global _MODEL_CACHE
    _MODEL_CACHE.clear()
    logger.info("Cleared YOLO model cache")


def get_cached_models() -> List[str]:
    """
    Get list of cached model keys.
    
    Returns:
        List of cache keys (format: "model_path:device")
    """
    return list(_MODEL_CACHE.keys())

