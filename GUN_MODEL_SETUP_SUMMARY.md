# 🎯 สรุป: Gun Detection Model Setup

**วันที่:** 14 ตุลาคม 2025  
**Model:** CCTV Gun Detection (Roboflow)  
**URL:** https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n

---

## ✅ สิ่งที่ได้สร้างแล้ว

### 📚 เอกสาร:
- ✅ **GUN_MODEL_QUICKSTART.md** - คู่มือเริ่มต้นด่วน
- ✅ **DOWNLOAD_GUN_MODEL.md** - คู่มือละเอียด
- ✅ **MODELS_GUIDE.md** - คู่มือ YOLO models ทั่วไป
- ✅ **MODELS_REQUIRED.md** - รายการ models ทั้งหมด
- ✅ **MODELS_QUICKREF.md** - Quick reference

### 🛠️ Scripts:
- ✅ **download_gun_model.py** - ดาวน์โหลด gun detection model
- ✅ **train_gun_model.py** - train model (ถ้าต้องการ)
- ✅ **download_models.py** - ดาวน์โหลด base models
- ✅ **download-models.sh** - Bash version

### ⚙️ Configuration:
- ✅ **config/cameras.yaml** - เปิดใช้งาน weapon detector สำหรับ camera_1

---

## 🚀 ขั้นตอนถัดไป (Todo)

### 1️⃣ ดาวน์โหลด Gun Detection Model

```bash
# ติดตั้ง dependencies
pip install roboflow ultralytics

# ตั้งค่า API key
export ROBOFLOW_API_KEY="your_roboflow_api_key"

# ดาวน์โหลด model
python3 download_gun_model.py
```

**ผลลัพธ์ที่คาดหวัง:**
- Model จะถูก download และ copy ไปที่ `models/weapon-yolov8n.pt`
- Script จะแสดง model classes และ configuration example

---

### 2️⃣ ตรวจสอบว่า Model ถูก Download แล้ว

```bash
# ตรวจสอบไฟล์
ls -lh models/weapon-yolov8n.pt

# Expected output:
# -rw-r--r-- 1 user staff X.XM Oct 14 15:XX models/weapon-yolov8n.pt
```

---

### 3️⃣ ทดสอบ Model (Optional)

```python
# test_gun.py
from ultralytics import YOLO

# Load model
model = YOLO('models/weapon-yolov8n.pt')

# Check classes
print(f"Classes: {model.names}")

# Test with image (if you have test image)
# results = model('test_image.jpg', conf=0.5)
# results[0].show()
```

---

### 4️⃣ รันระบบ

```bash
./run.sh
```

**สิ่งที่จะเกิดขึ้น:**
- System จะ load gun detection model
- Camera_1 จะใช้งาน weapon detector
- เมื่อตรวจจับปืนได้จะ:
  - 📤 ส่ง event ไปยัง Kinesis Data Streams
  - 📸 บันทึก snapshot ไปยัง S3
  - 📊 แสดงใน dashboard

---

### 5️⃣ เช็ค Dashboard

```bash
# เปิด browser
open http://localhost:8080

# หรือ
curl http://localhost:8080/health
```

---

## ⚙️ Configuration ที่เปิดใช้งานแล้ว

**ไฟล์:** `config/cameras.yaml`

```yaml
cameras:
  camera_1:
    enabled: true
    fps_target: 5
    
    detectors:
      - type: weapon
        params:
          model_path: models/weapon-yolov8n.pt
          conf_threshold: 0.5
          target_classes: [gun, pistol, rifle]
          temporal_window: 5
          min_confirmations: 3
          dedup_window: 30
          dedup_grid_size: 4
```

**พารามิเตอร์:**
- `model_path`: ที่อยู่ของ gun detection model
- `conf_threshold`: 0.5 = ตรวจจับเมื่อ confidence >= 50%
- `target_classes`: ตรวจจับ gun, pistol, rifle (ปรับตาม model classes ที่แท้จริง)
- `temporal_window`: ดูย้อนหลัง 5 frames
- `min_confirmations`: ต้องเจอใน 3/5 frames ถึงจะ alert
- `dedup_window`: ไม่ alert ซ้ำภายใน 30 วินาที
- `dedup_grid_size`: แบ่งภาพเป็น grid 4x4 เพื่อ dedup ตามตำแหน่ง

---

## 📊 Expected Logs

เมื่อรันระบบจะเห็น:

```log
2025-10-14 16:00:00 | camera_1 | INFO | Initializing frame source for KVS
2025-10-14 16:00:01 | camera_1 | INFO | Frame source initialized
2025-10-14 16:00:02 | camera_1 | INFO | Loading detector: weapon
2025-10-14 16:00:03 | camera_1 | INFO | Model loaded: models/weapon-yolov8n.pt
2025-10-14 16:00:03 | camera_1 | INFO | Model classes: ['gun', 'pistol', 'rifle']
2025-10-14 16:00:03 | camera_1 | INFO | 1 detectors ready
2025-10-14 16:00:03 | camera_1 | INFO | Worker started

# เมื่อตรวจจับได้:
2025-10-14 16:05:00 | camera_1 | WARN | 🔫 Weapon detected: gun (conf=0.87)
2025-10-14 16:05:00 | camera_1 | INFO | Temporal confirmations: 3/5 frames
2025-10-14 16:05:00 | camera_1 | INFO | Publishing event to KDS: stream-C01
2025-10-14 16:05:01 | camera_1 | INFO | Saving snapshot to S3: s3://multicam-snaps/snapshots/...
2025-10-14 16:05:01 | camera_1 | INFO | Event published successfully
```

