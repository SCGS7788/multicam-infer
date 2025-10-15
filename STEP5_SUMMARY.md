# Step 5: Publisher Implementation - Complete Summary

## Overview

Step 5 implements three AWS service publishers for sending detection events to Kinesis Data Streams, S3, and DynamoDB. All publishers share a common event envelope format and include robust error handling, retry logic, and metrics tracking.

**Validation Status**: ✅ All checks passed (5/5)

## Files Created

### 1. **src/kvs_infer/publisher/kds.py** (383 lines)
Kinesis Data Streams publisher with batching and exponential backoff.

### 2. **src/kvs_infer/publisher/s3.py** (343 lines)
S3 snapshot publisher for JPEG frame storage.

### 3. **src/kvs_infer/publisher/ddb.py** (411 lines)
DynamoDB publisher for persistent event storage.

### 4. **src/kvs_infer/publisher/__init__.py** (13 lines)
Module exports for easy imports.

### 5. **validate_step5.py** (484 lines)
Comprehensive validation script.

**Total Lines**: 1,634 lines

---

## Event Envelope Format

All publishers use a consistent event envelope format:

```json
{
  "event_id": "abc123...",          // SHA1 hash (camera_id:type:label:ts_bucket)
  "camera_id": "camera_1",          // Camera identifier
  "producer": "kvs-infer/1.0",      // Producer version
  "payload": {                       // Actual detection event
    "ts_ms": 1697123456789,
    "type": "weapon",
    "label": "knife",
    "conf": 0.87,
    "bbox": [100, 200, 50, 75],
    "extras": {
      "text": "ABC1234",            // ALPR only
      "ocr_conf": 0.92              // ALPR only
    }
  }
}
```

### Event ID Generation

Event IDs use SHA1 hashing with 1-second bucketing to prevent duplicates:

```python
def _generate_event_id(camera_id, event_type, label, ts_ms):
    """Generate SHA1 event ID with 1-second bucketing."""
    ts_bucket = (ts_ms // 1000) * 1000  # Round to nearest second
    hash_input = f"{camera_id}:{event_type}:{label}:{ts_bucket}"
    return hashlib.sha1(hash_input.encode()).hexdigest()
```

**Example**: `camera_1:weapon:knife:1697123456000` → `abc123def456...`

---

## Publisher Details

### 1. KDS Publisher (kds.py)

**Purpose**: Stream detection events to Kinesis Data Streams with batching and retries.

#### Features

✅ **Batching**: Up to 500 records per `PutRecords` call  
✅ **Exponential Backoff**: `base * (2^attempt) * jitter` where jitter ∈ [0.8, 1.2]  
✅ **Retry Logic**: Handles throttling and transient errors  
✅ **Event Envelope**: Automatic wrapping with `event_id`, `camera_id`, `producer`  
✅ **Partition Key**: Uses `camera_id` for proper sharding  
✅ **Metrics**: Tracks published, failed, retried, batches_sent  

#### Initialization

```python
from kvs_infer.publisher import KDSClient

# Initialize client
kds = KDSClient(
    region="us-east-1",
    stream_name="detection-events",
    batch_size=500,            # Max records per batch
    max_retries=3,             # Retry attempts
    base_backoff_ms=100        # Base backoff in milliseconds
)
```

#### Usage

```python
# Single event
event = {
    "camera_id": "camera_1",
    "payload": {
        "ts_ms": 1697123456789,
        "type": "weapon",
        "label": "knife",
        "conf": 0.87,
        "bbox": [100, 200, 50, 75],
        "extras": {}
    }
}

kds.put_event(event, partition_key="camera_1")

# Multiple events
events = [event1, event2, event3]
kds.put_events(events, partition_key="camera_1")

# Flush remaining batch
kds.flush()

# Get metrics
metrics = kds.get_metrics()
print(f"Published: {metrics['published']}, Failed: {metrics['failed']}")
```

#### Retry Logic

