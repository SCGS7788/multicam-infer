# Configuration Guide for kvs-infer

## Overview

kvs-infer uses a YAML-based configuration system with Pydantic v2 for validation. Each camera can be configured independently with its own detection pipeline, ROI settings, and routing rules.

## Configuration Structure

```
config/
├── cameras.example.yaml    # Full example with 4 cameras
└── cameras.yaml           # Your configuration (copy from example)
```

## Top-Level Sections

### 1. Global Configuration

#### AWS Settings
```yaml
aws:
  region: us-east-1         # Default AWS region
```

#### Publishers (Global Defaults)
```yaml
publishers:
  kds_stream: detection-events     # Default Kinesis Data Stream
  s3_bucket: my-bucket             # Default S3 bucket
  ddb_table: null                  # Optional DynamoDB table
```

#### Service Settings
```yaml
service:
  hls_session_seconds: 300         # HLS URL refresh (60-43200)
  reconnect_delay_seconds: 5       # Reconnect delay (1-300)
```

#### Snapshots Settings
```yaml
snapshots:
  enabled: true
  jpeg_quality: 90                 # 1-100
  image_format: jpg                # jpg or png
```

#### Device & Monitoring
```yaml
device: cpu                        # cpu, cuda:0, cuda:1, etc.
metrics_enabled: true
metrics_port: 9090
log_level: INFO
log_format: json                   # json or text
```

---

## Camera Configuration

Each camera in the `cameras:` list has these sections:

### Basic Settings

```yaml
- id: camera-01                    # Unique ID (alphanumeric, -, _)
  kvs_stream_name: my-kvs-stream   # KVS stream name
  enabled: true                    # Enable/disable camera
```

**Validation:**
- `id` must be unique across all cameras
- `id` can only contain: `a-z`, `A-Z`, `0-9`, `-`, `_`
- `kvs_stream_name` can be shared (multiple cameras, one stream)

### Playback Settings

```yaml
playback:
  mode: HLS                        # HLS or GETMEDIA
  retention_required: true         # Warn if false for HLS
```

**Important:** HLS mode requires KVS data retention enabled. If `retention_required: true`, a warning is logged if retention is not detected.

### Frame Processing

```yaml
fps_target: 5                      # Target FPS (1-30, null = all frames)
resize:                            # Optional frame resize
  width: 1280                      # Must be even number
  height: 720                      # Must be even number
```

### Region of Interest (ROI)

```yaml
roi:
  enabled: true
  polygons:
    - name: zone-1                 # Optional name
      points:                      # At least 3 points
        - [100, 200]               # [x, y] coordinates
        - [500, 200]
        - [500, 600]
        - [100, 600]
    - name: zone-2
      points:
        - [700, 300]
        - [1000, 300]
        - [1000, 700]
        - [700, 700]
```

**Validation:**
- Each polygon needs ≥3 points
- Coordinates must be non-negative integers
- When `enabled: true`, at least one polygon required

---

## Detection Pipeline

The `pipeline:` list defines detectors to run **in order** for each frame.

### 1. Weapon Detection

```yaml
pipeline:
  - type: weapon
    enabled: true
    weapon:
      yolo_weights: s3://bucket/weapon.pt   # S3 or local path
      classes:                              # Classes to detect
        - gun
        - knife
        - rifle
        - pistol
      conf_threshold: 0.6                   # 0.0-1.0
      nms_iou: 0.5                          # 0.0-1.0
      min_box:
        width: 30                           # Minimum pixels
        height: 30
      temporal_confirm:                     # Optional
        frames: 3                           # Confirm over N frames
        iou_threshold: 0.5                  # Tracking IoU
```

**Temporal Confirmation:**
- Reduces false positives
- Requires detection in N consecutive frames
- Uses IoU for tracking across frames
- Adds latency = (N-1) * frame_time

### 2. Fire/Smoke Detection

```yaml
pipeline:
  - type: fire_smoke
    enabled: true
    fire_smoke:
      yolo_weights: /models/fire.pt         # Custom model required
      conf_threshold: 0.5
      nms_iou: 0.4
      min_box:
        width: 40
        height: 40
```

**Note:** Fire/smoke detection requires a custom-trained YOLO model.

### 3. ALPR (License Plate Recognition)

```yaml
pipeline:
  - type: alpr
    enabled: true
    alpr:
      plate_detector_weights: s3://bucket/plate.pt
      ocr_engine: paddleocr             # paddleocr or tesseract
      ocr_lang: en                      # Language code (en, th, etc.)
      conf_threshold: 0.7
      crop_expand: 0.1                  # Expand crop by 10%
      min_box:
        width: 50
        height: 20
```

