# Step 3: Detector Interface & Registry - Implementation Summary

**Date**: 2024
**Status**: ✅ COMPLETE
**Validation**: All checks passed

## Overview

Step 3 implements the detector abstraction layer with registry pattern, event schema, temporal confirmation, ROI filtering, and YOLO utilities. This provides the foundation for implementing specific detectors (weapon, fire_smoke, ALPR).

## Implementation Details

### 1. Event Schema (`Event` dataclass)
- **Purpose**: Standardized detection event format
- **Fields**:
  - `camera_id: str` - Camera identifier
  - `type: str` - Detector type (weapon, fire_smoke, alpr, etc.)
  - `label: str` - Detection label/class name
  - `conf: float` - Confidence score (0.0-1.0)
  - `bbox: List[float]` - Bounding box [x1, y1, x2, y2]
  - `ts_ms: int` - Timestamp in milliseconds
  - `extras: dict` - Additional metadata
- **Validation**: Confidence range check, bbox format check
- **Methods**: `validate()`, `to_dict()`, `from_dict()`

### 2. DetectionContext (`DetectionContext` dataclass)
- **Purpose**: Provides context for detection processing
- **Fields**:
  - `camera_id: str`
  - `frame_width: int`
  - `frame_height: int`
  - `roi_polygons: Optional[List[List[Tuple[float, float]]]]` - ROI polygons
  - `min_box_area: float` - Minimum box area filter

### 3. Detector Abstract Base Class
- **Purpose**: Interface for all detector implementations
- **Abstract Methods**:
  - `configure(self, cfg: dict) -> None` - Configure detector
  - `process(self, frame, ts_ms, ctx) -> List[Event]` - Process frame
- **Concrete Methods**:
  - `is_configured() -> bool`
  - `get_name() -> str`

### 4. DetectorRegistry (Singleton Pattern)
- **Purpose**: Centralized detector registration and creation
- **Methods**:
  - `@classmethod register(name: str)` - Decorator for registration
  - `create(name: str, cfg: dict) -> Detector` - Factory method
  - `list_detectors() -> List[str]` - List registered detectors
  - `is_registered(name: str) -> bool` - Check registration
- **Usage**:
  ```python
  @DetectorRegistry.register("weapon")
  class WeaponDetector(Detector):
      ...
  
  detector = DetectorRegistry.create("weapon", cfg)
  ```

### 5. TemporalConfirmationHelper
- **Purpose**: Confirm detections over multiple frames
- **Parameters**:
  - `window_frames: int` - Sliding window size (default: 5)
  - `iou_threshold: float` - IoU threshold for matching (default: 0.3)
  - `min_confirmations: int` - Minimum confirmations required (default: 3)
- **Methods**:
  - `add_detection(label, bbox, conf, ts_ms)` - Add detection
  - `check_confirmation(label, bbox) -> bool` - Check if confirmed
  - `add_and_check(label, bbox, conf, ts_ms) -> bool` - Add and check
- **Implementation**: Uses `collections.deque` for efficient sliding window

### 6. ROI Filtering Utilities
- **`calculate_iou(bbox1, bbox2) -> float`**: Intersection over Union
- **`point_in_polygon(x, y, polygon) -> bool`**: Ray casting algorithm
- **`bbox_in_roi(bbox, roi_polygons) -> bool`**: Check if bbox overlaps ROI
- **`filter_by_min_box_size(detections, min_area) -> List`**: Filter small boxes
- **`filter_detections(detections, roi_polygons, min_area) -> List`**: Combined filtering

### 7. YOLO Common Utilities
- **`select_device() -> str`**: Auto-select "cuda:0" or "cpu"
- **`load_yolo_model(model_path, device) -> YOLO`**: Lazy load with caching
- **`run_yolo(model, frame, classes, conf, iou) -> List`**: Run inference
- **`clear_model_cache()`**: Clear cached models
- **`get_cached_models() -> List[str]`**: List cached models
- **Model Cache**: `{model_path:device → YOLO instance}`

