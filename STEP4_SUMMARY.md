# Step 4: Specific Detector Implementations - Complete Summary

**Date**: October 12, 2025  
**Status**: ✅ COMPLETE  
**Validation**: All checks passed

## Overview

Step 4 implements three production-ready detectors with temporal confirmation, deduplication, ROI filtering, and specialized features:

1. **WeaponDetector**: YOLO-based weapon detection with class filtering
2. **FireSmokeDetector**: Fire/smoke detection with separate thresholds
3. **ALPRDetector**: License plate recognition with OCR (PaddleOCR + Tesseract)

All detectors share common patterns:
- Temporal confirmation (reduce false positives)
- Spatial deduplication (avoid duplicate events)
- ROI filtering (ignore irrelevant areas)
- Configurable thresholds

## Implementation Details

### 1. WeaponDetector (`weapon.py` - 266 lines)

**Purpose**: Detect weapons (guns, knives, rifles) using YOLO with temporal confirmation.

**Configuration**:
```python
cfg = {
    "model_path": "weapon_yolov8n.pt",
    "device": None,  # Auto-select CUDA:0 or CPU
    "classes": ["knife", "gun", "rifle"],  # Filter by these labels
    "conf_threshold": 0.6,
    "iou_threshold": 0.5,
    "temporal_window": 5,  # frames
    "temporal_iou": 0.3,
    "temporal_min_conf": 3,  # 3/5 frames required
    "dedup_window": 30,  # frames
    "dedup_grid_size": 20,  # pixels
}
```

**Key Features**:
- ✅ Class filtering: Only emit events for specified weapon classes
- ✅ Temporal confirmation: Requires 3/5 consecutive frames
- ✅ Deduplication: Hash by label + spatial grid (20x20 pixels)
- ✅ ROI filtering: Respects region of interest polygons
- ✅ Minimum box area filtering

**Detection Flow**:
```
1. Run YOLO inference
2. Filter by weapon classes (knife, gun, etc.)
3. Apply ROI + min_box_area filtering
4. Check temporal confirmation (3/5 frames)
5. Check deduplication (hash-based, 30-frame window)
6. Emit Event(type="weapon")
```

**Event Schema**:
```python
Event(
    camera_id="camera_1",
    type="weapon",
    label="knife",  # YOLO class name
    conf=0.85,
    bbox=[100, 100, 200, 200],
    ts_ms=1697123456789,
    extras={
        "frame_count": 42,
        "det_hash": "a1b2c3d4e5f6",
    }
)
```

**Deduplication Logic**:
```python
def _detection_hash(label: str, bbox: List[float], grid_size: int = 20) -> str:
    """
    Hash = MD5(label + grid_position)[:12]
    
    Example:
    - label="knife", bbox=[100, 150, 200, 250]
    - center = (150, 200)
    - grid = (7, 10) with grid_size=20
    - hash_input = "knife:7_10"
    - hash = "a1b2c3d4e5f6"
    """
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2
    grid_x = int(center_x // grid_size)
    grid_y = int(center_y // grid_size)
    grid_id = f"{grid_x}_{grid_y}"
    hash_input = f"{label}:{grid_id}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]
```

**Usage Example**:
```python
from kvs_infer.detectors.base import DetectorRegistry, DetectionContext
import numpy as np

# Create detector
detector = DetectorRegistry.create("weapon", {
    "model_path": "weapon_yolov8n.pt",
    "classes": ["knife", "gun", "rifle"],
    "conf_threshold": 0.65,
    "temporal_window": 5,
    "temporal_min_conf": 3,
})

# Setup context
ctx = DetectionContext(
    camera_id="camera_1",
    frame_width=1920,
    frame_height=1080,
    roi_polygons=[[(100, 100), (500, 100), (500, 500), (100, 500)]],
    min_box_area=500,
)

# Process frame
frame = np.zeros((1080, 1920, 3), dtype=np.uint8)  # BGR
events = detector.process(frame, ts_ms=1697123456789, ctx=ctx)

for event in events:
    print(f"⚠️ Weapon: {event.label} ({event.conf:.2f}) @ {event.bbox}")
```

