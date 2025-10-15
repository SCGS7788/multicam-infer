#!/usr/bin/env python3.11
"""
Verification script to check project structure without requiring dependencies.
"""

import sys
from pathlib import Path

def check_file_exists(path: Path, description: str) -> bool:
    """Check if a file exists."""
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def main():
    """Run verification checks."""
    project_root = Path(__file__).parent
    src_dir = project_root / "src" / "kvs_infer"
    
    print("=" * 60)
    print("kvs-infer Project Structure Verification")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # Core files
    print("📦 Core Application Files:")
    all_passed &= check_file_exists(src_dir / "__init__.py", "Package init")
    all_passed &= check_file_exists(src_dir / "__main__.py", "Module entry point")
    all_passed &= check_file_exists(src_dir / "app.py", "Main application")
    all_passed &= check_file_exists(src_dir / "config.py", "Configuration")
    print()
    
    # Frame source
    print("🎥 Frame Source Modules:")
    frame_source = src_dir / "frame_source"
    all_passed &= check_file_exists(frame_source / "__init__.py", "Frame source init")
    all_passed &= check_file_exists(frame_source / "kvs_hls.py", "KVS HLS reader")
    all_passed &= check_file_exists(frame_source / "getmedia_stub.py", "GetMedia stub")
    print()
    
    # Detectors
    print("🔍 Detector Modules:")
    detectors = src_dir / "detectors"
    all_passed &= check_file_exists(detectors / "__init__.py", "Detectors init")
    all_passed &= check_file_exists(detectors / "base.py", "Base detector")
    all_passed &= check_file_exists(detectors / "yolo_common.py", "YOLO common")
    all_passed &= check_file_exists(detectors / "weapon.py", "Weapon detector")
    all_passed &= check_file_exists(detectors / "fire_smoke.py", "Fire/smoke detector")
    all_passed &= check_file_exists(detectors / "alpr.py", "ALPR detector")
    print()
    
    # Publishers
    print("📤 Publisher Modules:")
    publishers = src_dir / "publishers"
    all_passed &= check_file_exists(publishers / "__init__.py", "Publishers init")
    all_passed &= check_file_exists(publishers / "kds.py", "Kinesis Data Streams")
    all_passed &= check_file_exists(publishers / "s3.py", "S3 uploader")
    all_passed &= check_file_exists(publishers / "ddb.py", "DynamoDB writer")
    print()
    
    # Utils
    print("🛠️  Utility Modules:")
    utils = src_dir / "utils"
    all_passed &= check_file_exists(utils / "__init__.py", "Utils init")
    all_passed &= check_file_exists(utils / "log.py", "Logging")
    all_passed &= check_file_exists(utils / "metrics.py", "Metrics")
    all_passed &= check_file_exists(utils / "roi.py", "ROI utilities")
    all_passed &= check_file_exists(utils / "time.py", "Time utilities")
    print()
    
    # Config and docs
    print("📝 Configuration & Documentation:")
    all_passed &= check_file_exists(project_root / "config" / "cameras.example.yaml", "Example config")
    all_passed &= check_file_exists(project_root / "requirements.txt", "Requirements")
    all_passed &= check_file_exists(project_root / "setup.py", "Setup script")
    all_passed &= check_file_exists(project_root / "Dockerfile", "Dockerfile")
    all_passed &= check_file_exists(project_root / "README.md", "README")
    all_passed &= check_file_exists(project_root / "QUICKSTART.md", "Quick start guide")
    all_passed &= check_file_exists(project_root / ".gitignore", "Git ignore")
    all_passed &= check_file_exists(project_root / "run.sh", "Run script")
    print()
    
    # Test module import structure
    print("🧪 Testing Module Structure:")
    try:
        sys.path.insert(0, str(src_dir.parent))
        
        # Test import without dependencies
        print("   Checking Python syntax...")
        import ast
        
        test_files = [
            src_dir / "__init__.py",
            src_dir / "app.py",
            src_dir / "config.py",
        ]
        
        syntax_ok = True
        for file in test_files:
            try:
                with open(file) as f:
                    ast.parse(f.read())
                print(f"   ✅ {file.name} - syntax OK")
            except SyntaxError as e:
                print(f"   ❌ {file.name} - syntax error: {e}")
                syntax_ok = False
        
        all_passed &= syntax_ok
        print()
    except Exception as e:
        print(f"   ⚠️  Could not verify imports: {e}")
        print()
    
    # Summary
    print("=" * 60)
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print()
        print("Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run the app: ./run.sh --help")
        print("3. Configure cameras: cp config/cameras.example.yaml config/cameras.yaml")
        print("4. Start processing: ./run.sh --config config/cameras.yaml")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print()
        print("Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
