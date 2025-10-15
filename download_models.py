#!/usr/bin/env python3
"""
download_models.py - Python script สำหรับดาวน์โหลด YOLO models
"""

import os
import sys
import shutil
from pathlib import Path

def download_with_ultralytics():
    """Download models using Ultralytics package"""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ Error: ultralytics not installed")
        print("💡 Run: pip install ultralytics")
        return False
    
    models_dir = Path('models')
    models_dir.mkdir(exist_ok=True)
    
    print("🤖 Downloading YOLOv8 models using Ultralytics...")
    print("=" * 60)
    print()
    
    sizes = {
        'n': 'nano (smallest, fastest)',
        's': 'small (balanced)',
        'm': 'medium (better accuracy)'
    }
    
    for size, desc in sizes.items():
        print(f"📦 Downloading YOLOv8{size} - {desc}...")
        try:
            # Initialize YOLO - this will auto-download the model
            model = YOLO(f'yolov8{size}.pt')
            
            # Find the downloaded model in cache
            cache_path = Path.home() / '.ultralytics' / 'weights' / f'yolov8{size}.pt'
            target_path = models_dir / f'yolov8{size}.pt'
            
            if cache_path.exists() and not target_path.exists():
                shutil.copy(cache_path, target_path)
                size_mb = target_path.stat().st_size / (1024 * 1024)
                print(f"✅ Copied to models/yolov8{size}.pt ({size_mb:.1f} MB)")
            elif target_path.exists():
                print(f"⏭️  models/yolov8{size}.pt already exists")
            else:
                print(f"⚠️  Could not find downloaded model in cache")
        except Exception as e:
            print(f"❌ Error downloading YOLOv8{size}: {e}")
    
    print()
    return True

def create_detector_models():
    """Create detector-specific model copies"""
    models_dir = Path('models')
    base_model = models_dir / 'yolov8n.pt'
    
    if not base_model.exists():
        print("❌ Base model yolov8n.pt not found")
        return False
    
    print("2️⃣  Creating Detector-Specific Models")
    print("-" * 60)
    
    detectors = [
        ('weapon', 'Weapon Detection'),
        ('fire-smoke', 'Fire & Smoke Detection'),
        ('license-plate', 'License Plate Detection (ALPR)')
    ]
    
    for detector_name, desc in detectors:
        target = models_dir / f'{detector_name}-yolov8n.pt'
        if not target.exists():
            shutil.copy(base_model, target)
            print(f"✅ Created {target.name} ({desc})")
        else:
            print(f"⏭️  {target.name} already exists")
    
    print()
    return True

def list_models():
    """List all downloaded models"""
    models_dir = Path('models')
    print("📋 Downloaded Models")
    print("-" * 60)
    
    if not models_dir.exists():
        print("No models directory found")
        return
    
    models = sorted(models_dir.glob('*.pt'))
    if not models:
        print("No .pt files found")
        return
    
    total_size = 0
    for model in models:
        size_mb = model.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  📄 {model.name:30} {size_mb:6.1f} MB")
    
    print("-" * 60)
    print(f"  Total: {len(models)} models, {total_size:.1f} MB")
    print()

def show_instructions():
    """Show post-download instructions"""
    print("⚠️  IMPORTANT NOTES")
    print("=" * 60)
    print()
    print("📌 These are BASE models trained on COCO dataset.")
    print("   They can detect general objects (person, car, etc.)")
    print("   but NOT specialized objects like:")
    print("   • Weapons (guns, knives)")
    print("   • Fire and smoke")
    print("   • License plates")
    print()
    print("🎯 For PRODUCTION, replace with CUSTOM models:")
    print()
    print("   1️⃣  Weapon Detection:")
    print("      URL: https://universe.roboflow.com/search?q=weapon")
    print("      Replace: models/weapon-yolov8n.pt")
    print()
    print("   2️⃣  Fire & Smoke Detection:")
    print("      URL: https://universe.roboflow.com/search?q=fire+smoke")
    print("      Replace: models/fire-smoke-yolov8n.pt")
    print()
    print("   3️⃣  License Plate Detection:")
    print("      URL: https://universe.roboflow.com/search?q=license+plate")
    print("      Replace: models/license-plate-yolov8n.pt")
    print()
    print("📖 Read MODELS_GUIDE.md for detailed instructions")
    print()

def main():
    print("🤖 YOLOv8 Models Download Script (Python)")
    print("=" * 60)
    print()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print(f"📂 Working directory: {script_dir}")
    print()
    
    # Download base models
    if not download_with_ultralytics():
        print()
        print("💡 Alternative: Run the bash script instead:")
        print("   chmod +x download-models.sh")
        print("   ./download-models.sh")
        return 1
    
    # Create detector copies
    if not create_detector_models():
        return 1
    
    # List all models
    list_models()
    
    # Show instructions
    show_instructions()
    
    print("✅ Setup complete!")
    print()
    print("🚀 Next steps:")
    print("   1. Edit config/cameras.yaml")
    print("   2. Enable detectors (uncomment detector sections)")
    print("   3. Run: ./run.sh")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