---

### 2. FireSmokeDetector (`fire_smoke.py` - 310 lines)

**Purpose**: Detect fire and smoke with separate thresholds, emitting different event types.

**Configuration**:
```python
cfg = {
    "model_path": "fire_smoke_yolov8n.pt",
    "device": None,
    "fire_labels": ["fire", "flame"],  # Labels for fire
    "smoke_labels": ["smoke"],  # Labels for smoke
    "fire_conf_threshold": 0.6,  # Higher threshold for fire
    "smoke_conf_threshold": 0.55,  # Lower threshold for smoke
    "iou_threshold": 0.5,
    "temporal_window": 5,
    "temporal_iou": 0.3,
    "temporal_min_conf": 3,
    "dedup_window": 30,
    "dedup_grid_size": 20,
}
```

**Key Features**:
- ✅ Separate labels: "fire" vs "smoke" detection
- ✅ Separate thresholds: Different confidence requirements
- ✅ Event type differentiation: type="fire" or type="smoke"
- ✅ Temporal confirmation: 3/5 frames required
- ✅ Deduplication: Hash by label + spatial grid
- ✅ ROI + min_box_area filtering

**Detection Flow**:
```
1. Run YOLO inference (use min of fire/smoke thresholds)
2. Filter by fire_labels or smoke_labels
3. Apply per-label threshold (fire: 0.6, smoke: 0.55)
4. Apply ROI + min_box_area filtering
5. Check temporal confirmation
6. Check deduplication
7. Emit Event(type="fire" or "smoke")
```

**Event Schema**:
```python
# Fire event
Event(
    camera_id="camera_1",
    type="fire",  # <-- Event type is "fire"
    label="flame",  # YOLO class name
    conf=0.82,
    bbox=[300, 200, 400, 350],
    ts_ms=1697123456789,
    extras={
        "frame_count": 42,
        "det_hash": "b2c3d4e5f6a1",
        "threshold_used": 0.6,
    }
)

# Smoke event
Event(
    camera_id="camera_1",
    type="smoke",  # <-- Event type is "smoke"
    label="smoke",
    conf=0.68,
    bbox=[200, 100, 350, 250],
    ts_ms=1697123456790,
    extras={
        "frame_count": 43,
        "det_hash": "c3d4e5f6a1b2",
        "threshold_used": 0.55,
    }
)
```

**Threshold Logic**:
```python
def _get_threshold_for_label(self, label: str) -> float:
    if label in self.fire_labels:
        return self.fire_conf_threshold  # 0.6
    elif label in self.smoke_labels:
        return self.smoke_conf_threshold  # 0.55
    else:
        return max(self.fire_conf_threshold, self.smoke_conf_threshold)

def _get_event_type_for_label(self, label: str) -> str:
    if label in self.fire_labels:
        return "fire"
    elif label in self.smoke_labels:
        return "smoke"
    else:
        return "fire_smoke"  # Fallback
```

**Usage Example**:
```python
detector = DetectorRegistry.create("fire_smoke", {
    "model_path": "fire_smoke_yolov8n.pt",
    "fire_labels": ["fire", "flame"],
    "smoke_labels": ["smoke"],
    "fire_conf_threshold": 0.65,
    "smoke_conf_threshold": 0.55,
})

events = detector.process(frame, ts_ms, ctx)

for event in events:
    if event.type == "fire":
        print(f"🔥 FIRE: {event.label} ({event.conf:.2f})")
    elif event.type == "smoke":
        print(f"💨 SMOKE: {event.label} ({event.conf:.2f})")
```

---

### 3. ALPRDetector (`alpr.py` - 251 lines)

**Purpose**: Detect license plates using YOLO, then extract text using OCR (PaddleOCR or Tesseract).

