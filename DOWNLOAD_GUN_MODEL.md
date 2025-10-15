# 🔫 Download Gun Detection Model from Roboflow

## Model Information

**Dataset:** CCTV Gun Detection (Roboflow Universe)
**URL:** https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n
**Type:** YOLOv8 Object Detection
**Purpose:** Detect guns/weapons in CCTV footage

---

## ⚡ Quick Download Steps

### ขั้นตอนที่ 1: Sign up / Login to Roboflow

1. ไปที่: https://roboflow.com
2. Sign up หรือ Login
3. ไปที่ dataset: https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n

### ขั้นตอนที่ 2: Export Model

1. คลิก **"Download Dataset"** หรือ **"Export"**
2. เลือก Format: **YOLOv8**
3. เลือก **"show download code"**
4. Copy code snippet

### ขั้นตอนที่ 3: Download ด้วย Python

สร้างไฟล์ `download_gun_model.py`:

```python
#!/usr/bin/env python3
"""
Download Gun Detection Model from Roboflow
"""

from roboflow import Roboflow
import os
import shutil

# Initialize Roboflow
# Get your API key from: https://app.roboflow.com/settings/api
rf = Roboflow(api_key="YOUR_API_KEY_HERE")

# Get the project and dataset
project = rf.workspace("maryamalkendi711gmailcom").project("cctv-gun-detection-gkc0n")
dataset = project.version(1).download("yolov8")

print("\n✅ Dataset downloaded!")
print(f"📂 Location: {dataset.location}")

# Find the weights file
weights_dir = os.path.join(dataset.location, "weights")
if os.path.exists(weights_dir):
    weights_file = os.path.join(weights_dir, "best.pt")
    if os.path.exists(weights_file):
        # Copy to models directory
        models_dir = "models"
        os.makedirs(models_dir, exist_ok=True)
        
        target_file = os.path.join(models_dir, "weapon-yolov8n.pt")
        shutil.copy(weights_file, target_file)
        
        print(f"\n✅ Model copied to: {target_file}")
        print(f"📊 Model size: {os.path.getsize(target_file) / (1024*1024):.1f} MB")
    else:
        print("\n⚠️  Weights file not found. You may need to train the model first.")
else:
    print("\n⚠️  Weights directory not found.")
    print("📖 Follow the instructions to train or export the model.")
```

### ขั้นตอนที่ 4: Get Roboflow API Key

1. ไปที่: https://app.roboflow.com/settings/api
2. Copy your **API Key**
3. แทนที่ `YOUR_API_KEY_HERE` ใน script

### ขั้นตอนที่ 5: Install Roboflow Package

```bash
pip install roboflow
```

### ขั้นตอนที่ 6: Run Script

```bash
python3 download_gun_model.py
```

---

## 🎯 Alternative: Manual Download

ถ้าไม่ต้องการใช้ API:

### ขั้นตอน Manual:

1. **Login to Roboflow**
   - https://roboflow.com

2. **Go to Dataset**
   - https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n

3. **Click "Download Dataset"**
   - เลือก Format: **YOLOv8**
   - คลิก **"Download ZIP"**

4. **Extract ZIP**
   ```bash
   unzip cctv-gun-detection-*.zip -d gun-detection-dataset
   ```

5. **Find Model Weights**
   ```bash
   # ถ้ามี pre-trained weights
   find gun-detection-dataset -name "*.pt"
   
   # Copy to models directory
   cp gun-detection-dataset/weights/best.pt models/weapon-yolov8n.pt
   ```

6. **Or Train the Model**
   ```bash
   # If no pre-trained weights, train it yourself
   python3 train_gun_model.py
   ```

---

## 🏋️ Training the Model (if needed)

ถ้า dataset ไม่มี pre-trained weights:

### train_gun_model.py

```python
#!/usr/bin/env python3
from ultralytics import YOLO
from roboflow import Roboflow

# Download dataset
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("maryamalkendi711gmailcom").project("cctv-gun-detection-gkc0n")
dataset = project.version(1).download("yolov8")

# Load base YOLO model
model = YOLO('yolov8n.pt')  # or yolov8s.pt for better accuracy

# Train
results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=100,
    imgsz=640,
    batch=16,
    name='gun-detector',
    device=0  # 0 = GPU, 'cpu' = CPU
)

print("\n✅ Training complete!")
print(f"📊 Best model: runs/detect/gun-detector/weights/best.pt")

# Copy to models directory
import shutil
import os
os.makedirs('models', exist_ok=True)
shutil.copy('runs/detect/gun-detector/weights/best.pt', 'models/weapon-yolov8n.pt')
print(f"✅ Model saved to: models/weapon-yolov8n.pt")
```

