#!/usr/bin/env python3
"""
Test Roboflow Gun Detector API
"""

from src.kvs_infer.detectors.roboflow_gun_detector import RoboflowGunDetector
import cv2
import numpy as np

print("🧪 Testing Roboflow Gun Detector")
print("=" * 60)
print()

# Initialize detector
print("📦 Initializing detector...")
try:
    detector = RoboflowGunDetector(
        api_key="oBQpsjr25DqFZziUSMVN",
        model_id="cctv-gun-detection-gkc0n/2",
        confidence_threshold=0.5
    )
    print("✅ Detector initialized!\n")
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    exit(1)

# Create test frame
print("🖼️  Creating test frame...")
frame = np.zeros((640, 640, 3), dtype=np.uint8)
cv2.putText(frame, "TEST FRAME", (150, 320), 
            cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
print("✅ Test frame created (640x640)\n")

# Run detection
print("🔍 Running detection via Roboflow API...")
print("   (This will make API call to serverless.roboflow.com)")
print()

try:
    detections = detector.detect(frame)
    
    print("✅ Detection complete!")
    print(f"📊 Found {len(detections)} objects\n")
    
    if detections:
        print("🎯 Detections:")
        print("-" * 60)
        for i, det in enumerate(detections, 1):
            print(f"\n{i}. Class: {det['class']}")
            print(f"   Confidence: {det['confidence']:.2%}")
            print(f"   BBox: {det['bbox']}")
    else:
        print("ℹ️  No objects detected (test frame is blank)")
        print("   This is expected for a blank test frame")
    
    print("\n" + "=" * 60)
    print("✅ Roboflow API is working correctly!")
    print("\n💡 Next steps:")
    print("   1. Register detector in src/kvs_infer/detectors/__init__.py")
    print("   2. Update config/cameras.yaml to use roboflow_gun detector")
    print("   3. Run system: ./run.sh")
    
except Exception as e:
    print(f"\n❌ Detection failed: {e}")
    print("\n💡 Possible causes:")
    print("   - No internet connection")
    print("   - API rate limit exceeded")
    print("   - Invalid API key")
    exit(1)