```python
def _send_batch_with_retries(batch):
    """Send batch with exponential backoff + jitter."""
    for attempt in range(max_retries):
        try:
            response = kinesis.put_records(...)
            return response
        except ProvisionedThroughputExceededException:
            # Exponential backoff with jitter
            sleep_ms = base_backoff_ms * (2 ** attempt)
            jitter = random.uniform(0.8, 1.2)
            time.sleep((sleep_ms * jitter) / 1000)
        except ServiceUnavailable:
            # Retry transient errors
            continue
```

**Backoff Examples**:
- Attempt 0: 100ms × 2^0 × [0.8-1.2] = 80-120ms
- Attempt 1: 100ms × 2^1 × [0.8-1.2] = 160-240ms
- Attempt 2: 100ms × 2^2 × [0.8-1.2] = 320-480ms

#### Batch Processing

- **Buffer Size**: 500 records (Kinesis limit per `PutRecords`)
- **Auto-Flush**: Triggered when buffer reaches 500 records
- **Manual Flush**: Call `flush()` to send remaining records

#### Structured Logging

```python
logger.info(
    "KDS batch published",
    extra={
        "stream_name": "detection-events",
        "record_count": 250,
        "attempt": 1,
        "published": 250,
        "failed": 0
    }
)
```

---

### 2. S3 Publisher (s3.py)

**Purpose**: Save JPEG snapshots of frames to S3 with optional bounding box annotations.

#### Features

✅ **JPEG Encoding**: `cv2.imencode` with configurable quality (0-100)  
✅ **Key Format**: `{prefix}/{camera_id}/{ts_ms}.jpg`  
✅ **Presigned URLs**: Generate shareable URLs with expiration  
✅ **Bbox Drawing**: Optional annotation with `cv2.rectangle` + `putText`  
✅ **S3 Metadata**: Attach camera_id, timestamp, quality, frame shape  
✅ **Metrics**: Tracks saved, failed, bytes_uploaded  

#### Initialization

```python
from kvs_infer.publisher import S3Snapshot

# Initialize client
s3 = S3Snapshot(
    bucket="detection-snapshots",
    prefix="snapshots",         # S3 prefix
    region="us-east-1",
    jpeg_quality=90             # 0-100 (higher = better quality)
)
```

#### Usage

##### Basic Save

```python
import cv2

# Read frame
frame = cv2.imread("frame.jpg")

# Save to S3
key = s3.save(
    frame=frame,
    camera_id="camera_1",
    ts_ms=1697123456789,
    extra_metadata={"event_type": "weapon"}
)

print(f"Saved to: s3://detection-snapshots/{key}")
# Output: s3://detection-snapshots/snapshots/camera_1/1697123456789.jpg
```

##### Save with Bounding Boxes

```python
# Detection results
detections = [
    {
        "bbox": [100, 200, 50, 75],
        "label": "knife",
        "conf": 0.87
    }
]

# Save with annotations
key = s3.save_with_bbox(
    frame=frame,
    camera_id="camera_1",
    ts_ms=1697123456789,
    detections=detections,
    draw_labels=True            # Draw label + confidence
)
```

##### Get Presigned URL

```python
# Generate shareable URL (expires in 1 hour)
url = s3.get_url(key, expires_in=3600)
print(f"Share URL: {url}")
# Output: https://detection-snapshots.s3.amazonaws.com/snapshots/camera_1/...
```

#### JPEG Encoding

```python
def save(frame, camera_id, ts_ms):
    """Encode frame as JPEG and upload to S3."""
    # Encode with cv2
    success, encoded = cv2.imencode(
        '.jpg',
        frame,
        [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    )
    
    if not success:
        raise RuntimeError("JPEG encoding failed")
    
    # Convert to bytes
    jpeg_bytes = encoded.tobytes()
    
    # Upload to S3
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=jpeg_bytes,
        ContentType='image/jpeg',
        Metadata={
            "camera_id": camera_id,
            "timestamp_ms": str(ts_ms),
            "jpeg_quality": str(jpeg_quality),
            "frame_shape": f"{frame.shape[0]}x{frame.shape[1]}"
        }
    )
```

