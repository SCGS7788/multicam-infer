# 🤖 YOLO Models Guide

## Models ที่ระบบรองรับ

ระบบนี้ใช้ **YOLOv8** (Ultralytics) สำหรับ Object Detection และรองรับ 3 ประเภท:

### 1. 🔫 Weapon Detection Model
### 2. 🔥 Fire & Smoke Detection Model  
### 3. 🚗 License Plate Detection Model (ALPR)

---

## 📦 วิธีดาวน์โหลด Models

### ตัวเลือก A: ใช้ Pre-trained Models (แนะนำสำหรับเริ่มต้น)

```bash
cd /Users/pradyapadsee/Documents/aws/multicam-infer/models

# 1. Download base YOLOv8 models
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8m.pt

# 2. Copy สำหรับแต่ละ use case (ใช้ชื่อตาม config)
cp yolov8n.pt weapon-yolov8n.pt
cp yolov8n.pt fire-smoke-yolov8n.pt
cp yolov8n.pt license-plate-yolov8n.pt

# 3. หรือ download แบบย่อ:
curl -L https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt \
  -o weapon-yolov8n.pt
curl -L https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt \
  -o fire-smoke-yolov8n.pt
curl -L https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt \
  -o license-plate-yolov8n.pt
```

**หมายเหตุ:** Pre-trained models เหล่านี้ train บน COCO dataset ซึ่งมี classes ทั่วไป (person, car, etc.) แต่ยังไม่มี weapon, fire, license plate โดยเฉพาะ

---

### ตัวเลือก B: ใช้ Custom Trained Models (แนะนำสำหรับ Production)

#### 🔫 1. Weapon Detection Model

**แหล่ง Models ที่แนะนำ:**

##### A. Roboflow (มี pre-trained models ฟรี)
```bash
# 1. ไปที่ Roboflow Universe:
# https://universe.roboflow.com/search?q=weapon+detection

# 2. เลือก model ที่ชอบ เช่น:
# - "Weapon Detection" by various authors
# - "Gun Detection"
# - "Knife Detection"

# 3. Export เป็น YOLOv8 format และ download
# 4. วาง file ที่ models/weapon-yolov8n.pt
```

##### B. Train เอง
```bash
# ถ้าต้องการ train model เอง:
# 1. เตรียม dataset (images + annotations)
# 2. ใช้ Ultralytics YOLO train

python << 'EOF'
from ultralytics import YOLO

# Load base model
model = YOLO('yolov8n.pt')

# Train on your dataset
model.train(
    data='weapon-dataset.yaml',  # path to dataset config
    epochs=100,
    imgsz=640,
    batch=16,
    name='weapon-detector'
)

# Export trained model
# Best model saved at: runs/detect/weapon-detector/weights/best.pt
EOF

# Copy to models folder
cp runs/detect/weapon-detector/weights/best.pt models/weapon-yolov8n.pt
```

