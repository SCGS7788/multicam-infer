# 🎯 Models Required for KVS-Infer System

## สรุป Models ที่ต้องใช้

### ตาราง Models ทั้งหมด

| Model Type | File Name | Size | Purpose | Priority |
|------------|-----------|------|---------|----------|
| **Base Model** | yolov8n.pt | 6 MB | สำหรับ development/testing | Required |
| **Base Model** | yolov8s.pt | 22 MB | สำหรับ production (balanced) | Recommended |
| **Weapon Detector** | weapon-yolov8n.pt | ตาม custom model | ตรวจจับอาวุธ (ปืน, มีด) | Optional |
| **Fire/Smoke Detector** | fire-smoke-yolov8n.pt | ตาม custom model | ตรวจจับไฟไหม้, ควัน | Optional |
| **License Plate Detector** | license-plate-yolov8n.pt | ตาม custom model | ตรวจจับป้ายทะเบียนรถ (ALPR) | Optional |

---

## 📦 ดาวน์โหลด Models

### วิธีที่ 1: ใช้ Bash Script (แนะนำ)

```bash
# ให้สิทธิ์ execute
chmod +x download-models.sh

# รัน script
./download-models.sh
```

**ผลลัพธ์:**
- ✅ ดาวน์โหลด yolov8n.pt (6 MB)
- ✅ ดาวน์โหลด yolov8s.pt (22 MB)
- ✅ สร้าง weapon-yolov8n.pt
- ✅ สร้าง fire-smoke-yolov8n.pt
- ✅ สร้าง license-plate-yolov8n.pt

---

### วิธีที่ 2: ใช้ Python Script

```bash
python3 download_models.py
```

---

### วิธีที่ 3: ดาวน์โหลดด้วยมือ

```bash
mkdir -p models
cd models

# Base models
curl -L https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt -o yolov8n.pt
curl -L https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt -o yolov8s.pt

# Create detector copies
cp yolov8n.pt weapon-yolov8n.pt
cp yolov8n.pt fire-smoke-yolov8n.pt
cp yolov8n.pt license-plate-yolov8n.pt

cd ..
```

---

## 🔍 ตรวจสอบ Models

```bash
# List files
ls -lh models/*.pt

# Expected output:
# -rw-r--r--  1 user  staff   6.2M  yolov8n.pt
# -rw-r--r--  1 user  staff    22M  yolov8s.pt
# -rw-r--r--  1 user  staff   6.2M  weapon-yolov8n.pt
# -rw-r--r--  1 user  staff   6.2M  fire-smoke-yolov8n.pt
# -rw-r--r--  1 user  staff   6.2M  license-plate-yolov8n.pt
```

---

## ⚙️ กำหนดค่าใน Config

### config/cameras.yaml

```yaml
cameras:
  camera_1:
    enabled: true
    stream_name: stream-C01
    region: ap-southeast-1
    
    # เปิดใช้งาน detectors
    detectors:
      # 1. Weapon Detection
      - type: weapon
        params:
          model_path: models/weapon-yolov8n.pt
          target_classes: [person, gun, knife]  # ใน base model มีแค่ person
          confidence_threshold: 0.5
          
      # 2. Fire & Smoke Detection
      - type: fire_smoke
        params:
          model_path: models/fire-smoke-yolov8n.pt
          target_classes: [fire, smoke]  # จะต้องใช้ custom model
          confidence_threshold: 0.6
          
      # 3. License Plate Detection (ALPR)
      - type: alpr
        params:
          detector_model_path: models/license-plate-yolov8n.pt
          ocr_engine: paddleocr  # หรือ tesseract
          confidence_threshold: 0.7
```

---

## 📚 แหล่ง Custom Models

### 🔫 1. Weapon Detection Models

**Roboflow Universe:**
- 🔗 https://universe.roboflow.com/search?q=weapon+detection
- เลือก dataset และ export เป็น YOLOv8 format

**GitHub:**
- 🔗 https://github.com/topics/weapon-detection
- ค้นหา pre-trained models

**Kaggle:**
- 🔗 https://www.kaggle.com/search?q=weapon+detection

**ตัวอย่าง Datasets:**
- Weapons Detection (Roboflow)
- Gun Detection Dataset
- Knife Detection Dataset

---

### 🔥 2. Fire & Smoke Detection Models

**Roboflow Universe:**
- 🔗 https://universe.roboflow.com/search?q=fire+smoke+detection

**GitHub:**
- 🔗 https://github.com/robmarkcole/fire-detection-yolov8
- 🔗 https://github.com/topics/fire-detection

**Kaggle:**
- 🔗 https://www.kaggle.com/datasets/atulyakumar98/test-dataset
- Fire and Smoke Detection Dataset

---

### 🚗 3. License Plate Detection Models

**Roboflow Universe:**
- 🔗 https://universe.roboflow.com/search?q=license+plate
- **สำหรับไทย:** ค้นหา "Thai license plate"