**OCR Engines:**
- `paddleocr`: Supports 80+ languages, GPU-accelerated
- `tesseract`: Requires system installation, CPU-only

**Supported Languages:**
- `en`: English
- `th`: Thai
- `zh`: Chinese
- [Full list](https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_en/multi_languages_en.md)

---

## Routing Configuration

Controls where events and snapshots are sent.

### Event Routing

```yaml
routing:
  events:
    to_kds: true                        # Send to Kinesis
    kds_stream_override: null           # Override global stream
```

**Override Example:**
```yaml
kds_stream_override: fire-alerts      # Send to different stream
```

### Snapshot Routing

```yaml
routing:
  snapshot:
    to_s3: true                         # Upload to S3
    prefix: snaps/${camera_id}/         # S3 key prefix
    on_event_only: true                 # Only when detections occur
    upload_crops: true                  # Upload detection crops
```

**Variable Expansion:**
- `${camera_id}` → camera's `id` field
- `${ENV_VAR}` → environment variable

**S3 Key Structure:**
```
{prefix}/{date}/{snapshot|crop}/{timestamp}[_{detection_id}].jpg

Example:
snaps/front-entrance/2025-10-12/snapshot/20251012_143052_123.jpg
snaps/front-entrance/2025-10-12/crop/20251012_143052_123_det001.jpg
```

---

## Environment Variables

The config supports environment variable expansion:

```yaml
publishers:
  s3_bucket: ${S3_BUCKET}           # From environment
  kds_stream: ${KDS_STREAM_NAME}

cameras:
  - id: cam-01
    kvs_stream_name: ${CAM01_STREAM}
```

Set in shell:
```bash
export S3_BUCKET=my-bucket
export KDS_STREAM_NAME=events
export CAM01_STREAM=camera-01-stream
```

---

## Validation Rules

### Strict Type Checking

Pydantic validates all types:
```yaml
fps_target: 5         # ✅ int
fps_target: "5"       # ❌ string not allowed
conf_threshold: 0.6   # ✅ float
conf_threshold: "0.6" # ❌ string not allowed
```

### Range Validation

```yaml
conf_threshold: 0.6   # ✅ 0.0-1.0
conf_threshold: 1.5   # ❌ > 1.0

fps_target: 15        # ✅ 1-30
fps_target: 60        # ❌ > 30

jpeg_quality: 90      # ✅ 1-100
jpeg_quality: 150     # ❌ > 100
```

### Required Fields

Each detector type requires its specific config:

```yaml
# ❌ WRONG - type is weapon but no weapon: config
- type: weapon
  enabled: true

# ✅ CORRECT
- type: weapon
  enabled: true
  weapon:
    yolo_weights: s3://bucket/model.pt
    classes: [gun, knife]
```

### Unique Constraints

```yaml
cameras:
  - id: cam-01        # ✅
  - id: cam-02        # ✅
  - id: cam-01        # ❌ duplicate ID
```

### HLS Retention Warning

```yaml
playback:
  mode: HLS
  retention_required: false    # ⚠️  Warning logged
```

If `retention_required: false` with HLS mode, a warning is logged at startup.

---

## Complete Examples

### Example 1: High-Security Entrance

```yaml
- id: main-entrance
  kvs_stream_name: entrance-hd-stream
  enabled: true
  
  playback:
    mode: HLS
    retention_required: true
  
  fps_target: 10                    # High FPS for security
  resize:
    width: 1920
    height: 1080
  
  roi:
    enabled: true
    polygons:
      - name: door-area
        points: [[200, 300], [800, 300], [800, 900], [200, 900]]
  
  pipeline:
    - type: weapon
      enabled: true
      weapon:
        yolo_weights: s3://models/weapon-v2.pt
        classes: [gun, knife, rifle]
        conf_threshold: 0.7
        nms_iou: 0.5
        min_box: {width: 40, height: 40}
        temporal_confirm:
          frames: 5                 # High certainty
          iou_threshold: 0.6
  
  routing:
    events:
      to_kds: true
      kds_stream_override: security-alerts
    snapshot:
      to_s3: true
      prefix: security/${camera_id}/
      on_event_only: true
      upload_crops: true
```

### Example 2: Parking Lot ALPR