**Dataset แนะนำ:**
- [Weapons Detection Dataset - Roboflow](https://universe.roboflow.com/joseph-nelson/gun-detection)
- [Knife Detection Dataset](https://universe.roboflow.com/knife-detection)
- [COCO Weapons Subset](https://github.com/...)

---

#### 🔥 2. Fire & Smoke Detection Model

**แหล่ง Models:**

##### A. Roboflow Universe
```bash
# 1. ไปที่:
# https://universe.roboflow.com/search?q=fire+smoke+detection

# 2. เลือก model เช่น:
# - "Fire and Smoke Detection"
# - "Fire Detection Dataset"
# - "Smoke Detection"

# 3. Export YOLOv8 และ download
```

##### B. GitHub Projects
```bash
# Fire Detection YOLOv8
git clone https://github.com/robmarkcole/fire-detection-yolov8
cd fire-detection-yolov8

# Download pre-trained weights (ถ้ามี)
# หรือ train เอง
```

##### C. Train เอง
```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(
    data='fire-smoke-dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='fire-smoke-detector'
)
```

**Dataset แนะนำ:**
- [Fire and Smoke Dataset - Roboflow](https://universe.roboflow.com/fire-detection)
- [Fire Detection Dataset - Kaggle](https://www.kaggle.com/datasets/fire-detection)

---

#### 🚗 3. License Plate Detection Model (ALPR)

**แหล่ง Models:**

##### A. Roboflow Universe
```bash
# 1. ไปที่:
# https://universe.roboflow.com/search?q=license+plate

# 2. เลือก model ที่รองรับประเทศของคุณ:
# - "License Plate Detection"
# - "Thai License Plate Detection" (สำหรับไทย)
# - "ANPR Dataset"
```

##### B. GitHub Pre-trained
```bash
# YOLOv8 License Plate Detector
git clone https://github.com/MuhammadMoinFaisal/Automatic_Number_Plate_Detection_Recognition_YOLOv8

# Download weights
wget https://github.com/.../license_plate_detector.pt \
  -O models/license-plate-yolov8n.pt
```

##### C. Train สำหรับประเทศไทย
```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(
    data='thai-license-plate-dataset.yaml',
    epochs=150,
    imgsz=640,
    batch=16,
    name='thai-plate-detector'
)
```

**Dataset แนะนำ:**
- [License Plate Dataset - Roboflow](https://universe.roboflow.com/license-plate-detection)
- [Thai License Plate Dataset](https://www.kaggle.com/datasets/thai-license-plate)

---

## 📥 Quick Download Script

สร้าง script สำหรับ download models อัตโนมัติ:

```bash
#!/bin/bash
# download-models.sh

echo "📦 Downloading YOLOv8 Models..."

# Create models directory
mkdir -p models
cd models

# Base YOLOv8 models
echo "1️⃣ Downloading base YOLOv8 models..."
wget -q --show-progress \
  https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt

wget -q --show-progress \
  https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt

# Create copies for each detector (temporary - replace with custom models)
echo "2️⃣ Creating detector-specific models..."
cp yolov8n.pt weapon-yolov8n.pt
cp yolov8n.pt fire-smoke-yolov8n.pt
cp yolov8n.pt license-plate-yolov8n.pt

echo "✅ Models downloaded!"
echo ""
echo "⚠️  Note: These are base models. For production:"
echo "   - Replace weapon-yolov8n.pt with custom weapon detector"
echo "   - Replace fire-smoke-yolov8n.pt with custom fire/smoke detector"
echo "   - Replace license-plate-yolov8n.pt with custom plate detector"
echo ""
echo "📂 Models location: $(pwd)"
ls -lh *.pt
```

**รัน:**
```bash
chmod +x download-models.sh
./download-models.sh
```

---

## 🎯 Model Sizes & Performance

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| **YOLOv8n** | ~6 MB | ⚡⚡⚡ Very Fast | ⭐⭐⭐ Good | Development, CPU |
| **YOLOv8s** | ~22 MB | ⚡⚡ Fast | ⭐⭐⭐⭐ Better | Balanced |
| **YOLOv8m** | ~52 MB | ⚡ Medium | ⭐⭐⭐⭐⭐ Best | Production, GPU |
| **YOLOv8l** | ~87 MB | 🐌 Slow | ⭐⭐⭐⭐⭐ Best | High accuracy |
| **YOLOv8x** | ~136 MB | 🐌🐌 Very Slow | ⭐⭐⭐⭐⭐ Best | Maximum accuracy |

**แนะนำ:**
- **Development/Testing:** YOLOv8n
- **Production (CPU):** YOLOv8s
- **Production (GPU):** YOLOv8m หรือ YOLOv8l

---

## 📁 โครงสร้าง Models Directory

```
models/
├── yolov8n.pt              # Base model (nano)
├── yolov8s.pt              # Base model (small)
├── yolov8m.pt              # Base model (medium)
│
├── weapon-yolov8n.pt       # Weapon detector
├── fire-smoke-yolov8n.pt   # Fire/smoke detector
└── license-plate-yolov8n.pt # Plate detector
```

---

## 🔧 การใช้งานใน Config

### ตัวอย่าง 1: ใช้ Base Model (ทดสอบ)

```yaml
cameras:
  camera_1:
    detectors:
      - type: weapon
        params:
          model_path: models/yolov8n.pt  # ใช้ base model
          target_classes: [person, knife]  # จะตรวจแค่ classes ที่มีใน COCO
```

### ตัวอย่าง 2: ใช้ Custom Model (Production)

```yaml
cameras:
  camera_1:
    detectors:
      - type: weapon
        params:
          model_path: models/weapon-yolov8n.pt  # Custom trained
          target_classes: [gun, knife, rifle, pistol]
```

---

## 🌐 ดาวน์โหลดจาก Python

```python
# download_models.py
from ultralytics import YOLO
import os

models_dir = 'models'
os.makedirs(models_dir, exist_ok=True)

print("📦 Downloading YOLOv8 models...")

# Download base models
for size in ['n', 's', 'm']:
    print(f"Downloading YOLOv8{size}...")
    model = YOLO(f'yolov8{size}.pt')
    # Model will be downloaded automatically to ~/.ultralytics
    
    # Copy to models directory
    import shutil
    src = os.path.expanduser(f'~/.ultralytics/weights/yolov8{size}.pt')
    dst = f'{models_dir}/yolov8{size}.pt'
    if os.path.exists(src):
        shutil.copy(src, dst)
        print(f"✅ Copied to {dst}")

# Create detector-specific copies
import shutil
shutil.copy(f'{models_dir}/yolov8n.pt', f'{models_dir}/weapon-yolov8n.pt')
shutil.copy(f'{models_dir}/yolov8n.pt', f'{models_dir}/fire-smoke-yolov8n.pt')
shutil.copy(f'{models_dir}/yolov8n.pt', f'{models_dir}/license-plate-yolov8n.pt')

print("✅ All models downloaded!")
```

**รัน:**
```bash
python download_models.py
```

---

## 🔍 ตรวจสอบ Models

```python
# test_model.py
from ultralytics import YOLO
import cv2

# Load model
model = YOLO('models/weapon-yolov8n.pt')

# Test with image
results = model('test_image.jpg')

# Print detections
for r in results:
    boxes = r.boxes
    for box in boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        label = model.names[cls]
        print(f"Detected: {label} (confidence: {conf:.2f})")

# Show results
results[0].show()
```

---

## 📊 Custom Training (ถ้าต้องการ)

### 1. เตรียม Dataset

```yaml
# weapon-dataset.yaml
path: /path/to/dataset
train: images/train
val: images/val

nc: 4  # number of classes
names: ['gun', 'knife', 'rifle', 'pistol']
```

### 2. Train

```python
from ultralytics import YOLO

# Load base model
model = YOLO('yolov8n.pt')

# Train
results = model.train(
    data='weapon-dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='weapon-detector',
    device=0  # GPU 0, หรือ 'cpu'
)

# Validate
metrics = model.val()

# Export
model.export(format='onnx')  # หรือ format อื่นๆ
```

### 3. Test

```python
# Test custom model
model = YOLO('runs/detect/weapon-detector/weights/best.pt')
results = model('test_image.jpg')
results[0].show()
```

---

## 🎓 Model Training Resources

### Datasets:
- **Roboflow Universe:** https://universe.roboflow.com
- **Kaggle Datasets:** https://www.kaggle.com/datasets
- **Open Images:** https://storage.googleapis.com/openimages/web/index.html

### Tutorials:
- **YOLOv8 Training:** https://docs.ultralytics.com/modes/train/
- **Custom Dataset:** https://docs.ultralytics.com/datasets/
- **Model Export:** https://docs.ultralytics.com/modes/export/

---

## 💡 สรุป

### สำหรับเริ่มต้น (Development):
```bash
# Download base models
cd models
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt
cp yolov8n.pt weapon-yolov8n.pt
cp yolov8n.pt fire-smoke-yolov8n.pt
cp yolov8n.pt license-plate-yolov8n.pt
```

### สำหรับ Production:
1. **ดาวน์โหลด** custom models จาก Roboflow/GitHub
2. หรือ **train** models เอง
3. **Test** ด้วยข้อมูลจริง
4. **Deploy** ใน config

---

**ต้องการความช่วยเหลือ?**
- Train custom model: [Ultralytics Docs](https://docs.ultralytics.com)
- Find datasets: [Roboflow Universe](https://universe.roboflow.com)
- Get pre-trained: Check GitHub repositories