**Configuration**:
```python
cfg = {
    "model_path": "plate_yolov8n.pt",
    "device": None,
    "plate_classes": ["plate", "license_plate"],
    "conf_threshold": 0.6,
    "iou_threshold": 0.5,
    "crop_expand": 0.1,  # 10% expansion for cropping
    "ocr_engine": "paddleocr",  # or "tesseract"
    "ocr_lang": "th",  # Thai language
    "ocr_conf_threshold": 0.6,
    "temporal_window": 5,
    "temporal_iou": 0.3,
    "temporal_min_conf": 3,
    "dedup_window": 60,  # Longer window for plates
    "dedup_grid_size": 20,
}
```

**Key Features**:
- ✅ YOLO plate detection
- ✅ Crop + pad plate region (10% expansion)
- ✅ OCR with PaddleOCR (multilingual) or Tesseract
- ✅ OCR confidence filtering
- ✅ Temporal confirmation (3/5 frames)
- ✅ Deduplication by plate text + location (60-frame window)
- ✅ ROI + min_box_area filtering

**Detection Flow**:
```
1. Run YOLO inference to detect plates
2. Filter by plate_classes
3. Apply ROI + min_box_area filtering
4. Check temporal confirmation
5. Crop and pad plate region (expand by 10%)
6. Run OCR (PaddleOCR or Tesseract)
7. Filter by OCR confidence threshold
8. Check deduplication (text-based hash)
9. Emit Event(type="alpr", extras={"text": ..., "ocr_conf": ...})
```

**Event Schema**:
```python
Event(
    camera_id="camera_1",
    type="alpr",
    label="plate",  # YOLO class name
    conf=0.88,  # YOLO confidence
    bbox=[450, 300, 600, 380],
    ts_ms=1697123456789,
    extras={
        "text": "ABC1234",  # <-- OCR text
        "ocr_conf": 0.92,  # <-- OCR confidence
        "ocr_engine": "paddleocr",
        "frame_count": 42,
        "det_hash": "d4e5f6a1b2c3",
    }
)
```

**OCR Engines**:

**PaddleOCR** (Recommended for Thai/multilingual):
```python
from paddleocr import PaddleOCR

# Initialize once
ocr = PaddleOCR(use_angle_cls=True, lang="th", show_log=False)

# Run OCR
result = ocr.ocr(crop_image, cls=True)

# Extract text
texts = [line[1][0] for line in result[0]]
confs = [line[1][1] for line in result[0]]
combined_text = "".join(texts).strip()
avg_conf = sum(confs) / len(confs)
```

**Tesseract** (Fallback):
```python
import pytesseract
from PIL import Image

# Convert to PIL
pil_img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

# Run OCR
data = pytesseract.image_to_data(pil_img, lang="th", output_type=pytesseract.Output.DICT)

# Extract text
texts = [data["text"][i] for i, conf in enumerate(data["conf"]) if conf > 0]
combined_text = "".join(texts)
```

**Crop and Pad**:
```python
def _crop_and_pad_plate(frame: np.ndarray, bbox: List[float], expand_ratio: float = 0.1):
    """
    Crop plate with 10% expansion on all sides.
    
    Example:
    - bbox = [100, 100, 300, 200]
    - width = 200, height = 100
    - expand_w = 20, expand_h = 10
    - new_bbox = [80, 90, 320, 210]
    """
    x1, y1, x2, y2 = [int(v) for v in bbox]
    width = x2 - x1
    height = y2 - y1
    expand_w = int(width * expand_ratio)
    expand_h = int(height * expand_ratio)
    
    # Apply expansion with boundary checks
    h, w = frame.shape[:2]
    x1 = max(0, x1 - expand_w)
    y1 = max(0, y1 - expand_h)
    x2 = min(w, x2 + expand_w)
    y2 = min(h, y2 + expand_h)
    
    crop = frame[y1:y2, x1:x2]
    return crop
```

