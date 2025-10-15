# 🎯 Models Quick Reference

## 📋 สรุปแบบเร็ว

### Models ที่ต้องใช้:

```
models/
├── yolov8n.pt                 ✅ Required (6 MB)
├── yolov8s.pt                 ⭐ Recommended (22 MB)
├── weapon-yolov8n.pt          🔫 Optional
├── fire-smoke-yolov8n.pt      🔥 Optional
└── license-plate-yolov8n.pt   🚗 Optional
```

---

## ⚡ Quick Download

### วิธีที่ 1: Auto (แนะนำ)
```bash
./download-models.sh
```

### วิธีที่ 2: Python
```bash
python3 download_models.py
```

### วิธีที่ 3: Manual
```bash
mkdir -p models && cd models
curl -L https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt -o yolov8n.pt
curl -L https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt -o yolov8s.pt
cp yolov8n.pt weapon-yolov8n.pt
cp yolov8n.pt fire-smoke-yolov8n.pt
cp yolov8n.pt license-plate-yolov8n.pt
```

---

## 📦 ขนาด Models

| Model | Size | Speed | Accuracy | Use |
|-------|------|-------|----------|-----|
| yolov8n | 6 MB | ⚡⚡⚡ | ⭐⭐⭐ | Dev, CPU |
| yolov8s | 22 MB | ⚡⚡ | ⭐⭐⭐⭐ | Production |
| yolov8m | 52 MB | ⚡ | ⭐⭐⭐⭐⭐ | GPU |

---

## ⚠️ Important!

**Base models = ทดสอบเท่านั้น!**

สำหรับ Production ต้องใช้ **Custom Models**:

### 🔫 Weapon Detection
- 🔗 https://universe.roboflow.com/search?q=weapon
- Download → Replace `models/weapon-yolov8n.pt`

### 🔥 Fire & Smoke Detection
- 🔗 https://universe.roboflow.com/search?q=fire+smoke
- Download → Replace `models/fire-smoke-yolov8n.pt`

### 🚗 License Plate Detection
- 🔗 https://universe.roboflow.com/search?q=license+plate
- Download → Replace `models/license-plate-yolov8n.pt`

---

## ✅ Verify

```bash
# Check models
ls -lh models/*.pt

# Test model
python3 << EOF
from ultralytics import YOLO
model = YOLO('models/yolov8n.pt')
print("✅ Model loaded successfully!")
print(f"Classes: {model.names}")
EOF
```

---

## 🚀 Enable in Config

**config/cameras.yaml:**
```yaml
cameras:
  camera_1:
    detectors:
      - type: weapon
        params:
          model_path: models/weapon-yolov8n.pt
          confidence_threshold: 0.5
```

---

## 📖 เอกสารเต็ม

- **MODELS_REQUIRED.md** - รายการ models ทั้งหมด
- **MODELS_GUIDE.md** - คู่มือละเอียด + training guide
- **CONFIG.md** - วิธีตั้งค่า detectors

---

## 💡 Workflow

```
1. Download base models → ./download-models.sh
2. Test system → ./run.sh
3. Get custom models → Roboflow/GitHub
4. Replace models → models/*.pt
5. Enable detectors → config/cameras.yaml
6. Deploy! → ./run.sh
```