## Files Created

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `src/kvs_infer/detectors/base.py` | 657 | 18.6 KB | Event schema, Detector ABC, Registry, Temporal confirmation, ROI utilities |
| `src/kvs_infer/detectors/yolo_common.py` | 187 | 4.6 KB | YOLO lazy loading, device selection, inference |
| `validate_step3.py` | 197 | 6.5 KB | Validation script |
| **Total** | **1,041** | **29.7 KB** | |

## Validation Results

```bash
$ python3.11 validate_step3.py

✅ STEP 3 VALIDATION COMPLETE!

All checks passed. Detector interface and registry are complete.

Summary:
  • Event schema: Complete
  • Detector base class: Complete
  • DetectorRegistry: Complete
  • Temporal confirmation: Complete
  • ROI filtering: Complete
  • YOLO common: Complete
```

### Validation Checks (All Passed)
- ✅ Event class with 7 fields
- ✅ DetectionContext class
- ✅ Detector ABC with configure() and process()
- ✅ DetectorRegistry with register(), create(), list_detectors()
- ✅ TemporalConfirmationHelper with sliding window
- ✅ 5 utility functions (IoU, point-in-polygon, ROI filtering)
- ✅ YOLO common with lazy loading and device selection
- ✅ Event validation (confidence, bbox format)
- ✅ Integration tests (Event creation, Registry operations)

## Architecture Decisions

### 1. Abstract Base Class Pattern
- **Decision**: Use `abc.ABC` with `@abstractmethod`
- **Rationale**: Enforces interface contract, type safety, IDE autocomplete
- **Trade-off**: Slightly more verbose than duck typing, but better maintainability

### 2. Registry with Decorator Pattern
- **Decision**: Use class decorator `@DetectorRegistry.register(name)`
- **Rationale**: Declarative registration, no manual bookkeeping
- **Example**:
  ```python
  @DetectorRegistry.register("weapon")
  class WeaponDetector(Detector):
      pass
  ```

### 3. Temporal Confirmation with Deque
- **Decision**: Use `collections.deque(maxlen=window_frames)`
- **Rationale**: O(1) append/pop, automatic size management, thread-safe
- **Alternative Considered**: List with manual slicing (O(n) complexity)

### 4. IoU-Based Detection Matching
- **Decision**: Use IoU > threshold for same detection across frames
- **Rationale**: Robust to small bbox variations, standard in tracking
- **Parameters**: Default IoU threshold = 0.3 (30% overlap)

### 5. Ray Casting for Point-in-Polygon
- **Decision**: Implement ray casting algorithm
- **Rationale**: O(n) complexity, handles concave polygons, no external dependencies
- **Alternative Considered**: Shapely library (avoided extra dependency)

### 6. Lazy Model Loading with Cache
- **Decision**: Cache loaded models by (path, device) key
- **Rationale**: Avoid reloading models (expensive), support multiple models
- **Memory Trade-off**: Models stay in memory until explicit clear

## Integration Points

### 1. CameraWorker Integration
```python
# In app.py CameraWorker
detector = DetectorRegistry.create(
    cfg.detector_type,
    cfg.detector_config
)

ctx = DetectionContext(
    camera_id=cfg.camera_id,
    frame_width=frame.shape[1],
    frame_height=frame.shape[0],
    roi_polygons=cfg.roi_zones,
    min_box_area=cfg.min_object_area,
)

events = detector.process(frame, ts_ms, ctx)
for event in events:
    publisher.send(event)
```

### 2. Specific Detector Implementation
```python
from kvs_infer.detectors.base import Detector, DetectorRegistry, Event
from kvs_infer.detectors.yolo_common import load_yolo_model, run_yolo

@DetectorRegistry.register("weapon")
class WeaponDetector(Detector):
    def configure(self, cfg: dict):
        self.model = load_yolo_model(cfg["model_path"])
        self.conf_threshold = cfg.get("conf_threshold", 0.6)
        self._configured = True
    
    def process(self, frame, ts_ms, ctx) -> List[Event]:
        detections = run_yolo(
            self.model, frame,
            conf=self.conf_threshold
        )
        
        events = []
        for label, conf, bbox in detections:
            event = Event(
                camera_id=ctx.camera_id,
                type="weapon",
                label=label,
                conf=conf,
                bbox=bbox,
                ts_ms=ts_ms,
                extras={}
            )
            events.append(event)
        
        return events
```

