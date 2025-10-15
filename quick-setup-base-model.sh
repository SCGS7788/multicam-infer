#!/bin/bash
# Quick setup using base model (temporary solution)
# Use this while waiting for custom model training to complete

echo "🚀 Quick Setup: Using Base Model"
echo "=================================="
echo ""
echo "⚠️  Note: This uses a base YOLO model that can detect general objects"
echo "   (person, car, etc.) but NOT specifically trained for guns."
echo "   For production, wait for custom training to complete."
echo ""

# Create models directory
mkdir -p models

# Download base model
if [ ! -f "models/yolov8n.pt" ]; then
    echo "📥 Downloading YOLOv8n base model..."
    curl -L https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt \
         -o models/yolov8n.pt
    echo "✅ Downloaded!"
else
    echo "✅ Base model already exists"
fi

# Copy as weapon model
echo "📋 Creating weapon-yolov8n.pt..."
cp models/yolov8n.pt models/weapon-yolov8n.pt

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Note: This is a TEMPORARY solution using base COCO model."
echo "   It will detect 'person' class but not guns specifically."
echo ""
echo "🏋️  Custom gun detection model is training in background."
echo "   Check progress: ps aux | grep train_gun_model"
echo ""
echo "🚀 You can now run the system:"
echo "   ./run.sh"
echo ""
echo "⏱️  Once custom training completes (~30-60 min):"
echo "   - Training will auto-copy model to models/weapon-yolov8n.pt"
echo "   - Restart system to use custom model"
echo ""