#### Key Generation

```python
def _generate_key(camera_id, ts_ms):
    """Generate S3 key with hierarchical structure."""
    return f"{prefix}/{camera_id}/{ts_ms}.jpg"
```

**Example Keys**:
- `snapshots/camera_1/1697123456789.jpg`
- `snapshots/camera_2/1697123457890.jpg`

#### Bbox Drawing

```python
def save_with_bbox(frame, camera_id, ts_ms, detections, draw_labels=True):
    """Draw bounding boxes and save."""
    annotated = frame.copy()
    
    for det in detections:
        x, y, w, h = det["bbox"]
        
        # Draw green rectangle
        cv2.rectangle(
            annotated,
            (x, y),
            (x + w, y + h),
            color=(0, 255, 0),
            thickness=2
        )
        
        if draw_labels:
            label = f"{det['label']} {det['conf']:.2f}"
            
            # Draw label background
            cv2.rectangle(
                annotated,
                (x, y - 20),
                (x + len(label) * 10, y),
                color=(0, 255, 0),
                thickness=-1  # Filled
            )
            
            # Draw label text
            cv2.putText(
                annotated,
                label,
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1
            )
    
    # Save annotated frame
    return self.save(annotated, camera_id, ts_ms)
```

#### Structured Logging

```python
logger.info(
    "S3 snapshot saved",
    extra={
        "bucket": "detection-snapshots",
        "key": "snapshots/camera_1/1697123456789.jpg",
        "camera_id": "camera_1",
        "ts_ms": 1697123456789,
        "size_bytes": 45678,
        "jpeg_quality": 90
    }
)
```

---

### 3. DynamoDB Publisher (ddb.py)

**Purpose**: Persist detection events to DynamoDB table for queryability and retention.

#### Features

✅ **Float-to-Decimal**: Automatic conversion for DynamoDB compatibility  
✅ **Batch Writing**: Up to 25 items per batch (DynamoDB limit)  
✅ **TTL Support**: Automatic expiration after configured days  
✅ **Query by Camera**: GSI support for time-range queries  
✅ **Decimal-to-Float**: Conversion for JSON serialization  
✅ **Metrics**: Tracks written, failed, batches_sent  

#### Initialization

```python
from kvs_infer.publisher import DDBWriter

# Initialize writer
ddb = DDBWriter(
    table_name="events-table",
    region="us-east-1",
    ttl_days=30                # Expire after 30 days (None = no expiration)
)
```

#### Usage

##### Single Event

```python
# Event envelope
event = {
    "event_id": "abc123...",
    "camera_id": "camera_1",
    "producer": "kvs-infer/1.0",
    "payload": {
        "ts_ms": 1697123456789,
        "type": "weapon",
        "label": "knife",
        "conf": 0.87,
        "bbox": [100, 200, 50, 75],
        "extras": {}
    }
}

# Write to DynamoDB
ddb.put_event(event)
```

##### Batch Write

```python
# Multiple events
events = [event1, event2, event3]

# Write batch (auto-chunks into 25-item batches)
ddb.put_events(events)
```

##### Query by Camera

```python
# Query events for camera_1 in last hour
import time
now_ms = int(time.time() * 1000)
hour_ago_ms = now_ms - (3600 * 1000)

events = ddb.query_by_camera(
    camera_id="camera_1",
    start_ts_ms=hour_ago_ms,
    end_ts_ms=now_ms,
    limit=100
)

for event in events:
    print(f"{event['type']}: {event['label']} @ {event['ts_ms']}")
```

#### Table Schema