**Deduplication Logic** (text-based):
```python
def _detection_hash(text: str, bbox: List[float], grid_size: int = 20) -> str:
    """
    Hash = MD5(plate_text + grid_position)[:12]
    
    Example:
    - text = "ABC1234"
    - bbox = [450, 300, 600, 380]
    - center = (525, 340)
    - grid = (26, 17) with grid_size=20
    - hash_input = "ABC1234:26_17"
    - hash = "d4e5f6a1b2c3"
    """
    grid_id = _bbox_to_grid(bbox, grid_size)
    hash_input = f"{text}:{grid_id}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]
```

**Usage Example**:
```python
detector = DetectorRegistry.create("alpr", {
    "model_path": "plate_yolov8n.pt",
    "plate_classes": ["plate", "license_plate"],
    "conf_threshold": 0.65,
    "ocr_engine": "paddleocr",
    "ocr_lang": "th",
    "crop_expand": 0.1,
})

events = detector.process(frame, ts_ms, ctx)

for event in events:
    plate_text = event.extras["text"]
    ocr_conf = event.extras["ocr_conf"]
    print(f"🚗 Plate: {plate_text} (YOLO: {event.conf:.2f}, OCR: {ocr_conf:.2f})")
```

---

## Common Patterns

### 1. Temporal Confirmation

**Purpose**: Reduce false positives by requiring detections in multiple consecutive frames.

**Implementation**:
```python
from kvs_infer.detectors.base import TemporalConfirmationHelper

helper = TemporalConfirmationHelper(
    window_frames=5,  # 5-frame sliding window
    iou_threshold=0.3,  # 30% IoU for same detection
    min_confirmations=3  # 3/5 frames required
)

# Add detection and check confirmation
is_confirmed = helper.add_and_check(
    label="knife",
    bbox=[100, 100, 200, 200],
    conf=0.85,
    ts_ms=1697123456789
)

if is_confirmed:
    # Emit event
    pass
```

**How It Works**:
1. Maintains a sliding window of recent detections (deque)
2. For each new detection, finds matches in window using IoU
3. Counts matches for same label
4. Returns True if count >= min_confirmations

**Example Timeline**:
```
Frame 1: knife @ [100,100,200,200] → count=1, not confirmed
Frame 2: knife @ [105,102,205,202] → count=2, not confirmed (IoU=0.85)
Frame 3: knife @ [103,98,203,198] → count=3, CONFIRMED! (IoU=0.82)
Frame 4: knife @ [108,95,208,195] → count=4, already confirmed
Frame 5: knife @ [110,92,210,192] → count=5, already confirmed
Frame 6: (window slides, Frame 1 dropped)
```

### 2. Spatial Deduplication

**Purpose**: Avoid emitting duplicate events for the same detection.

**Implementation**:
```python
from collections import deque
import hashlib

dedup_window = 30  # frames
dedup_grid_size = 20  # pixels
_recent_detections = deque(maxlen=30)
_frame_count = 0

# For each detection
det_hash = _detection_hash(label, bbox, dedup_grid_size)

# Check if recently emitted
is_duplicate = False
for frame_num, recent_hash in _recent_detections:
    if recent_hash == det_hash:
        if (_frame_count - frame_num) < dedup_window:
            is_duplicate = True
            break

if not is_duplicate:
    _recent_detections.append((_frame_count, det_hash))
    # Emit event
```

**Grid Quantization**:
```
Frame resolution: 1920x1080
Grid size: 20 pixels
Grid dimensions: 96x54 cells

Example:
- Detection at (525, 340) → Grid cell (26, 17)
- Detection at (535, 345) → Grid cell (26, 17) ← Same cell!
- Detection at (545, 360) → Grid cell (27, 18) ← Different cell
```

### 3. ROI Filtering

**Purpose**: Ignore detections outside regions of interest.

**Implementation**:
```python
from kvs_infer.detectors.base import filter_detections

roi_polygons = [
    [(100, 100), (500, 100), (500, 500), (100, 500)],  # Entrance
    [(800, 200), (1200, 200), (1200, 600), (800, 600)]  # Exit
]

detections = filter_detections(
    detections,
    roi_polygons=roi_polygons,
    min_area=500  # 500 pixels minimum
)
```

