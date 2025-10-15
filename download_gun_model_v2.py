#!/usr/bin/env python3
"""
Download Gun Detection Model using Roboflow Inference API
Model: cctv-gun-detection-gkc0n/2
"""

import os
import sys
from pathlib import Path

def check_inference_sdk():
    """Check if inference_sdk is installed"""
    try:
        import inference_sdk
        return True
    except ImportError:
        return False

def install_inference_sdk():
    """Install inference_sdk package"""
    print("📦 Installing inference_sdk package...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "inference-sdk"])
        print("✅ inference_sdk installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install inference_sdk")
        return False

def download_model_from_api():
    """Download model weights from Roboflow"""
    from roboflow import Roboflow
    
    print("\n📥 Downloading Model from Roboflow...")
    print("=" * 60)
    
    # API Key from user
    api_key = "oBQpsjr25DqFZziUSMVN"
    
    try:
        # Initialize Roboflow
        rf = Roboflow(api_key=api_key)
        
        # Get the project and version
        print("🔍 Accessing project: cctv-gun-detection-gkc0n/2")
        project = rf.workspace("maryamalkendi711gmailcom").project("cctv-gun-detection-gkc0n")
        
        # Download version 2 (the one specified in API call)
        print("⬇️  Downloading model version 2 (YOLOv8 format)...")
        dataset = project.version(2).download("yolov8")
        
        print(f"\n✅ Dataset downloaded!")
        print(f"📂 Location: {dataset.location}")
        
        return dataset.location
        
    except Exception as e:
        print(f"\n❌ Error downloading: {e}")
        return None

def find_and_copy_weights(dataset_location):
    """Find model weights and copy to models directory"""
    dataset_path = Path(dataset_location)
    
    # Common locations for weights
    possible_locations = [
        dataset_path / "weights" / "best.pt",
        dataset_path / "weights" / "last.pt",
        dataset_path / "best.pt",
        dataset_path / "last.pt",
    ]
    
    weights_file = None
    for loc in possible_locations:
        if loc.exists():
            weights_file = loc
            break
    
    # Search recursively
    if not weights_file:
        weights_files = list(dataset_path.rglob("*.pt"))
        if weights_files:
            weights_file = weights_files[0]
    
    if not weights_file:
        print("\n⚠️  No pre-trained weights found in dataset")
        return None
    
    print(f"\n✅ Found weights: {weights_file}")
    
    # Copy to models directory
    import shutil
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    target_file = models_dir / "weapon-yolov8n.pt"
    shutil.copy(weights_file, target_file)
    
    size_mb = target_file.stat().st_size / (1024 * 1024)
    print(f"✅ Model copied to: {target_file}")
    print(f"📊 Model size: {size_mb:.1f} MB")
    
    return target_file

def test_model(model_path):
    """Test the downloaded model"""
    try:
        from ultralytics import YOLO
        
        print(f"\n🧪 Testing model...")
        model = YOLO(str(model_path))
        
        print(f"\n📋 Model Information:")
        print(f"   Classes: {model.names}")
        print(f"   Number of classes: {len(model.names)}")
        
        return model.names
    except Exception as e:
        print(f"\n⚠️  Could not load model: {e}")
        return None

def update_env_file(api_key):
    """Update .env file with new API key"""
    env_file = Path(".env")
    
    if env_file.exists():
        content = env_file.read_text()
        
        # Update or add ROBOFLOW_API_KEY
        if "ROBOFLOW_API_KEY" in content:
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if line.startswith('ROBOFLOW_API_KEY'):
                    new_lines.append(f'ROBOFLOW_API_KEY={api_key}')
                else:
                    new_lines.append(line)
            content = '\n'.join(new_lines)
        else:
            # Add at the end of Roboflow section
            content = content.replace(
                '# Roboflow API Key (for downloading models)',
                f'# Roboflow API Key (for downloading models)\nROBOFLOW_API_KEY={api_key}'
            )
        
        env_file.write_text(content)
        print(f"\n✅ Updated .env file with API key")

def show_config_example(classes):
    """Show configuration example"""
    print("\n⚙️  Configuration Example")
    print("=" * 60)
    print("\nconfig/cameras.yaml already configured with:")
    print("""
cameras:
  camera_1:
    detectors:
      - type: weapon
        params:
          model_path: models/weapon-yolov8n.pt""")
    
    if classes:
        class_list = list(classes.values())
        print(f"          target_classes: {class_list}")
    
    print("""          conf_threshold: 0.5
          temporal_window: 5
          min_confirmations: 3
          dedup_window: 30
""")

def main():
    print("🔫 Gun Detection Model Downloader (Roboflow Inference API)")
    print("=" * 60)
    print("Model: cctv-gun-detection-gkc0n/2")
    print("API Key: oBQpsjr25DqFZziUSMVN")
    print()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if roboflow is installed
    try:
        import roboflow
    except ImportError:
        print("⚠️  roboflow package not found")
        response = input("Install roboflow now? (y/n): ").strip().lower()
        if response == 'y':
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "roboflow"])
        else:
            print("\n💡 Install manually: pip install roboflow")
            return 1
    
    # Update .env file
    update_env_file("oBQpsjr25DqFZziUSMVN")
    
    # Download model
    dataset_location = download_model_from_api()
    if not dataset_location:
        return 1
    
    # Find and copy weights
    model_path = find_and_copy_weights(dataset_location)
    if not model_path:
        print("\n💡 Model may need to be trained first")
        print("   Or try downloading from Roboflow web interface")
        return 1
    
    # Test model
    classes = test_model(model_path)
    
    # Show config example
    show_config_example(classes)
    
    print("\n✅ Setup Complete!")
    print("\n🚀 Next steps:")
    print("   1. Model is ready: models/weapon-yolov8n.pt")
    print("   2. Configuration already set in config/cameras.yaml")
    print("   3. Run system: ./run.sh")
    print("   4. Check dashboard: http://localhost:8080")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
