#!/usr/bin/env python3
"""
Download Gun Detection Model from Roboflow
Dataset: CCTV Gun Detection
URL: https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n
"""

import os
import sys
import shutil
from pathlib import Path

def check_roboflow_installed():
    """Check if roboflow package is installed"""
    try:
        import roboflow
        return True
    except ImportError:
        return False

def install_roboflow():
    """Install roboflow package"""
    print("📦 Installing roboflow package...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "roboflow"])
        print("✅ roboflow installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install roboflow")
        return False

def get_api_key():
    """Get Roboflow API key from user or environment"""
    # Try environment variable first
    api_key = os.environ.get('ROBOFLOW_API_KEY')
    
    if api_key:
        print(f"✅ Using API key from environment variable")
        return api_key
    
    # Ask user
    print("\n🔑 Roboflow API Key Required")
    print("=" * 60)
    print("Get your API key from: https://app.roboflow.com/settings/api")
    print()
    api_key = input("Enter your Roboflow API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided")
        return None
    
    return api_key

def download_model(api_key):
    """Download gun detection model from Roboflow"""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("❌ roboflow package not found")
        return False
    
    print("\n📥 Downloading Gun Detection Dataset...")
    print("=" * 60)
    
    try:
        # Initialize Roboflow
        rf = Roboflow(api_key=api_key)
        
        # Get the project
        print("🔍 Accessing project: cctv-gun-detection-gkc0n")
        project = rf.workspace("maryamalkendi711gmailcom").project("cctv-gun-detection-gkc0n")
        
        # Download dataset (version 1, YOLOv8 format)
        print("⬇️  Downloading dataset (YOLOv8 format)...")
        dataset = project.version(1).download("yolov8")
        
        print(f"\n✅ Dataset downloaded!")
        print(f"📂 Location: {dataset.location}")
        
        return dataset.location
        
    except Exception as e:
        print(f"\n❌ Error downloading dataset: {e}")
        print("\n💡 Possible solutions:")
        print("   1. Check your API key is correct")
        print("   2. Check your internet connection")
        print("   3. Verify dataset URL: https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n")
        return None

def find_weights(dataset_location):
    """Find model weights in downloaded dataset"""
    dataset_path = Path(dataset_location)
    
    # Common locations for weights
    possible_locations = [
        dataset_path / "weights" / "best.pt",
        dataset_path / "weights" / "last.pt",
        dataset_path / "best.pt",
        dataset_path / "last.pt",
    ]
    
    for weights_file in possible_locations:
        if weights_file.exists():
            return weights_file
    
    # Search recursively
    weights_files = list(dataset_path.rglob("*.pt"))
    if weights_files:
        return weights_files[0]
    
    return None

def copy_to_models(weights_file):
    """Copy weights to models directory"""
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    target_file = models_dir / "weapon-yolov8n.pt"
    
    shutil.copy(weights_file, target_file)
    
    size_mb = target_file.stat().st_size / (1024 * 1024)
    print(f"\n✅ Model copied to: {target_file}")
    print(f"📊 Model size: {size_mb:.1f} MB")
    
    return target_file

def check_model_classes(model_path):
    """Check model classes"""
    try:
        from ultralytics import YOLO
        model = YOLO(str(model_path))
        
        print(f"\n📋 Model Information:")
        print(f"   Classes: {model.names}")
        print(f"   Number of classes: {len(model.names)}")
        
        return model.names
    except Exception as e:
        print(f"\n⚠️  Could not load model to check classes: {e}")
        return None

def show_config_example(classes):
    """Show example configuration"""
    print("\n⚙️  Configuration Example")
    print("=" * 60)
    print("\nEdit config/cameras.yaml and add:")
    print("""
cameras:
  camera_1:
    detectors:
      - type: weapon
        params:
          model_path: models/weapon-yolov8n.pt
          conf_threshold: 0.5""")
    
    if classes:
        class_names = list(classes.values())
        print(f"          target_classes: {class_names}")
    
    print("""          temporal_window: 5
          min_confirmations: 3
          dedup_window: 30
          dedup_grid_size: 4
""")

def main():
    print("🔫 Gun Detection Model Downloader")
    print("=" * 60)
    print("Dataset: CCTV Gun Detection (Roboflow)")
    print("URL: https://universe.roboflow.com/maryamalkendi711gmailcom/cctv-gun-detection-gkc0n")
    print()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if roboflow is installed
    if not check_roboflow_installed():
        print("⚠️  roboflow package not found")
        print()
        response = input("Install roboflow now? (y/n): ").strip().lower()
        if response == 'y':
            if not install_roboflow():
                return 1
        else:
            print("\n💡 Install manually: pip install roboflow")
            return 1
    
    # Get API key
    api_key = get_api_key()
    if not api_key:
        return 1
    
    # Download dataset
    dataset_location = download_model(api_key)
    if not dataset_location:
        return 1
    
    # Find weights
    print("\n🔍 Looking for model weights...")
    weights_file = find_weights(dataset_location)
    
    if weights_file:
        print(f"✅ Found weights: {weights_file}")
        
        # Copy to models directory
        model_path = copy_to_models(weights_file)
        
        # Check classes
        classes = check_model_classes(model_path)
        
        # Show config example
        show_config_example(classes)
        
        print("\n✅ Download complete!")
        print("\n🚀 Next steps:")
        print("   1. Edit config/cameras.yaml")
        print("   2. Enable weapon detector (see example above)")
        print("   3. Run: ./run.sh")
        print("   4. Check dashboard: http://localhost:8080")
        
        return 0
    else:
        print("\n⚠️  No pre-trained weights found in dataset")
        print("\n💡 You may need to train the model first:")
        print("   python3 train_gun_model.py")
        return 1

if __name__ == '__main__':
    sys.exit(main())