---

## 🔧 Tuning Parameters

### ลด False Positives (ตรวจจับผิดพลาด):

```yaml
conf_threshold: 0.7              # เพิ่มเป็น 0.6-0.8
temporal_window: 7               # เพิ่มเป็น 7-10
min_confirmations: 5             # เพิ่มเป็น 4-6
```

### เพิ่ม Sensitivity (ตรวจจับง่ายขึ้น):

```yaml
conf_threshold: 0.3              # ลดเป็น 0.3-0.4
temporal_window: 3               # ลดเป็น 3
min_confirmations: 2             # ลดเป็น 2
```

### ลด Alert Frequency:

```yaml
dedup_window: 60                 # เพิ่มเป็น 60-120 วินาที
```

---

## 🧪 Testing Checklist

### ก่อนรันระบบ:
- [ ] ติดตั้ง roboflow: `pip install roboflow`
- [ ] ติดตั้ง ultralytics: `pip install ultralytics`
- [ ] มี Roboflow API key
- [ ] ดาวน์โหลด model สำเร็จ: `models/weapon-yolov8n.pt` มีอยู่
- [ ] Config ถูกแก้ไขแล้ว: weapon detector enabled

### หลังรันระบบ:
- [ ] System เริ่มต้นสำเร็จ (no crash)
- [ ] Model โหลดสำเร็จ (เห็น log "Model loaded")
- [ ] Worker running (เห็น log "Worker started")
- [ ] Health check OK: `curl http://localhost:8080/health`
- [ ] Dashboard เข้าได้: http://localhost:8080

### ทดสอบ Detection:
- [ ] มีวิดีโอใน KVS stream
- [ ] System ประมวลผล frames (เห็น log "Processing frame")
- [ ] ตรวจจับปืนได้ (เมื่อมีในภาพ)
- [ ] Event ถูกส่งไปยัง KDS
- [ ] Snapshot ถูกบันทึกใน S3
- [ ] Dashboard แสดงข้อมูล detection

---

## 📖 เอกสารอ้างอิง

### สำหรับ Gun Model:
1. **GUN_MODEL_QUICKSTART.md** - เริ่มต้นด่วน (อ่านก่อน)
2. **DOWNLOAD_GUN_MODEL.md** - คู่มือละเอียด
3. Dataset URL: https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n

### สำหรับ Models ทั่วไป:
1. **MODELS_GUIDE.md** - คู่มือ YOLO models ทั้งหมด
2. **MODELS_REQUIRED.md** - รายการ models ที่ต้องใช้
3. **MODELS_QUICKREF.md** - Quick reference

### สำหรับระบบ:
1. **CONFIG.md** - การตั้งค่าระบบ
2. **QUICKSTART.md** - เริ่มต้นใช้งานระบบ
3. **ERROR_ANALYSIS.md** - แก้ไข errors

---

## 💡 Tips

### 1. API Key Security
```bash
# เก็บใน environment variable (แนะนำ)
export ROBOFLOW_API_KEY="xxx"

# หรือเก็บใน .env file
echo "ROBOFLOW_API_KEY=xxx" >> .env
source .env
```

### 2. Model Performance
- **CPU:** ใช้ yolov8n (เล็กสุด, เร็วสุด)
- **GPU:** สามารถใช้ yolov8s หรือ yolov8m ได้

### 3. False Positives
- ถ้าตรวจจับผิดบ่อย → เพิ่ม `conf_threshold` และ `min_confirmations`
- ถ้าพลาดการตรวจจับ → ลด `conf_threshold`

### 4. Video Data
- ระบบต้องมีวิดีโอจาก KVS streams ถึงจะทำงาน
- Connection errors = ยังไม่มีวิดีโอ (ปกติ)

---

## 🚨 Troubleshooting

### ❌ "roboflow not installed"
```bash
pip install roboflow
```

### ❌ "No API key provided"
```bash
export ROBOFLOW_API_KEY="your_key_here"
```

### ❌ "Model file not found"
```bash
# ดาวน์โหลดใหม่
python3 download_gun_model.py

# หรือตรวจสอบ path ใน config
nano config/cameras.yaml
```

### ❌ "No pre-trained weights"
```bash
# Train model yourself
python3 train_gun_model.py
```

---

## ✅ Status

**สถานะปัจจุบัน:**
- ✅ เอกสารและ scripts สร้างเสร็จแล้ว
- ✅ Configuration เปิดใช้งาน weapon detector แล้ว
- ⏳ **รอดาวน์โหลด model:** `python3 download_gun_model.py`
- ⏳ **รอทดสอบระบบ:** `./run.sh`

**Next Action:**
```bash
# 1. Get API key from Roboflow
# 2. Run:
export ROBOFLOW_API_KEY="your_key"
python3 download_gun_model.py

# 3. Test system:
./run.sh
```

---

**สร้างโดย:** GitHub Copilot  
**วันที่:** 14 ตุลาคม 2025  
**โปรเจค:** kvs-infer (Multi-Camera Inference System)
