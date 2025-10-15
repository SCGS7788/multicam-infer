# Configuration Quick Reference

## File Locations
```
config/cameras.example.yaml  → Example with 4 cameras
config/cameras.yaml          → Your config (copy from example)
src/kvs_infer/config.py      → Pydantic models
CONFIG.md                    → Full documentation
```

## Quick Start
```bash
# 1. Copy example
cp config/cameras.example.yaml config/cameras.yaml

# 2. Edit (required fields)
vim config/cameras.yaml
  - id: YOUR_CAMERA_ID
  - kvs_stream_name: YOUR_KVS_STREAM
  - publishers.s3_bucket: YOUR_S3_BUCKET

# 3. Test
PYTHONPATH=src python -c "from kvs_infer.config import load_yaml; load_yaml('config/cameras.yaml')"
```

## Minimal Camera Config
```yaml
cameras:
  - id: cam-01                       # Required: unique ID
    kvs_stream_name: my-stream       # Required: KVS stream
    enabled: true
    pipeline: []                     # No detectors
```

## Camera with Weapon Detection
```yaml
cameras:
  - id: entrance
    kvs_stream_name: entrance-stream
    fps_target: 5
    pipeline:
      - type: weapon
        enabled: true
        weapon:
          yolo_weights: s3://bucket/weapon.pt
          classes: [gun, knife]
          conf_threshold: 0.6
```

## Camera with ALPR
```yaml
cameras:
  - id: parking
    kvs_stream_name: parking-stream
    fps_target: 2
    pipeline:
      - type: alpr
        enabled: true
        alpr:
          plate_detector_weights: s3://bucket/plate.pt
          ocr_engine: paddleocr
          ocr_lang: en
          conf_threshold: 0.7
```

## ROI Example
```yaml
roi:
  enabled: true
  polygons:
    - name: zone1
      points:
        - [100, 200]
        - [500, 200]
        - [500, 600]
        - [100, 600]
```

## Routing Example
```yaml
routing:
  events:
    to_kds: true
    kds_stream_override: alerts       # Optional override
  snapshot:
    to_s3: true
    prefix: snaps/${camera_id}/       # ${camera_id} expands
    on_event_only: true
    upload_crops: true
```

## Environment Variables
```bash
# Set in shell
export S3_BUCKET=my-bucket
export KDS_STREAM=events

# Use in YAML
publishers:
  s3_bucket: ${S3_BUCKET}
  kds_stream: ${KDS_STREAM}
```

## Validation Ranges
```yaml
conf_threshold: 0.5      # 0.0 - 1.0
fps_target: 5            # 1 - 30
jpeg_quality: 90         # 1 - 100
hls_session_seconds: 300 # 60 - 43200
```

## Common Errors

**Duplicate IDs:**
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

**Missing Detector Config:**
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

**Invalid Camera ID:**
```yaml
# ❌ WRONG
id: "camera 01"        # Spaces not allowed

# ✅ CORRECT
id: camera-01          # Use hyphens
```

## Test Commands
```bash
# Syntax check (no dependencies)
python3.11 test_config_syntax.py

# Full validation (requires pydantic, pyyaml)
python3.11 test_config.py

# Final validation
python3.11 validate_step1.py
```

## Get Help
- Full guide: `CONFIG.md`
- Examples: `config/cameras.example.yaml`
- Models: `src/kvs_infer/config.py` (docstrings)