**GitHub:**
- 🔗 https://github.com/MuhammadMoinFaisal/Automatic_Number_Plate_Detection_Recognition_YOLOv8
- 🔗 https://github.com/topics/license-plate-recognition

**Kaggle:**
- 🔗 https://www.kaggle.com/datasets/andrewmvd/car-plate-detection

---

## 🎓 Training Custom Models

ถ้าต้องการ train models เอง:

### ขั้นตอน:

1. **เตรียม Dataset**
   ```
   dataset/
   ├── images/
   │   ├── train/
   │   └── val/
   └── labels/
       ├── train/
       └── val/
   ```

2. **สร้าง data.yaml**
   ```yaml
   path: /path/to/dataset
   train: images/train
   val: images/val
   
   nc: 2  # number of classes
   names: ['gun', 'knife']
   ```

3. **Train Model**
   ```python
   from ultralytics import YOLO
   
   # Load base model
   model = YOLO('yolov8n.pt')
   
   # Train
   results = model.train(
       data='data.yaml',
       epochs=100,
       imgsz=640,
       batch=16,
       name='weapon-detector'
   )
   
   # Best model: runs/detect/weapon-detector/weights/best.pt
   ```

4. **Copy Model**
   ```bash
   cp runs/detect/weapon-detector/weights/best.pt models/weapon-yolov8n.pt
   ```

---

## 🧪 ทดสอบ Models

### Test Script

```python
from ultralytics import YOLO
import cv2

# Load model
model = YOLO('models/weapon-yolov8n.pt')

# Test with image
results = model('test_image.jpg')

# Show results
for r in results:
    boxes = r.boxes
    for box in boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        label = model.names[cls]
        print(f"Detected: {label} (confidence: {conf:.2f})")

# Display
results[0].show()
```

### Run Test

```bash
python test_model.py
```

---

## 📊 Model Performance Comparison

| Model Size | Parameters | Size (MB) | Speed (ms) | mAP50 | Use Case |
|------------|------------|-----------|------------|-------|----------|
| **YOLOv8n** | 3.2M | 6 | 8 | 37.3 | Development, CPU |
| **YOLOv8s** | 11.2M | 22 | 10 | 44.9 | Balanced |
| **YOLOv8m** | 25.9M | 52 | 15 | 50.2 | Production, GPU |
| **YOLOv8l** | 43.7M | 87 | 20 | 52.9 | High Accuracy |
| **YOLOv8x** | 68.2M | 136 | 28 | 53.9 | Maximum Accuracy |

**แนะนำ:**
- **CPU:** YOLOv8n หรือ YOLOv8s
- **GPU:** YOLOv8m หรือ YOLOv8l
- **Production:** YOLOv8s (balanced)

---

## ✅ Checklist

### Base Models (Required)
- [ ] ดาวน์โหลด yolov8n.pt (6 MB)
- [ ] ดาวน์โหลด yolov8s.pt (22 MB) - แนะนำ

### Detector Models (Optional)
- [ ] Weapon detector: weapon-yolov8n.pt
- [ ] Fire/Smoke detector: fire-smoke-yolov8n.pt
- [ ] License plate detector: license-plate-yolov8n.pt

### Configuration
- [ ] แก้ไข config/cameras.yaml
- [ ] เปิดใช้งาน detectors
- [ ] ตั้งค่า confidence thresholds

### Testing
- [ ] ทดสอบ model กับรูปภาพ
- [ ] ตรวจสอบ detection results
- [ ] ทดสอบกับวิดีโอจริง

### Production
- [ ] Replace base models ด้วย custom models
- [ ] Fine-tune parameters
- [ ] Monitor performance

---

## 🚀 Quick Start

```bash
# 1. ดาวน์โหลด models
./download-models.sh

# 2. ตรวจสอบ models
ls -lh models/*.pt

# 3. แก้ไข config
nano config/cameras.yaml

# 4. รันระบบ
./run.sh

# 5. เช็ค dashboard
open http://localhost:8080
```

---

## 📖 เอกสารเพิ่มเติม

- **MODELS_GUIDE.md** - คู่มือ models แบบละเอียด
- **CONFIG.md** - คู่มือ configuration
- **QUICKSTART.md** - เริ่มต้นใช้งาน
- **Ultralytics Docs** - https://docs.ultralytics.com

---

## 💡 Tips

1. **Development:** ใช้ base models (yolov8n.pt) ก่อน
2. **Production:** Replace ด้วย custom trained models
3. **Performance:** เลือก model size ตาม hardware
4. **Accuracy:** Test กับข้อมูลจริงก่อน deploy
5. **Updates:** Check Ultralytics สำหรับ model versions ใหม่

---

## 🆘 ต้องการความช่วยเหลือ?

- **Train models:** อ่าน MODELS_GUIDE.md
- **Find datasets:** เข้า Roboflow Universe
- **Performance issues:** ลดขนาด model หรือ batch size
- **Errors:** เช็ค logs และ ERROR_ANALYSIS.md