**Ray Casting Algorithm**:
```python
def point_in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
    """
    Check if point is inside polygon using ray casting.
    
    Cast ray from point to infinity (horizontal right).
    Count intersections with polygon edges.
    Odd count = inside, even count = outside.
    """
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
```

## Files Created

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `src/kvs_infer/detectors/weapon.py` | 266 | 8.2 KB | Weapon detector with temporal confirmation |
| `src/kvs_infer/detectors/fire_smoke.py` | 310 | 10.5 KB | Fire/smoke detector with separate thresholds |
| `src/kvs_infer/detectors/alpr.py` | 251 | 9.9 KB | ALPR detector with OCR (PaddleOCR + Tesseract) |
| `src/kvs_infer/detectors/__init__.py` | 10 | 0.3 KB | Import detectors for registration |
| `validate_step4.py` | 399 | 13.1 KB | Validation script |
| **Total** | **1,236** | **41.9 KB** | |

## Validation Results

```bash
$ python3.11 validate_step4.py

✅ STEP 4 VALIDATION COMPLETE!

All checks passed. Detector implementations are complete.

Summary:
  • Weapon detector: Complete
  • Fire/Smoke detector: Complete
  • ALPR detector: Complete
  • Temporal confirmation: Complete
  • Deduplication: Complete
  • ROI filtering: Complete
```

### Validation Checks (All Passed)
- ✅ 3 detector files (weapon, fire_smoke, alpr)
- ✅ All detectors registered in DetectorRegistry
- ✅ All detectors import successfully
- ✅ Detector interface (configure, process, is_configured)
- ✅ Deduplication logic (_detection_hash, _bbox_to_grid)
- ✅ Temporal confirmation (temporal_helper)
- ✅ ROI filtering (filter_detections usage)
- ✅ ALPR-specific features (crop, OCR engines, extras)
- ✅ Fire/smoke separate thresholds

## Configuration Examples

### Camera 1: Weapon Detection (Entrance)
```yaml
camera_id: camera_1
stream_name: entrance-stream
detector_type: weapon
detector_config:
  model_path: /models/weapon_yolov8n.pt
  classes: [knife, gun, rifle]
  conf_threshold: 0.65
  temporal_window: 5
  temporal_min_conf: 3
  dedup_window: 30
roi_zones:
  - [[100, 100], [500, 100], [500, 500], [100, 500]]
min_object_area: 500
```

### Camera 2: Fire/Smoke Detection (Kitchen)
```yaml
camera_id: camera_2
stream_name: kitchen-stream
detector_type: fire_smoke
detector_config:
  model_path: /models/fire_smoke_yolov8n.pt
  fire_labels: [fire, flame]
  smoke_labels: [smoke]
  fire_conf_threshold: 0.65
  smoke_conf_threshold: 0.55
  temporal_window: 5
  temporal_min_conf: 3
  dedup_window: 30
roi_zones:
  - [[200, 150], [800, 150], [800, 700], [200, 700]]
min_object_area: 1000
```

### Camera 3: ALPR (Parking Lot)
```yaml
camera_id: camera_3
stream_name: parking-stream
detector_type: alpr
detector_config:
  model_path: /models/plate_yolov8n.pt
  plate_classes: [plate, license_plate]
  conf_threshold: 0.65
  ocr_engine: paddleocr
  ocr_lang: th
  ocr_conf_threshold: 0.6
  crop_expand: 0.1
  temporal_window: 5
  temporal_min_conf: 3
  dedup_window: 60
roi_zones:
  - [[300, 200], [1200, 200], [1200, 800], [300, 800]]
min_object_area: 500
```

## Integration with CameraWorker