```
Table: events-table

Partition Key: event_id (String)    - SHA1 hash for deduplication
Sort Key: ts_ms (Number)             - Timestamp in milliseconds

Attributes:
  - camera_id (String)
  - producer (String)
  - type (String)                    - "weapon", "fire", "smoke", "alpr"
  - label (String)                   - "knife", "gun", "ABC1234", etc.
  - conf (Number/Decimal)            - Confidence score
  - bbox (List<Number>)              - [x, y, w, h]
  - extras (Map)                     - Additional metadata
  - ttl (Number)                     - Expiration timestamp (optional)

GSI: camera_id-ts_ms-index
  Partition Key: camera_id (String)
  Sort Key: ts_ms (Number)
```

#### Float-to-Decimal Conversion

DynamoDB does not support native floats. All float values must be converted to `Decimal`:

```python
from decimal import Decimal

def _convert_floats_to_decimal(obj):
    """Convert floats to Decimal recursively."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats_to_decimal(item) for item in obj]
    else:
        return obj
```

**Example**:
- Input: `{"conf": 0.87, "bbox": [100.5, 200.3, 50.0, 75.0]}`
- Output: `{"conf": Decimal("0.87"), "bbox": [Decimal("100.5"), ...]}`

#### TTL (Time-to-Live)

```python
def _prepare_item(event):
    """Add TTL if configured."""
    item = {...}  # Flatten event envelope
    
    if ttl_days is not None:
        import time
        ttl_timestamp = int(time.time()) + (ttl_days * 86400)
        item["ttl"] = ttl_timestamp
    
    return item
```

**Example**: 30-day retention
- Current time: 1697123456 (Unix timestamp)
- TTL: 1697123456 + (30 × 86400) = 1699715456
- DynamoDB automatically deletes item after TTL expires

#### Batch Writing

```python
def put_events(events):
    """Write batch with automatic chunking."""
    batch_size = 25  # DynamoDB limit
    
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        
        with table.batch_writer() as batch_writer:
            for event in batch:
                item = _prepare_item(event)
                batch_writer.put_item(Item=item)
```

#### Structured Logging

```python
logger.info(
    "DDB event written",
    extra={
        "table_name": "events-table",
        "event_id": "abc123...",
        "camera_id": "camera_1",
        "event_type": "weapon"
    }
)
```

---

## Metrics Tracking

All publishers track metrics for monitoring:

```python
# KDS metrics
{
    "published": 1250,        # Successfully published records
    "failed": 3,              # Failed records
    "retried": 7,             # Retry attempts
    "batches_sent": 3         # Number of batches
}

# S3 metrics
{
    "saved": 340,             # Successfully saved snapshots
    "failed": 2,              # Failed uploads
    "bytes_uploaded": 12345678  # Total bytes uploaded
}

# DDB metrics
{
    "written": 890,           # Successfully written events
    "failed": 1,              # Failed writes
    "batches_sent": 36        # Number of batches
}
```

### Accessing Metrics

```python
# Get current metrics
kds_metrics = kds.get_metrics()
s3_metrics = s3.get_metrics()
ddb_metrics = ddb.get_metrics()

# Reset metrics
kds.reset_metrics()
s3.reset_metrics()
ddb.reset_metrics()
```

---

## Error Handling

All publishers implement robust error handling:

### 1. Client Errors (4xx)

```python
try:
    response = client.put_records(...)
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_message = e.response['Error']['Message']
    
    logger.error(
        f"AWS client error: {error_code} - {error_message}",
        extra={
            "error_code": error_code,
            "error_message": error_message
        }
    )
```

**Common Errors**:
- `ProvisionedThroughputExceededException` → Retry with backoff
- `ResourceNotFoundException` → Table/stream does not exist
- `ValidationException` → Invalid parameters

### 2. Service Errors (5xx)

```python
except Exception as e:
    if "ServiceUnavailable" in str(e):
        # Retry transient errors
        continue
    else:
        # Log and fail
        logger.error(f"Unexpected error: {e}", exc_info=True)
```

### 3. Encoding Errors

