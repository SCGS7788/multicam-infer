# 🔫 Gun Detection Model - Quick Start

## ⚡ ขั้นตอนย่อ (3 Steps)

### 1️⃣ ติดตั้ง Dependencies
```bash
pip install roboflow ultralytics
```

### 2️⃣ ดาวน์โหลด Model
```bash
python3 download_gun_model.py
# จะถามหา Roboflow API Key
# Get from: https://app.roboflow.com/settings/api
```

### 3️⃣ Enable ใน Config
```bash
nano config/cameras.yaml
# Uncomment weapon detector section
```

---

## 📖 รายละเอียด

### Step 1: Get Roboflow API Key

1. ไปที่ https://roboflow.com
2. Sign up / Login
3. ไปที่ https://app.roboflow.com/settings/api
4. Copy API Key

**ตั้งค่า Environment Variable (แนะนำ):**
```bash
export ROBOFLOW_API_KEY="your_api_key_here"
```

หรือจะใส่ตอนรัน script ก็ได้

---

### Step 2: Download Gun Detection Model

```bash
# Install roboflow (ครั้งแรกเท่านั้น)
pip install roboflow

# Download model
python3 download_gun_model.py
```

**Output ที่คาดหวัง:**
```
🔫 Gun Detection Model Downloader
============================================================
Dataset: CCTV Gun Detection (Roboflow)
URL: https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n

✅ Using API key from environment variable
📥 Downloading Gun Detection Dataset...
============================================================
🔍 Accessing project: cctv-gun-detection-gkc0n
⬇️  Downloading dataset (YOLOv8 format)...

✅ Dataset downloaded!
📂 Location: /path/to/dataset

🔍 Looking for model weights...
✅ Found weights: /path/to/dataset/weights/best.pt

✅ Model copied to: models/weapon-yolov8n.pt
📊 Model size: XX.X MB

📋 Model Information:
   Classes: {0: 'gun', 1: 'pistol', 2: 'rifle'}
   Number of classes: 3
```

---

### Step 3: Enable in Config

Edit `config/cameras.yaml`:

```yaml
cameras:
  camera_1:
    enabled: true
    fps_target: 5
    
    kvs:
      stream_name: stream-C01
      region: ap-southeast-1
    
    detectors:
      # 🔫 Gun Detection - ENABLED
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

---

### Step 4: Test & Run

```bash
# Run system
./run.sh

# Open dashboard
open http://localhost:8080
```

---

## 🧪 Test Model (Optional)

สร้าง `test_gun.py`:

```python
from ultralytics import YOLO

# Load model
model = YOLO('models/weapon-yolov8n.pt')

# Test with image
results = model('test_image.jpg', conf=0.5)

# Show results
results[0].show()
```

Run:
```bash
python3 test_gun.py
```

---

## 🔧 Troubleshooting

### ❌ "roboflow not installed"
```bash
pip install roboflow
```

### ❌ "No API key provided"
```bash
export ROBOFLOW_API_KEY="your_key"
# หรือใส่ใน script
```

### ❌ "No pre-trained weights found"
```bash
# Train model yourself
python3 train_gun_model.py
```

### ❌ "Model not loading"
```bash
# Check file exists
ls -lh models/weapon-yolov8n.pt

# Check ultralytics installed
pip install ultralytics
```

---

## ⚙️ Configuration Options

### Confidence Threshold
```yaml
conf_threshold: 0.5  # ค่าต่ำ = detect ง่าย, มี false positive
conf_threshold: 0.7  # ค่าสูง = detect ยาก, แม่นยำกว่า
```

### Target Classes
```yaml
# Detect ทุก class
target_classes: [gun, pistol, rifle]

# Detect เฉพาะ gun
target_classes: [gun]
```

### Temporal Filtering
```yaml
temporal_window: 5        # ดูย้อนหลัง 5 frames
min_confirmations: 3      # ต้องเจอ 3 ใน 5 frames ถึงจะ alert
```

### Deduplication
```yaml
dedup_window: 30          # ไม่ alert ซ้ำใน 30 วินาที
dedup_grid_size: 4        # แบ่งภาพเป็น grid 4x4
```

---

## 📊 Expected Output

เมื่อรันระบบจะเห็น logs:

```
2025-10-14 15:50:00 | camera_1 | INFO | Frame source initialized
2025-10-14 15:50:01 | camera_1 | INFO | Loaded detector: weapon
2025-10-14 15:50:01 | camera_1 | INFO | Model classes: ['gun', 'pistol', 'rifle']
2025-10-14 15:50:02 | camera_1 | INFO | 1 detectors ready
2025-10-14 15:50:02 | camera_1 | INFO | Worker started

# When detection happens:
2025-10-14 15:51:00 | camera_1 | WARN | 🔫 Weapon detected: gun (0.87)
2025-10-14 15:51:00 | camera_1 | INFO | Publishing event to KDS
2025-10-14 15:51:00 | camera_1 | INFO | Saving snapshot to S3
```

---

## 🎯 Performance Tips

### For CPU:
- ใช้ yolov8n (smallest model)
- ลด fps_target เป็น 3-5
- ลด image size ถ้าจำเป็น

### For GPU:
- ใช้ yolov8s หรือ yolov8m
- สามารถใช้ fps_target สูงกว่าได้

### Reduce False Positives:
- เพิ่ม conf_threshold เป็น 0.6-0.7
- เพิ่ม min_confirmations เป็น 4-5
- เพิ่ม temporal_window เป็น 7-10

---

## 📖 เอกสารเพิ่มเติม

- **DOWNLOAD_GUN_MODEL.md** - คู่มือละเอียด
- **MODELS_GUIDE.md** - คู่มือ models ทั่วไป
- **CONFIG.md** - การตั้งค่า detectors
- **Roboflow Dataset**: https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n

---

## ✅ Checklist

- [ ] ติดตั้ง roboflow (`pip install roboflow`)
- [ ] ติดตั้ง ultralytics (`pip install ultralytics`)
- [ ] Get Roboflow API Key
- [ ] รัน `python3 download_gun_model.py`
- [ ] ตรวจสอบ `models/weapon-yolov8n.pt` มีไหม
- [ ] แก้ไข `config/cameras.yaml` (enable weapon detector)
- [ ] รันระบบ `./run.sh`
- [ ] เช็ค dashboard `http://localhost:8080`

---

## 🚀 All-in-One Command

```bash
# Full setup
pip install roboflow ultralytics && \
export ROBOFLOW_API_KEY="your_key" && \
python3 download_gun_model.py && \
./run.sh
```

---

Good luck! 🎯
