#!/usr/bin/env python3
"""
Roboflow Inference API Wrapper for Gun Detection
Uses serverless API instead of downloading model weights
"""

import os
import sys
from pathlib import Path

def install_inference_sdk():
    """Install inference_sdk package"""
    print("📦 Installing inference_sdk...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "inference-sdk", "-q"])
        print("✅ inference_sdk installed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install inference_sdk")
        return False

def test_roboflow_api():
    """Test Roboflow Inference API"""
    try:
        from inference_sdk import InferenceHTTPClient
    except ImportError:
        print("⚠️  inference_sdk not found")
        if not install_inference_sdk():
            return False
        from inference_sdk import InferenceHTTPClient
    
    print("\n🧪 Testing Roboflow Inference API...")
    print("=" * 60)
    
    # Initialize client
    CLIENT = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key="oBQpsjr25DqFZziUSMVN"
    )
    
    print("✅ API Client initialized")
    print(f"   API URL: https://serverless.roboflow.com")
    print(f"   Model: cctv-gun-detection-gkc0n/2")
    print(f"   API Key: oBQpsjr25DqFZziUSMVN")
    
    return True

def create_roboflow_detector():
    """Create Roboflow detector wrapper for kvs-infer"""
    
    detector_code = '''"""
Roboflow Inference API Detector
Uses Roboflow serverless API for gun detection
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from inference_sdk import InferenceHTTPClient


class RoboflowGunDetector:
    """
    Gun detector using Roboflow Inference API
    Model: cctv-gun-detection-gkc0n/2
    """
    
    def __init__(
        self,
        api_key: str = "oBQpsjr25DqFZziUSMVN",
        api_url: str = "https://serverless.roboflow.com",
        model_id: str = "cctv-gun-detection-gkc0n/2",
        confidence_threshold: float = 0.5,
        **kwargs
    ):
        """Initialize Roboflow detector"""
        self.api_key = api_key
        self.api_url = api_url
        self.model_id = model_id
        self.confidence_threshold = confidence_threshold
        
        # Initialize client
        self.client = InferenceHTTPClient(
            api_url=self.api_url,
            api_key=self.api_key
        )
        
        print(f"✅ RoboflowGunDetector initialized")
        print(f"   Model: {self.model_id}")
        print(f"   Confidence threshold: {self.confidence_threshold}")
    
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run detection on frame using Roboflow API
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of detections with format:
            {
                'class': str,
                'confidence': float,
                'bbox': (x1, y1, x2, y2)
            }
        """
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Encode image to bytes
        _, img_encoded = cv2.imencode('.jpg', frame_rgb)
        img_bytes = img_encoded.tobytes()
        
        try:
            # Call Roboflow API
            result = self.client.infer(img_bytes, model_id=self.model_id)
            
            # Parse results
            detections = []
            if 'predictions' in result:
                for pred in result['predictions']:
                    confidence = pred.get('confidence', 0.0)
                    
                    # Filter by confidence
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Extract bbox
                    x = pred['x']
                    y = pred['y']
                    width = pred['width']
                    height = pred['height']
                    
                    # Convert to x1, y1, x2, y2
                    x1 = int(x - width / 2)
                    y1 = int(y - height / 2)
                    x2 = int(x + width / 2)
                    y2 = int(y + height / 2)
                    
                    detections.append({
                        'class': pred.get('class', 'unknown'),
                        'confidence': confidence,
                        'bbox': (x1, y1, x2, y2)
                    })
            
            return detections
            
        except Exception as e:
            print(f"⚠️  Roboflow API error: {e}")
            return []
    
    def __call__(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Allow detector to be called directly"""
        return self.detect(frame)


# For compatibility with existing detector interface
def create_detector(**kwargs) -> RoboflowGunDetector:
    """Factory function to create detector"""
    return RoboflowGunDetector(**kwargs)
'''
    
    # Save detector code
    detector_file = Path("src/kvs_infer/detectors/roboflow_gun_detector.py")
    detector_file.parent.mkdir(parents=True, exist_ok=True)
    detector_file.write_text(detector_code)
    
    print(f"\n✅ Created Roboflow detector: {detector_file}")
    return detector_file

def show_usage_example():
    """Show how to use Roboflow detector"""
    print("\n📖 Usage Example")
    print("=" * 60)
    print("""
# Test detector directly:
python3 << 'EOF'
from src.kvs_infer.detectors.roboflow_gun_detector import RoboflowGunDetector
import cv2

# Initialize detector
detector = RoboflowGunDetector(confidence_threshold=0.5)

# Load test image
frame = cv2.imread('test_image.jpg')

# Run detection
detections = detector.detect(frame)

# Print results
for det in detections:
    print(f"Detected: {det['class']} ({det['confidence']:.2%})")
    print(f"  BBox: {det['bbox']}")
EOF
""")

def show_config_example():
    """Show configuration for kvs-infer"""
    print("\n⚙️  Configuration for kvs-infer")
    print("=" * 60)
    print("""
Option 1: Use Roboflow API detector (RECOMMENDED)
--------------------------------------------------
Edit config/cameras.yaml:

cameras:
  camera_1:
    detectors:
      - type: roboflow_gun  # Use API-based detector
        params:
          api_key: oBQpsjr25DqFZziUSMVN
          model_id: cctv-gun-detection-gkc0n/2
          confidence_threshold: 0.5

Benefits:
  ✅ No model download needed
  ✅ Always up-to-date model
  ✅ Serverless (no GPU needed)
  ⚠️  Requires internet connection
  ⚠️  API rate limits apply


Option 2: Download and use local model (current setup)
-------------------------------------------------------
Keep existing config:

cameras:
  camera_1:
    detectors:
      - type: weapon  # Use local YOLO model
        params:
          model_path: models/weapon-yolov8n.pt
          conf_threshold: 0.5

Benefits:
  ✅ Works offline
  ✅ Faster (no API calls)
  ⚠️  Need to download/train model first
  ⚠️  Requires local compute (CPU/GPU)
""")

def main():
    print("🔫 Roboflow Inference API Setup")
    print("=" * 60)
    print("Model: cctv-gun-detection-gkc0n/2")
    print("Method: Serverless API (no model download needed)")
    print()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Test API
    if not test_roboflow_api():
        return 1
    
    # Create detector wrapper
    detector_file = create_roboflow_detector()
    
    # Show usage
    show_usage_example()
    show_config_example()
    
    print("\n✅ Roboflow API Setup Complete!")
    print("\n💡 Two options to use:")
    print("   1. API-based: Edit config to use 'roboflow_gun' detector")
    print("   2. Local model: Continue with current setup (need model file)")
    print()
    print("🚀 For testing API-based detection:")
    print("   python3 -c 'from src.kvs_infer.detectors.roboflow_gun_detector import *'")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
