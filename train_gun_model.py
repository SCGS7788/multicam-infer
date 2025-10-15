#!/usr/bin/env python3
"""
Train Gun Detection Model
(In case the Roboflow dataset doesn't include pre-trained weights)
"""

import os
import sys
from pathlib import Path

def check_ultralytics():
    """Check if ultralytics is installed"""
    try:
        from ultralytics import YOLO
        return True
    except ImportError:
        print("❌ ultralytics not installed")
        print("💡 Install: pip install ultralytics")
        return False

def check_dataset():
    """Check if dataset was downloaded"""
    # Look for data.yaml in common locations
    possible_locations = [
        Path("cctv-gun-detection-1"),
        Path("CCTV-Gun-Detection-1"),
        Path("gun-detection-dataset"),
    ]
    
    for loc in possible_locations:
        data_yaml = loc / "data.yaml"
        if data_yaml.exists():
            return data_yaml
    
    # Search recursively
    data_yamls = list(Path(".").rglob("data.yaml"))
    if data_yamls:
        # Filter for gun detection dataset
        for yaml_file in data_yamls:
            if "gun" in str(yaml_file).lower() or "weapon" in str(yaml_file).lower():
                return yaml_file
    
    return None

def train_model(data_yaml):
    """Train gun detection model"""
    from ultralytics import YOLO
    
    print("\n🏋️  Training Gun Detection Model")
    print("=" * 60)
    print(f"Dataset: {data_yaml}")
    print()
    
    # Ask user for training parameters
    print("⚙️  Training Configuration:")
    print()
    
    # Model size
    print("Select base model size:")
    print("  1. YOLOv8n (nano) - fastest, smallest")
    print("  2. YOLOv8s (small) - balanced [recommended]")
    print("  3. YOLOv8m (medium) - better accuracy")
    
    choice = input("\nChoice (1/2/3) [2]: ").strip() or "2"
    
    model_map = {
        "1": "yolov8n.pt",
        "2": "yolov8s.pt",
        "3": "yolov8m.pt"
    }
    base_model = model_map.get(choice, "yolov8s.pt")
    
    print(f"\n📦 Base model: {base_model}")
    
    # Epochs
    epochs_input = input("Number of epochs [100]: ").strip()
    epochs = int(epochs_input) if epochs_input else 100
    
    # Batch size
    batch_input = input("Batch size [16]: ").strip()
    batch = int(batch_input) if batch_input else 16
    
    # Device
    device_input = input("Device (0=GPU, cpu=CPU) [0]: ").strip() or "0"
    
    print("\n🚀 Starting training...")
    print(f"   Model: {base_model}")
    print(f"   Epochs: {epochs}")
    print(f"   Batch: {batch}")
    print(f"   Device: {device_input}")
    print()
    print("⏱️  This may take 30-60 minutes (or more)...")
    print()
    
    try:
        # Load base model
        model = YOLO(base_model)
        
        # Train
        results = model.train(
            data=str(data_yaml),
            epochs=epochs,
            imgsz=640,
            batch=batch,
            name='gun-detector',
            device=device_input,
            patience=20,  # early stopping
            save=True,
            project='runs/detect'
        )
        
        print("\n✅ Training complete!")
        
        # Best model location
        best_model = Path("runs/detect/gun-detector/weights/best.pt")
        
        if best_model.exists():
            print(f"\n📊 Best model: {best_model}")
            
            # Copy to models directory
            import shutil
            models_dir = Path("models")
            models_dir.mkdir(exist_ok=True)
            
            target = models_dir / "weapon-yolov8n.pt"
            shutil.copy(best_model, target)
            
            size_mb = target.stat().st_size / (1024 * 1024)
            print(f"✅ Copied to: {target} ({size_mb:.1f} MB)")
            
            # Show metrics
            print("\n📈 Training Metrics:")
            print(f"   mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
            print(f"   mAP50-95: {results.results_dict.get('metrics/mAP50-95(B)', 'N/A')}")
            
            return target
        else:
            print("⚠️  Best model not found")
            return None
            
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        return None

def validate_model(model_path):
    """Validate trained model"""
    from ultralytics import YOLO
    
    print("\n🧪 Validating model...")
    
    try:
        model = YOLO(str(model_path))
        
        # Print model info
        print(f"\n📋 Model Information:")
        print(f"   Classes: {model.names}")
        print(f"   Number of classes: {len(model.names)}")
        
        return True
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def show_next_steps():
    """Show next steps"""
    print("\n🚀 Next Steps:")
    print("=" * 60)
    print()
    print("1️⃣  Edit config/cameras.yaml:")
    print("""
    cameras:
      camera_1:
        detectors:
          - type: weapon
            params:
              model_path: models/weapon-yolov8n.pt
              conf_threshold: 0.5
              target_classes: [gun, pistol, rifle]
""")
    print()
    print("2️⃣  Test model:")
    print("    python3 test_gun_model.py")
    print()
    print("3️⃣  Run system:")
    print("    ./run.sh")
    print()
    print("4️⃣  Monitor dashboard:")
    print("    http://localhost:8080")

def main():
    print("🏋️  Gun Detection Model Training")
    print("=" * 60)
    print()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check ultralytics
    if not check_ultralytics():
        return 1
    
    # Check dataset
    print("🔍 Looking for dataset...")
    data_yaml = check_dataset()
    
    if not data_yaml:
        print("\n❌ Dataset not found!")
        print("\n💡 Please download dataset first:")
        print("   python3 download_gun_model.py")
        return 1
    
    print(f"✅ Found dataset: {data_yaml}")
    
    # Confirm training
    print("\n⚠️  Training will take significant time and resources.")
    response = input("Start training now? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Training cancelled.")
        return 0
    
    # Train model
    model_path = train_model(data_yaml)
    
    if not model_path:
        return 1
    
    # Validate
    if not validate_model(model_path):
        return 1
    
    # Show next steps
    show_next_steps()
    
    print("\n✅ Training complete!")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