```python
success, encoded = cv2.imencode('.jpg', frame, [...])
if not success:
    raise RuntimeError("JPEG encoding failed")
```

---

## Integration Example

Complete example integrating all publishers:

```python
from kvs_infer.publisher import KDSClient, S3Snapshot, DDBWriter

# Initialize publishers
kds = KDSClient(
    region="us-east-1",
    stream_name="detection-events",
    batch_size=500
)

s3 = S3Snapshot(
    bucket="detection-snapshots",
    prefix="snapshots",
    jpeg_quality=90
)

ddb = DDBWriter(
    table_name="events-table",
    ttl_days=30
)

# Process detection event
def process_detection(frame, camera_id, detection_result):
    """
    Process detection and publish to all services.
    
    Args:
        frame: CV2 frame (numpy array)
        camera_id: Camera identifier
        detection_result: Dict with type, label, conf, bbox, extras
    """
    import time
    
    # Build event payload
    ts_ms = int(time.time() * 1000)
    
    event = {
        "camera_id": camera_id,
        "payload": {
            "ts_ms": ts_ms,
            "type": detection_result["type"],
            "label": detection_result["label"],
            "conf": detection_result["conf"],
            "bbox": detection_result["bbox"],
            "extras": detection_result.get("extras", {})
        }
    }
    
    # 1. Send to Kinesis Data Streams
    kds.put_event(event, partition_key=camera_id)
    
    # 2. Save snapshot to S3 with bounding box
    s3_key = s3.save_with_bbox(
        frame=frame,
        camera_id=camera_id,
        ts_ms=ts_ms,
        detections=[detection_result],
        draw_labels=True
    )
    
    # 3. Store in DynamoDB (wrapped in envelope by KDS)
    # Note: KDS creates the event envelope, DDB expects full envelope
    event_envelope = kds._create_event_envelope(event, "kvs-infer/1.0")
    ddb.put_event(event_envelope)
    
    return {
        "kds": "published",
        "s3_key": s3_key,
        "ddb": "written"
    }

# Example usage
import cv2

frame = cv2.imread("frame.jpg")
camera_id = "camera_1"

detection = {
    "type": "weapon",
    "label": "knife",
    "conf": 0.87,
    "bbox": [100, 200, 50, 75],
    "extras": {}
}

result = process_detection(frame, camera_id, detection)
print(f"Published to KDS, saved to S3: {result['s3_key']}, written to DDB")

# Flush remaining KDS batch
kds.flush()

# Check metrics
print(f"KDS: {kds.get_metrics()}")
print(f"S3: {s3.get_metrics()}")
print(f"DDB: {ddb.get_metrics()}")
```

---

## Configuration

Publishers can be configured via environment variables or config file:

### Environment Variables

```bash
# KDS
export KDS_REGION="us-east-1"
export KDS_STREAM_NAME="detection-events"
export KDS_BATCH_SIZE=500
export KDS_MAX_RETRIES=3
export KDS_BASE_BACKOFF_MS=100

# S3
export S3_REGION="us-east-1"
export S3_BUCKET="detection-snapshots"
export S3_PREFIX="snapshots"
export S3_JPEG_QUALITY=90

# DynamoDB
export DDB_REGION="us-east-1"
export DDB_TABLE_NAME="events-table"
export DDB_TTL_DAYS=30
```

### Config File (config/defaults.yaml)

```yaml
publishers:
  kds:
    enabled: true
    region: us-east-1
    stream_name: detection-events
    batch_size: 500
    max_retries: 3
    base_backoff_ms: 100
  
  s3:
    enabled: true
    region: us-east-1
    bucket: detection-snapshots
    prefix: snapshots
    jpeg_quality: 90
  
  ddb:
    enabled: false
    region: us-east-1
    table_name: events-table
    ttl_days: 30
```

---

## AWS Resource Setup

### 1. Kinesis Data Stream