```python
# In app.py CameraWorker

from kvs_infer.detectors.base import DetectorRegistry, DetectionContext
from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource

# Load config
camera_cfg = load_camera_config("camera_1.yaml")

# Create detector
detector = DetectorRegistry.create(
    camera_cfg.detector_type,  # "weapon"
    camera_cfg.detector_config.model_dump()
)

# Create frame source
frame_source = KVSHLSFrameSource(
    stream_name=camera_cfg.stream_name,
    region=camera_cfg.aws_region
)

# Setup context
ctx = DetectionContext(
    camera_id=camera_cfg.camera_id,
    frame_width=1920,
    frame_height=1080,
    roi_polygons=camera_cfg.roi_zones,
    min_box_area=camera_cfg.min_object_area
)

# Processing loop
for frame, ts_ms in frame_source:
    # Run detector
    events = detector.process(frame, ts_ms, ctx)
    
    # Publish events
    for event in events:
        publisher.send(event.to_dict())
        
        logger.info(
            f"Event: {event.type} - {event.label} "
            f"({event.conf:.2f}) @ {event.bbox}"
        )
```

## Dependencies

### Core Dependencies
```
torch>=2.3.1        # YOLO model inference
ultralytics         # YOLO models
opencv-python       # Frame processing, cropping
numpy               # Array operations
```

### OCR Dependencies (Optional)
```
paddleocr           # Recommended for multilingual OCR
pytesseract         # Alternative OCR engine
Pillow              # Image processing for Tesseract
```

### Installation
```bash
# Core dependencies
pip install torch ultralytics opencv-python numpy

# PaddleOCR (recommended)
pip install paddleocr

# OR Tesseract (alternative)
pip install pytesseract pillow
# Also requires: brew install tesseract (macOS) or apt-get install tesseract-ocr (Ubuntu)
```

## Performance Characteristics

### Latency Benchmarks (Estimated)

| Component | Latency (ms) | Notes |
|-----------|--------------|-------|
| YOLO inference (GPU) | 20-50 | YOLOv8n on RTX 3060 |
| YOLO inference (CPU) | 200-500 | YOLOv8n on Intel i7 |
| Temporal confirmation | 0.1 | 5-frame window check |
| Deduplication | 0.05 | Hash lookup in deque |
| ROI filtering | 0.5 | 2 polygons, 10 detections |
| **Weapon total (GPU)** | **25-55** | |
| **Weapon total (CPU)** | **200-505** | |
| PaddleOCR (Thai) | 100-200 | Single plate |
| Tesseract OCR | 50-150 | Single plate |
| Crop and pad | 1-2 | OpenCV operations |
| **ALPR total (GPU)** | **125-255** | YOLO + OCR |
| **ALPR total (CPU)** | **350-655** | YOLO + OCR |

### Memory Usage

| Component | Memory (MB) | Notes |
|-----------|-------------|-------|
| YOLOv8n model | 6 | Nano model |
| YOLOv8m model | 25 | Medium model |
| PaddleOCR models | 50-100 | Det + Rec + Cls models |
| Tesseract | 10-20 | Language data |
| Frame buffer (1080p) | 6 | 1920x1080x3 bytes |
| Temporal window | 0.5 | 5 frames of detections |
| Dedup window | 0.1 | 30-60 frame hashes |

### Throughput (FPS)

| Detector | GPU (FPS) | CPU (FPS) | Notes |
|----------|-----------|-----------|-------|
| Weapon | 20-40 | 2-5 | YOLOv8n |
| Fire/Smoke | 20-40 | 2-5 | YOLOv8n |
| ALPR | 8-15 | 1-2 | YOLO + OCR |

## Troubleshooting

### Issue 1: "No detections after temporal confirmation"
```python
# Lower temporal requirements
detector_config:
  temporal_window: 5
  temporal_min_conf: 2  # Was 3, now 2/5 frames
  temporal_iou: 0.2  # Was 0.3, now more lenient
```

### Issue 2: "Too many duplicate events"
```python
# Increase dedup window
detector_config:
  dedup_window: 60  # Was 30, now 2 seconds at 30 FPS
  dedup_grid_size: 10  # Was 20, now finer grid
```