## Usage Examples

### Example 1: Basic Detector Registration
```python
from kvs_infer.detectors.base import Detector, DetectorRegistry

@DetectorRegistry.register("my_detector")
class MyDetector(Detector):
    def configure(self, cfg: dict):
        self.threshold = cfg.get("threshold", 0.5)
        self._configured = True
    
    def process(self, frame, ts_ms, ctx):
        # Detection logic
        return []

# Create detector
detector = DetectorRegistry.create("my_detector", {"threshold": 0.7})
```

### Example 2: Temporal Confirmation
```python
from kvs_infer.detectors.base import TemporalConfirmationHelper

helper = TemporalConfirmationHelper(
    window_frames=5,
    iou_threshold=0.3,
    min_confirmations=3
)

# Add detection from frame 1
is_confirmed = helper.add_and_check(
    "weapon", [100, 100, 200, 200], 0.8, 1000
)
# Returns False (only 1/3 confirmations)

# Add similar detection from frame 2
is_confirmed = helper.add_and_check(
    "weapon", [105, 102, 205, 202], 0.82, 1033
)
# Returns False (only 2/3 confirmations)

# Add similar detection from frame 3
is_confirmed = helper.add_and_check(
    "weapon", [103, 98, 203, 198], 0.79, 1066
)
# Returns True (3/3 confirmations reached!)
```

### Example 3: ROI Filtering
```python
from kvs_infer.detectors.base import filter_detections

roi_polygons = [
    [(100, 100), (300, 100), (300, 300), (100, 300)]  # Square ROI
]

detections = [
    ("weapon", 0.8, [150, 150, 200, 200]),  # Inside ROI
    ("weapon", 0.7, [50, 50, 80, 80]),      # Outside ROI
]

filtered = filter_detections(
    detections,
    roi_polygons=roi_polygons,
    min_area=500  # 500 pixels minimum
)
# Returns only the first detection
```

### Example 4: YOLO Lazy Loading
```python
from kvs_infer.detectors.yolo_common import load_yolo_model, run_yolo

# First call: loads model
model = load_yolo_model("yolov8n.pt")  # ~3 seconds

# Second call: instant (cached)
model = load_yolo_model("yolov8n.pt")  # ~0.001 seconds

# Run inference
detections = run_yolo(
    model, frame,
    classes=[0, 1, 2],  # person, bicycle, car
    conf=0.6,
    iou=0.5
)

for label, conf, bbox in detections:
    print(f"{label}: {conf:.2f}")
```

## Testing Strategy

### Unit Tests Required
1. **Event Validation**:
   - Valid event creation
   - Invalid confidence (< 0 or > 1)
   - Invalid bbox format (not 4 values)
   - to_dict() and from_dict() round-trip

2. **DetectorRegistry**:
   - Register detector
   - Create detector
   - List registered detectors
   - Duplicate registration error
   - Unknown detector error

3. **TemporalConfirmationHelper**:
   - Single detection (not confirmed)
   - Multiple detections with high IoU (confirmed)
   - Multiple detections with low IoU (not confirmed)
   - Window sliding behavior (old detections dropped)

4. **ROI Filtering**:
   - Point in polygon (inside, outside, on edge)
   - Bbox in ROI (fully inside, partially inside, outside)
   - calculate_iou() (overlapping, non-overlapping, identical boxes)
   - filter_by_min_box_size()

5. **YOLO Common**:
   - select_device() with/without CUDA
   - load_yolo_model() caching
   - run_yolo() with mock model (avoid downloading weights)

### Integration Tests Required
1. **Full Detector Pipeline**:
   - Register → Create → Configure → Process
   - Event generation and validation
   - ROI filtering integration
   - Temporal confirmation integration