```bash
aws kinesis create-stream \
  --stream-name detection-events \
  --shard-count 2 \
  --region us-east-1
```

**Shard Capacity**:
- 1 shard = 1 MB/sec write, 2 MB/sec read
- 1 shard = 1,000 records/sec write
- Adjust shard count based on camera count and event rate

### 2. S3 Bucket

```bash
aws s3api create-bucket \
  --bucket detection-snapshots \
  --region us-east-1
```

**Lifecycle Policy** (optional):
```json
{
  "Rules": [
    {
      "Id": "expire-old-snapshots",
      "Status": "Enabled",
      "Prefix": "snapshots/",
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

### 3. DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name events-table \
  --attribute-definitions \
    AttributeName=event_id,AttributeType=S \
    AttributeName=ts_ms,AttributeType=N \
    AttributeName=camera_id,AttributeType=S \
  --key-schema \
    AttributeName=event_id,KeyType=HASH \
    AttributeName=ts_ms,KeyType=RANGE \
  --global-secondary-indexes \
    "IndexName=camera_id-ts_ms-index,\
     KeySchema=[{AttributeName=camera_id,KeyType=HASH},{AttributeName=ts_ms,KeyType=RANGE}],\
     Projection={ProjectionType=ALL},\
     ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
  --provisioned-throughput \
    ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1

# Enable TTL
aws dynamodb update-time-to-live \
  --table-name events-table \
  --time-to-live-specification \
    "Enabled=true,AttributeName=ttl"
```

---

## IAM Permissions

### KDS Publisher

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:PutRecord",
        "kinesis:PutRecords"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/detection-events"
    }
  ]
}
```

### S3 Publisher

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::detection-snapshots/snapshots/*"
    }
  ]
}
```

### DynamoDB Publisher

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:123456789012:table/events-table",
        "arn:aws:dynamodb:us-east-1:123456789012:table/events-table/index/*"
      ]
    }
  ]
}
```

---

## Testing

### Unit Tests

```python
import pytest
from kvs_infer.publisher import KDSClient, S3Snapshot, DDBWriter

def test_kds_event_envelope():
    """Test event envelope generation."""
    kds = KDSClient(region="us-east-1", stream_name="test")
    
    event = {
        "camera_id": "camera_1",
        "payload": {
            "ts_ms": 1697123456789,
            "type": "weapon",
            "label": "knife",
            "conf": 0.87,
            "bbox": [100, 200, 50, 75],
            "extras": {}
        }
    }
    
    envelope = kds._create_event_envelope(event, "kvs-infer/1.0")
    
    assert "event_id" in envelope
    assert envelope["camera_id"] == "camera_1"
    assert envelope["producer"] == "kvs-infer/1.0"
    assert envelope["payload"]["type"] == "weapon"

def test_s3_jpeg_encoding():
    """Test JPEG encoding."""
    import numpy as np
    
    s3 = S3Snapshot(bucket="test", prefix="test")
    
    # Create dummy frame
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Encode
    success, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    
    assert success
    assert len(encoded) > 0

def test_ddb_float_to_decimal():
    """Test float-to-Decimal conversion."""
    from kvs_infer.publisher.ddb import _convert_floats_to_decimal
    
    obj = {
        "conf": 0.87,
        "bbox": [100.5, 200.3, 50.0, 75.0]
    }
    
    converted = _convert_floats_to_decimal(obj)
    
    assert isinstance(converted["conf"], Decimal)
    assert str(converted["conf"]) == "0.87"
```

---

## Performance Optimization

### 1. KDS Batching

- **Batch Size**: 500 records (maximize throughput)
- **Flush Frequency**: Every 1 second or when batch full
- **Shard Count**: Scale based on event rate (1 shard = 1,000 records/sec)

```python
# Efficient batching
for i in range(1000):
    kds.put_event(event, partition_key=camera_id)
    # Auto-flushes every 500 records

