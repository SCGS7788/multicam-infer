#!/bin/bash
# download-models.sh - Script สำหรับดาวน์โหลด YOLO models

set -e  # Exit on error

echo "🤖 YOLOv8 Models Download Script"
echo "=================================="
echo ""

# สร้าง models directory
MODELS_DIR="models"
mkdir -p "$MODELS_DIR"

echo "📂 Models directory: $(pwd)/$MODELS_DIR"
echo ""

# Function to download file
download_file() {
    local url=$1
    local output=$2
    echo "⬇️  Downloading $(basename $output)..."
    if command -v wget &> /dev/null; then
        wget -q --show-progress "$url" -O "$output"
    elif command -v curl &> /dev/null; then
        curl -L --progress-bar "$url" -o "$output"
    else
        echo "❌ Error: wget or curl not found. Please install one of them."
        exit 1
    fi
}

# Base YOLOv8 model URL
YOLO_BASE_URL="https://github.com/ultralytics/assets/releases/download/v8.3.0"

echo "1️⃣  Downloading Base YOLOv8 Models"
echo "-----------------------------------"

# Download YOLOv8n (nano - smallest, fastest)
if [ ! -f "$MODELS_DIR/yolov8n.pt" ]; then
    download_file "$YOLO_BASE_URL/yolov8n.pt" "$MODELS_DIR/yolov8n.pt"
    echo "✅ YOLOv8n downloaded (6 MB)"
else
    echo "⏭️  YOLOv8n already exists"
fi

# Download YOLOv8s (small - balanced)
if [ ! -f "$MODELS_DIR/yolov8s.pt" ]; then
    download_file "$YOLO_BASE_URL/yolov8s.pt" "$MODELS_DIR/yolov8s.pt"
    echo "✅ YOLOv8s downloaded (22 MB)"
else
    echo "⏭️  YOLOv8s already exists"
fi

echo ""
echo "2️⃣  Creating Detector-Specific Models"
echo "--------------------------------------"

# Create copies for each detector type
detectors=("weapon" "fire-smoke" "license-plate")

for detector in "${detectors[@]}"; do
    model_file="$MODELS_DIR/${detector}-yolov8n.pt"
    if [ ! -f "$model_file" ]; then
        cp "$MODELS_DIR/yolov8n.pt" "$model_file"
        echo "✅ Created ${detector}-yolov8n.pt"
    else
        echo "⏭️  ${detector}-yolov8n.pt already exists"
    fi
done

echo ""
echo "📋 Model Summary"
echo "----------------"
ls -lh "$MODELS_DIR"/*.pt 2>/dev/null || echo "No .pt files found"

echo ""
echo "✅ Download Complete!"
echo ""
echo "⚠️  IMPORTANT NOTES:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 These are BASE models trained on COCO dataset."
echo "   They can detect general objects (person, car, etc.)"
echo "   but NOT specialized objects like:"
echo "   • Weapons (guns, knives)"
echo "   • Fire and smoke"
echo "   • License plates"
echo ""
echo "🎯 For PRODUCTION use, you need CUSTOM models:"
echo ""
echo "   1️⃣  Weapon Detection:"
echo "      • Visit: https://universe.roboflow.com/search?q=weapon+detection"
echo "      • Download custom weapon detector"
echo "      • Replace: models/weapon-yolov8n.pt"
echo ""
echo "   2️⃣  Fire & Smoke Detection:"
echo "      • Visit: https://universe.roboflow.com/search?q=fire+smoke"
echo "      • Download custom fire/smoke detector"
echo "      • Replace: models/fire-smoke-yolov8n.pt"
echo ""
echo "   3️⃣  License Plate Detection:"
echo "      • Visit: https://universe.roboflow.com/search?q=license+plate"
echo "      • Download ALPR model (Thai plates if needed)"
echo "      • Replace: models/license-plate-yolov8n.pt"
echo ""
echo "📖 Read MODELS_GUIDE.md for detailed instructions"
echo ""
echo "🚀 To start using these models:"
echo "   1. Edit config/cameras.yaml"
echo "   2. Enable detectors (uncomment detector sections)"
echo "   3. Run: ./run.sh"
echo ""