---

## 🧪 Test the Model

### test_gun_model.py

```python
#!/usr/bin/env python3
from ultralytics import YOLO
import cv2

# Load the gun detection model
model = YOLO('models/weapon-yolov8n.pt')

# Test with an image
results = model('test_image.jpg', conf=0.5)

# Print detections
print("\n🔍 Detections:")
for r in results:
    boxes = r.boxes
    for box in boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        label = model.names[cls]
        coords = box.xyxy[0].tolist()
        
        print(f"  🔫 {label}: {conf:.2%} at {coords}")

# Show results
results[0].show()

# Save annotated image
results[0].save('detection_result.jpg')
print("\n✅ Results saved to: detection_result.jpg")
```

Run:
```bash
python3 test_gun_model.py
```

---

## 📋 Summary

### Option A: Download Pre-trained (ถ้ามี)
```bash
# 1. Install roboflow
pip install roboflow

# 2. Run download script
python3 download_gun_model.py

# 3. Verify
ls -lh models/weapon-yolov8n.pt
```

### Option B: Train Yourself
```bash
# 1. Download dataset
python3 download_gun_model.py

# 2. Train model
python3 train_gun_model.py

# 3. Wait for training (~30-60 min on GPU)

# 4. Model saved to models/weapon-yolov8n.pt
```

### Option C: Manual Download
```bash
# 1. Download ZIP from Roboflow website
# 2. Extract and find weights
# 3. Copy to models/weapon-yolov8n.pt
```

---

## ⚙️ Enable in Config

After downloading the model, edit `config/cameras.yaml`:

```yaml
cameras:
  camera_1:
    detectors:
      - type: weapon
        params:
          model_path: models/weapon-yolov8n.pt
          conf_threshold: 0.5
          target_classes: [gun, pistol, rifle]  # adjust based on model classes
          temporal_window: 5
          min_confirmations: 3
          dedup_window: 30
```

---

## 🚀 Run System

```bash
./run.sh
```

---

## 🔍 Check Model Classes

```python
from ultralytics import YOLO

model = YOLO('models/weapon-yolov8n.pt')
print(f"Classes: {model.names}")
# Output: {0: 'gun', 1: 'pistol', 2: 'rifle'} (example)
```

---

## 📊 Expected Performance

- **Classes:** gun, pistol, rifle (หรือตาม dataset)
- **Input Size:** 640x640
- **FPS:** ~30-50 FPS on GPU, ~5-10 FPS on CPU
- **Accuracy:** Depends on training quality

---

## 💡 Tips

1. **API Key:** เก็บไว้ที่ environment variable
   ```bash
   export ROBOFLOW_API_KEY="your_key_here"
   ```

2. **Training:** ใช้ GPU จะเร็วกว่า CPU มาก
   
3. **Classes:** เช็คว่า model มี classes อะไรบ้าง
   
4. **Threshold:** ปรับ confidence threshold ตามความต้องการ

---

## 🆘 Troubleshooting

### Problem: No API Key
**Solution:** Sign up at https://roboflow.com

### Problem: Dataset not found
**Solution:** Check URL and workspace name

### Problem: No pre-trained weights
**Solution:** Train the model yourself (see training section)

### Problem: Model too slow
**Solution:** Use smaller model (yolov8n) or reduce image size

---

## 📖 Next Steps

1. ✅ Download/Train gun detection model
2. ✅ Copy to `models/weapon-yolov8n.pt`
3. ✅ Enable in `config/cameras.yaml`
4. ✅ Test with `./run.sh`
5. ✅ Monitor via dashboard: http://localhost:8080

---

**Need Help?**
- Roboflow Docs: https://docs.roboflow.com
- YOLOv8 Training: https://docs.ultralytics.com/modes/train/
- This project: See MODELS_GUIDE.md
