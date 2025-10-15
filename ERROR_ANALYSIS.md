# 🔍 Error Analysis & Solutions

## ปัญหาที่พบจาก Log

### ❌ 1. Model File Not Found (camera_2)

**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'models/weapon-yolov8n.pt'
```

**สาเหสุ:**
- `camera_2` มี detector config แต่ไม่มีไฟล์ model

**✅ แก้ไข:**
- ✅ แก้แล้ว: เปลี่ยน `detectors:` เป็น `detectors: []` (comment ออก)

---

### ❌ 2. TypeError: cannot unpack non-iterable NoneType

**Error:**
```python
TypeError: cannot unpack non-iterable NoneType object
File "app.py", line 528: frame, ts_ms = self.frame_source.read_frame()
```

**สาเหสุ:**
- `read_frame()` คืนค่า `None` แทนที่จะเป็น tuple `(frame, timestamp)`
- เกิดเมื่อ connection ขาดหาย

**✅ แก้ไข:**
- ✅ แก้แล้ว: เพิ่ม check `if result is None or not isinstance(result, tuple)`

**Code ใหม่:**
```python
# Read frame
result = self.frame_source.read_frame()

# Handle both None and tuple returns
if result is None or not isinstance(result, tuple):
    time.sleep(0.1)
    continue

frame, ts_ms = result
```

---

### ❌ 3. AWS Kinesis Video Streams Connection Error (หลัก)

**Error:**
```
ERROR: Could not connect to the endpoint URL: 
"https://kinesisvideo.ap-southeast-1.amazonaws.com/getDataEndpoint"
```

**สาเหสุที่เป็นไปได้:**

#### 🌐 A. ไม่มี Internet Connection
```bash
# ทดสอบ:
ping kinesisvideo.ap-southeast-1.amazonaws.com
curl https://kinesisvideo.ap-southeast-1.amazonaws.com
```

#### 🔒 B. AWS Credentials ไม่ถูกต้อง/หมดอายุ
```bash
# ตรวจสอบ credentials:
cat ~/.aws/credentials
aws sts get-caller-identity

# ถ้าหมดอายุ:
aws configure
# หรือ
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

#### 🚫 C. KVS Stream ไม่มีอยู่จริง
```bash
# ตรวจสอบว่ามี stream:
aws kinesisvideo list-streams --region ap-southeast-1

# ตรวจสอบ stream เฉพาะ:
aws kinesisvideo describe-stream \
  --stream-name stream-C01 \
  --region ap-southeast-1
```

#### 🔧 D. Network/Firewall/Proxy Issue
```bash
# ถ้าอยู่หลัง Proxy:
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port

# หรือใน config:
aws configure set default.proxy http://proxy:port
```

#### 🏢 E. VPC Endpoint (ถ้ารันใน VPC)
- ต้องมี VPC Endpoint สำหรับ Kinesis Video Streams
- ตรวจสอบ Security Groups

---

## 🛠️ วิธีแก้ไข

### Option 1: ตรวจสอบ AWS Setup

```bash
# 1. ตรวจสอบ credentials
aws sts get-caller-identity

# 2. ตรวจสอบ KVS streams
aws kinesisvideo list-streams --region ap-southeast-1

# 3. ทดสอบ connection
aws kinesisvideo describe-stream \
  --stream-name stream-C01 \
  --region ap-southeast-1
```

**ถ้าผลลัพธ์:**
- ❌ Error: ไม่มี credentials หรือ permissions
- ✅ Success: Stream พร้อมใช้งาน

---

### Option 2: ใช้ Mock/Test Mode (ไม่ต้อง AWS)

ถ้าต้องการทดสอบโดยไม่ต้องเชื่อม AWS:

**แก้ `src/kvs_infer/frame_source/kvs_hls.py`:**

```python
def read_frame(self):
    """Read frame - with fallback for testing."""
    if os.getenv('TEST_MODE') == 'true':
        # Return dummy frame for testing
        import numpy as np
        dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        return dummy_frame, int(time.time() * 1000)
    
    # Normal HLS reading...
```

**รัน:**
```bash
export TEST_MODE=true
./run.sh --config config/cameras.yaml
```

---

### Option 3: ปิดกล้องที่มีปัญหา

**แก้ `config/cameras.yaml`:**

```yaml
cameras:
  camera_1:
    enabled: false  # ปิดไว้ก่อน
    
  camera_2:
    enabled: false  # ปิดไว้ก่อน
    
  camera_3:
    enabled: false
```

---

### Option 4: สร้าง KVS Stream ใหม่

```bash
# 1. สร้าง stream
aws kinesisvideo create-stream \
  --stream-name stream-C01 \
  --region ap-southeast-1 \
  --data-retention-in-hours 24

# 2. เปิด data retention (สำคัญสำหรับ HLS!)
aws kinesisvideo update-stream \
  --stream-name stream-C01 \
  --region ap-southeast-1 \
  --data-retention-in-hours 24

# 3. ตรวจสอบ
aws kinesisvideo describe-stream \
  --stream-name stream-C01 \
  --region ap-southeast-1
```

---

## 📊 สรุปสถานะ

| ปัญหา | สถานะ | แก้ไขยังไง |
|-------|-------|-----------|
| ❌ Model file not found | ✅ แก้แล้ว | Comment detector ใน config |
| ❌ TypeError in read_frame | ✅ แก้แล้ว | เพิ่ม None check |
| ❌ AWS connection error | ⚠️ ต้องตรวจสอบ | ดูด้านล่าง |

---

## 🚀 ขั้นตอนถัดไป

### 1. ตรวจสอบ AWS (ถ้าต้องการใช้จริง)

```bash
# ทดสอบ AWS credentials
aws sts get-caller-identity

# ถ้า error → ต้อง configure credentials
aws configure

# ตรวจสอบ KVS stream
aws kinesisvideo list-streams --region ap-southeast-1
```

### 2. รันระบบใหม่

```bash
# หยุดระบบเดิม
pkill -f "python.*kvs_infer"

# รันใหม่
./run.sh --config config/cameras.yaml
```

### 3. ดู log

```bash
# ดู real-time logs
tail -f <log-file>

# หรือดูใน terminal output
```

---

## 💡 Recommendations

### สำหรับ Development (ไม่มี AWS)

```bash
# 1. ปิดทุกกล้อง
# 2. หรือใช้ TEST_MODE=true
# 3. หรือใช้ mock data
```

### สำหรับ Production (มี AWS)

```bash
# 1. ตรวจสอบ credentials
# 2. ตรวจสอบ KVS streams exist
# 3. ตรวจสอบ data retention enabled
# 4. ตรวจสอบ network/firewall
```

---

## 🔗 ลิงก์ที่เป็นประโยชน์

- [AWS KVS Documentation](https://docs.aws.amazon.com/kinesisvideostreams/)
- [AWS Credentials Setup](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [Troubleshooting KVS](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/troubleshooting.html)

---

**ตอนนี้แก้ไข 2 ปัญหาแล้ว (model file + TypeError)**  
**ปัญหาที่ 3 (AWS connection) ต้องตรวจสอบ AWS setup** ✅