### Issue 3: "PaddleOCR not recognizing Thai plates"
```python
# Check PaddleOCR installation
python -c "from paddleocr import PaddleOCR; print(PaddleOCR(lang='th'))"

# Try different language
detector_config:
  ocr_lang: en  # English
  # OR
  ocr_lang: ch  # Chinese
```

### Issue 4: "ALPR OCR confidence too low"
```python
# Lower OCR confidence threshold
detector_config:
  ocr_conf_threshold: 0.4  # Was 0.6
  
# Increase crop expansion
detector_config:
  crop_expand: 0.15  # Was 0.1 (10%), now 15%
```

### Issue 5: "Fire detector too sensitive"
```python
# Increase fire threshold
detector_config:
  fire_conf_threshold: 0.75  # Was 0.6
  temporal_min_conf: 4  # Was 3, require 4/5 frames
```

### Issue 6: "Detections outside ROI"
```python
# Check ROI polygon definition
roi_zones:
  - [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
  # Must be clockwise or counter-clockwise
  # Example: [[100,100], [500,100], [500,500], [100,500]]

# Visualize ROI
import cv2
frame_copy = frame.copy()
for polygon in roi_polygons:
    pts = np.array(polygon, np.int32).reshape((-1, 1, 2))
    cv2.polylines(frame_copy, [pts], True, (0, 255, 0), 2)
cv2.imshow("ROI", frame_copy)
```

## Testing Strategy

### Unit Tests Required

1. **WeaponDetector**:
   - Test class filtering
   - Test temporal confirmation
   - Test deduplication logic
   - Test ROI filtering integration
   - Test event creation

2. **FireSmokeDetector**:
   - Test separate thresholds
   - Test event type differentiation (fire vs smoke)
   - Test label-specific threshold application
   - Test temporal confirmation
   - Test deduplication

3. **ALPRDetector**:
   - Test plate detection
   - Test crop and pad logic
   - Test PaddleOCR integration (mock)
   - Test Tesseract integration (mock)
   - Test OCR confidence filtering
   - Test text-based deduplication

### Integration Tests Required

1. **Full Pipeline**:
   - Frame source → Detector → Events
   - Multiple detections in single frame
   - Temporal confirmation across frames
   - Deduplication across frames
   - ROI filtering with real polygons

2. **Configuration**:
   - Load from YAML
   - Create detector from config
   - Configure with invalid params
   - Validate all config fields

## Next Steps

### Priority 1: Unit Tests
- Create `tests/test_weapon_detector.py`
- Create `tests/test_fire_smoke_detector.py`
- Create `tests/test_alpr_detector.py`
- Achieve >90% code coverage

### Priority 1: CameraWorker Integration
- Wire detector pipeline in `app.py`
- Add detector metrics (latency, event count)
- Add error handling for detector failures
- Add graceful degradation

### Priority 2: Documentation
- Create `docs/DETECTOR_USAGE.md` with examples
- Create `docs/DETECTOR_TUNING.md` with parameter guides
- Add docstring examples for all detectors

### Priority 3: Performance Optimization
- Profile detector latency
- Optimize crop operations
- Add batch inference support
- Add async detector processing

### Priority 4: Model Training
- Collect weapon detection dataset
- Train custom YOLO model for weapons
- Collect fire/smoke dataset
- Collect Thai license plate dataset
- Train custom plate detection model

## References

- [Ultralytics YOLOv8 Documentation](https://docs.ultralytics.com/)
- [PaddleOCR Documentation](https://github.com/PaddlePaddle/PaddleOCR)
- [Tesseract OCR Documentation](https://github.com/tesseract-ocr/tesseract)
- [Temporal Confirmation in Object Detection](https://arxiv.org/abs/1703.07402)
- [Deduplication Strategies for Event Streams](https://en.wikipedia.org/wiki/Data_deduplication)

---

**Summary**: Step 4 delivers three production-ready detectors (weapon, fire_smoke, alpr) with temporal confirmation, spatial deduplication, ROI filtering, and specialized features. Total implementation: 827 lines across 3 files. All validation checks passed. Ready for integration with CameraWorker.