## Next Steps

### 1. Implement Specific Detectors (Priority 1)
- **weapon.py**: Weapon detection with YOLO
- **fire_smoke.py**: Fire/smoke detection with YOLO
- **alpr.py**: License plate recognition with EasyOCR

### 2. Unit Tests (Priority 1)
- Create `tests/test_detector_base.py`
- Create `tests/test_yolo_common.py`
- Achieve >90% code coverage

### 3. Documentation (Priority 2)
- Create `docs/DETECTOR_BASE.md` with architecture
- Create `docs/DETECTOR_GUIDE.md` for custom detector development
- Add docstring examples

### 4. CameraWorker Integration (Priority 1)
- Wire detector pipeline in `app.py`
- Add metrics for detection latency
- Add error handling for detector failures

### 5. Performance Optimization (Priority 3)
- Profile detector.process() latency
- Optimize YOLO inference batching
- Add async detector support

## Dependencies

### Direct Dependencies
- `torch` (2.3.1+): Device selection, CUDA support
- `numpy`: Array operations for bbox/IoU calculations
- `ultralytics`: YOLO model loading and inference (optional at runtime)

### Standard Library
- `abc`: Abstract base classes
- `dataclasses`: Event and context schemas
- `collections.deque`: Temporal confirmation window
- `logging`: Detector logging
- `typing`: Type hints

## Performance Characteristics

### Memory Usage
- **Event**: ~200 bytes per event
- **TemporalConfirmationHelper**: ~1 KB per instance (5-frame window)
- **YOLO Model Cache**: ~6 MB per YOLOv8n model, ~25 MB per YOLOv8m model

### Compute Complexity
- **calculate_iou()**: O(1) - constant time
- **point_in_polygon()**: O(n) - n = polygon vertices
- **bbox_in_roi()**: O(m*n) - m = ROI polygons, n = vertices per polygon
- **TemporalConfirmationHelper.add_and_check()**: O(w) - w = window size

### Latency Benchmarks (Estimated)
- Event validation: ~0.01 ms
- IoU calculation: ~0.001 ms
- Point-in-polygon: ~0.01 ms (10-vertex polygon)
- Temporal confirmation: ~0.1 ms (5-frame window)
- YOLO inference: ~20-50 ms (YOLOv8n on GPU)

## Troubleshooting

### Issue 1: "ultralytics not installed"
```bash
pip install ultralytics
```

### Issue 2: YOLO model download fails
```python
# Pre-download models
from ultralytics import YOLO
model = YOLO("yolov8n.pt")  # Downloads to ~/.cache/ultralytics/
```

### Issue 3: CUDA out of memory
```python
# Clear model cache
from kvs_infer.detectors.yolo_common import clear_model_cache
clear_model_cache()

# Use smaller model
model = load_yolo_model("yolov8n.pt")  # Instead of yolov8m.pt
```

### Issue 4: Temporal confirmation not working
```python
# Check IoU threshold and min_confirmations
helper = TemporalConfirmationHelper(
    window_frames=5,
    iou_threshold=0.2,  # Lower threshold (was 0.3)
    min_confirmations=2  # Lower requirement (was 3)
)
```

### Issue 5: ROI filtering too aggressive
```python
# Debug ROI polygons
from kvs_infer.detectors.base import point_in_polygon
x, y = 150, 150  # Bbox center
for poly in roi_polygons:
    is_inside = point_in_polygon(x, y, poly)
    print(f"Point ({x},{y}) in {poly}: {is_inside}")
```

## References

- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)
- [IoU Calculation](https://en.wikipedia.org/wiki/Jaccard_index)
- [Ray Casting Algorithm](https://en.wikipedia.org/wiki/Point_in_polygon)
- [Abstract Base Classes in Python](https://docs.python.org/3/library/abc.html)

---

**Summary**: Step 3 provides a robust, extensible detector abstraction layer with event schema, registry pattern, temporal confirmation, ROI filtering, and YOLO utilities. Total implementation: 844 lines across 2 files. All validation checks passed. Ready for specific detector implementations.