```yaml
- id: parking-exit
  kvs_stream_name: parking-stream
  enabled: true
  
  playback:
    mode: HLS
    retention_required: true
  
  fps_target: 2                     # Low FPS sufficient
  resize: null                      # Native resolution
  
  roi:
    enabled: true
    polygons:
      - name: exit-lane
        points: [[400, 500], [1200, 500], [1200, 900], [400, 900]]
  
  pipeline:
    - type: alpr
      enabled: true
      alpr:
        plate_detector_weights: s3://models/thai-plate.pt
        ocr_engine: paddleocr
        ocr_lang: th
        conf_threshold: 0.75
        crop_expand: 0.15
        min_box: {width: 60, height: 25}
  
  routing:
    events:
      to_kds: true
      kds_stream_override: alpr-events
    snapshot:
      to_s3: true
      prefix: alpr/${camera_id}/
      on_event_only: true
      upload_crops: true
```

### Example 3: Fire Monitoring

```yaml
- id: warehouse-01
  kvs_stream_name: warehouse-stream
  enabled: true
  
  playback:
    mode: HLS
    retention_required: true
  
  fps_target: 3
  resize: {width: 1280, height: 720}
  
  roi:
    enabled: false                  # Monitor entire area
  
  pipeline:
    - type: fire_smoke
      enabled: true
      fire_smoke:
        yolo_weights: /models/fire-v3.pt
        conf_threshold: 0.5
        nms_iou: 0.4
        min_box: {width: 50, height: 50}
  
  routing:
    events:
      to_kds: true
      kds_stream_override: fire-alerts
    snapshot:
      to_s3: true
      prefix: fire/${camera_id}/
      on_event_only: true
      upload_crops: false           # Full frames only
```

---

## Testing Configuration

### 1. Syntax Check

```bash
python3.11 test_config_syntax.py
```

### 2. Validation Test (requires dependencies)

```bash
pip install pydantic pyyaml
python3.11 -c "from kvs_infer.config import load_yaml; config = load_yaml('config/cameras.example.yaml'); print(f'Loaded {len(config.cameras)} cameras')"
```

### 3. Dry Run

```bash
./run.sh --config config/cameras.yaml --log-format text
# Press Ctrl+C after startup to verify config
```

---

## Troubleshooting

### Validation Errors

**Error:** `Camera ID cannot be empty`
```yaml
# ❌ WRONG
- id: ""

# ✅ CORRECT
- id: camera-01
```

**Error:** `Duplicate camera IDs found`
```yaml
# ❌ WRONG
cameras:
  - id: cam1
  - id: cam1

# ✅ CORRECT
cameras:
  - id: cam1
  - id: cam2
```

**Error:** `Detector type 'weapon' requires 'weapon' configuration`
```yaml
# ❌ WRONG
- type: weapon
  enabled: true

# ✅ CORRECT
- type: weapon
  enabled: true
  weapon:
    yolo_weights: s3://bucket/model.pt
    classes: [gun]
```

**Error:** `ROI polygon must have at least 3 points`
```yaml
# ❌ WRONG
roi:
  enabled: true
  polygons:
    - points: [[100, 100], [200, 200]]  # Only 2 points

# ✅ CORRECT
roi:
  enabled: true
  polygons:
    - points: [[100, 100], [200, 100], [200, 200]]
```

### YAML Syntax Errors

**Error:** Contains tab character
```yaml
# ❌ WRONG (tabs)
cameras:
	- id: cam1         # Tab character

# ✅ CORRECT (spaces)
cameras:
  - id: cam1          # 2 spaces
```

**Error:** Inconsistent indentation
```yaml
# ❌ WRONG
cameras:
  - id: cam1
   enabled: true      # 1 space (should be 4)

# ✅ CORRECT
cameras:
  - id: cam1
    enabled: true     # 4 spaces
```

---

## Best Practices

1. **Start Simple:** Begin with one camera, one detector
2. **Use ROI:** Improve performance and reduce false positives
3. **Tune Thresholds:** Start high (0.7), lower if needed
4. **Monitor Metrics:** Watch FPS, inference time via Prometheus
5. **Test Incrementally:** Enable cameras one at a time
6. **Use Temporal Confirmation:** For critical detections (weapons)
7. **Environment Variables:** Use for secrets and deployment-specific values
8. **Validate Often:** Run `test_config_syntax.py` after changes

---

## See Also

- `cameras.example.yaml` - Full working example
- `README.md` - Project documentation
- `QUICKSTART.md` - Getting started guide