# Manual flush for remaining
kds.flush()
```

### 2. S3 Upload Optimization

- **JPEG Quality**: 85-90 (balance quality vs size)
- **Frame Resolution**: Resize if needed (e.g., 1920x1080 → 1280x720)
- **Multipart Upload**: For large files (>5MB)

```python
# Resize frame before saving
import cv2

frame_resized = cv2.resize(frame, (1280, 720))
s3.save(frame_resized, camera_id, ts_ms)
```

### 3. DDB Write Optimization

- **Batch Size**: 25 items (maximize throughput)
- **Provisioned Capacity**: Scale based on write rate
- **On-Demand Mode**: For unpredictable workloads

```python
# Efficient batch writing
events = [...]  # 100 events
ddb.put_events(events)  # Auto-chunks into 4 batches of 25
```

---

## Monitoring

### CloudWatch Metrics

**KDS**:
- `IncomingRecords`: Records received
- `WriteProvisionedThroughputExceeded`: Throttling
- `PutRecords.Latency`: API latency

**S3**:
- `PutRequests`: Upload requests
- `4xxErrors`: Client errors
- `5xxErrors`: Server errors

**DynamoDB**:
- `ConsumedWriteCapacityUnits`: Write capacity
- `UserErrors`: Client errors
- `SystemErrors`: Server errors

### Custom Metrics

```python
import time

# Track end-to-end latency
start = time.time()

kds.put_event(event, partition_key=camera_id)
s3.save(frame, camera_id, ts_ms)
ddb.put_event(event_envelope)

latency_ms = (time.time() - start) * 1000
print(f"Total latency: {latency_ms:.2f}ms")
```

---

## Troubleshooting

### Issue: KDS Throttling

**Symptoms**: `ProvisionedThroughputExceededException`, high retry count

**Solutions**:
1. Increase shard count: `aws kinesis update-shard-count --stream-name ... --target-shard-count 4`
2. Reduce batch size: `batch_size=250`
3. Increase backoff: `base_backoff_ms=200`

### Issue: S3 Upload Failures

**Symptoms**: High `failed` count in S3 metrics

**Solutions**:
1. Check IAM permissions: `s3:PutObject`
2. Verify bucket exists: `aws s3 ls s3://detection-snapshots`
3. Check region mismatch: Ensure bucket and client are in same region

### Issue: DDB Float Errors

**Symptoms**: `ValidationException: One or more parameter values were invalid: Type mismatch for key conf`

**Solutions**:
1. Verify float-to-Decimal conversion is working
2. Check for `NaN` or `Infinity` values (not supported)
3. Use `Decimal(str(float_value))` instead of `Decimal(float_value)`

---

## Next Steps

1. **Integration**: Wire publishers in `CameraWorker` processing loop
2. **Configuration**: Add publisher config to `config/defaults.yaml`
3. **Testing**: Add integration tests with LocalStack/Moto
4. **Monitoring**: Add CloudWatch alarms for metrics
5. **Documentation**: Update README with publisher setup instructions

---

## Summary

✅ **KDS Publisher**: Batching (500 records), exponential backoff with jitter, retry logic  
✅ **S3 Publisher**: JPEG encoding, presigned URLs, bbox drawing  
✅ **DDB Publisher**: Float-to-Decimal conversion, batch writing, TTL support  
✅ **Event Envelope**: SHA1 event_id, consistent format across all publishers  
✅ **Error Handling**: Robust client/server error handling with logging  
✅ **Metrics**: Comprehensive tracking for monitoring  
✅ **Validation**: All checks passed (5/5)  

**Total Implementation**: 1,634 lines of production-ready code

---

**Validation Status**: ✅ All checks passed (5/5)

```bash
python3 validate_step5.py
# ✓ KDS Publisher: PASSED
# ✓ S3 Publisher: PASSED
# ✓ DynamoDB Publisher: PASSED
# ✓ Publisher Module: PASSED
# ✓ Event Envelope Format: PASSED
```
