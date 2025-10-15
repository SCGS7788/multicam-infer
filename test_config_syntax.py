#!/usr/bin/env python3.11
"""
Test configuration syntax without dependencies.
Only checks Python syntax and basic structure.
"""

import ast
import sys
from pathlib import Path


def check_python_syntax(file_path: Path) -> bool:
    """Check if Python file has valid syntax."""
    try:
        with open(file_path) as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print(f"  ❌ Syntax error: {e}")
        return False


def check_yaml_syntax(file_path: Path) -> bool:
    """Basic YAML syntax check (without pyyaml)."""
    try:
        with open(file_path) as f:
            content = f.read()
        
        # Basic checks
        if not content.strip():
            print("  ❌ File is empty")
            return False
        
        # Check for common YAML issues
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for tabs (YAML doesn't allow tabs)
            if '\t' in line:
                print(f"  ❌ Line {i}: Contains tab character (YAML uses spaces)")
                return False
        
        print(f"  ✅ Basic YAML syntax looks OK ({len(lines)} lines)")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Run syntax checks."""
    print("=" * 70)
    print("Configuration Syntax Validation")
    print("=" * 70)
    print()
    
    project_root = Path(__file__).parent
    
    # Check config.py
    print("📝 Checking config.py syntax...")
    config_py = project_root / "src" / "kvs_infer" / "config.py"
    if not config_py.exists():
        print(f"  ❌ File not found: {config_py}")
        return 1
    
    if not check_python_syntax(config_py):
        return 1
    print("  ✅ config.py syntax is valid")
    print()
    
    # Check app.py
    print("📝 Checking app.py syntax...")
    app_py = project_root / "src" / "kvs_infer" / "app.py"
    if not check_python_syntax(app_py):
        return 1
    print("  ✅ app.py syntax is valid")
    print()
    
    # Check example YAML
    print("📝 Checking cameras.example.yaml...")
    example_yaml = project_root / "config" / "cameras.example.yaml"
    if not example_yaml.exists():
        print(f"  ❌ File not found: {example_yaml}")
        return 1
    
    if not check_yaml_syntax(example_yaml):
        return 1
    print()
    
    # Count features in example YAML
    print("📊 Example YAML structure:")
    with open(example_yaml) as f:
        content = f.read()
        
    cameras = content.count('  - id:')
    weapon_detectors = content.count('type: weapon')
    fire_detectors = content.count('type: fire_smoke')
    alpr_detectors = content.count('type: alpr')
    roi_configs = content.count('roi:')
    
    print(f"  • Cameras defined: {cameras}")
    print(f"  • Weapon detectors: {weapon_detectors}")
    print(f"  • Fire/smoke detectors: {fire_detectors}")
    print(f"  • ALPR detectors: {alpr_detectors}")
    print(f"  • ROI configurations: {roi_configs}")
    print()
    
    # Check for required sections
    print("📋 Required sections:")
    required = ["aws:", "publishers:", "service:", "snapshots:", "cameras:"]
    for section in required:
        if section in content:
            print(f"  ✅ {section}")
        else:
            print(f"  ❌ Missing: {section}")
            return 1
    print()
    
    # Check for detector configs
    print("🔍 Detector configurations:")
    detector_configs = ["weapon:", "fire_smoke:", "alpr:"]
    for config in detector_configs:
        if config in content:
            print(f"  ✅ {config}")
    print()
    
    print("=" * 70)
    print("✅ ALL SYNTAX CHECKS PASSED!")
    print()
    print("Configuration is ready. To use:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Copy config: cp config/cameras.example.yaml config/cameras.yaml")
    print("3. Edit config/cameras.yaml with your AWS resources")
    print("4. Test: PYTHONPATH=src python -c 'from kvs_infer.config import load_yaml; print(load_yaml(\"config/cameras.example.yaml\"))'")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
