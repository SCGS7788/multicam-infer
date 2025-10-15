#!/usr/bin/env python3.11
"""
Validation script for Step 4: Specific Detector Implementations.

Validates:
1. File existence and sizes
2. Detector registration
3. Configuration interface
4. Process method signature
5. Deduplication logic
6. Integration checks
"""

import sys
import os
from pathlib import Path


def check_file(path: str, min_lines: int = 0) -> tuple:
    """Check if file exists and meets line count requirement."""
    p = Path(path)
    if not p.exists():
        return False, 0, 0
    
    size_kb = p.stat().st_size / 1024
    with open(p) as f:
        lines = len(f.readlines())
    
    return lines >= min_lines, lines, size_kb


def main():
    print("=" * 80)
    print("Step 4 Validation: Specific Detector Implementations")
    print("=" * 80)
    print()
    
    errors = []
    
    # 1. Check file existence
    print("1. Detector Implementation Files")
    
    files = {
        "weapon.py": ("src/kvs_infer/detectors/weapon.py", 200),
        "fire_smoke.py": ("src/kvs_infer/detectors/fire_smoke.py", 200),
        "alpr.py": ("src/kvs_infer/detectors/alpr.py", 200),
    }
    
    total_lines = 0
    
    for name, (path, min_lines) in files.items():
        ok, lines, size = check_file(path, min_lines)
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {path} ({size:.1f} KB, {lines} lines)")
        
        if not ok:
            errors.append(f"Missing or insufficient: {path}")
        
        total_lines += lines
    
    print(f"  ℹ Total: {total_lines} lines")
    print()
    
    # 2. Check detector registration
    print("2. Detector Registration")
    
    try:
        from kvs_infer.detectors.base import DetectorRegistry
        
        # Check registered detectors
        detectors = DetectorRegistry.list_detectors()
        
        required_detectors = ["weapon", "fire_smoke", "alpr"]
        
        for det_name in required_detectors:
            is_registered = DetectorRegistry.is_registered(det_name)
            status = "✓" if is_registered else "✗"
            print(f"  {status} {det_name} detector registered")
            
            if not is_registered:
                errors.append(f"{det_name} detector not registered")
        
        print(f"  ℹ Total registered: {detectors}")
        
    except Exception as e:
        print(f"  ✗ Registration check failed: {e}")
        errors.append(f"Registration check failed: {e}")
    
    print()
    
    # 3. Check detector imports
    print("3. Detector Imports")
    
    try:
        from kvs_infer.detectors.weapon import WeaponDetector
        print("  ✓ WeaponDetector imports successfully")
    except Exception as e:
        print(f"  ✗ WeaponDetector import failed: {e}")
        errors.append(f"WeaponDetector import failed")
    
    try:
        from kvs_infer.detectors.fire_smoke import FireSmokeDetector
        print("  ✓ FireSmokeDetector imports successfully")
    except Exception as e:
        print(f"  ✗ FireSmokeDetector import failed: {e}")
        errors.append(f"FireSmokeDetector import failed")
    
    try:
        from kvs_infer.detectors.alpr import ALPRDetector
        print("  ✓ ALPRDetector imports successfully")
    except Exception as e:
        print(f"  ✗ ALPRDetector import failed: {e}")
        errors.append(f"ALPRDetector import failed")
    
    print()
    
    # 4. Check detector interface
    print("4. Detector Interface")
    
    try:
        from kvs_infer.detectors.weapon import WeaponDetector
        from kvs_infer.detectors.base import Detector
        
        detector = WeaponDetector()
        
        # Check inheritance
        if isinstance(detector, Detector):
            print("  ✓ WeaponDetector inherits from Detector")
        else:
            print("  ✗ WeaponDetector does not inherit from Detector")
            errors.append("WeaponDetector inheritance issue")
        
        # Check methods
        if hasattr(detector, "configure"):
            print("  ✓ configure() method exists")
        else:
            print("  ✗ configure() method missing")
            errors.append("configure() method missing")
        
        if hasattr(detector, "process"):
            print("  ✓ process() method exists")
        else:
            print("  ✗ process() method missing")
            errors.append("process() method missing")
        
        if hasattr(detector, "is_configured"):
            print("  ✓ is_configured() method exists")
        else:
            print("  ✗ is_configured() method missing")
            errors.append("is_configured() method missing")
        
    except Exception as e:
        print(f"  ✗ Interface check failed: {e}")
        errors.append(f"Interface check failed")
    
    print()
    
    # 5. Check deduplication logic
    print("5. Deduplication Logic")
    
    try:
        # Check for dedup functions in weapon.py
        with open("src/kvs_infer/detectors/weapon.py") as f:
            weapon_code = f.read()
        
        if "_detection_hash" in weapon_code:
            print("  ✓ _detection_hash() found in weapon.py")
        else:
            print("  ✗ _detection_hash() missing in weapon.py")
            errors.append("_detection_hash() missing")
        
        if "_bbox_to_grid" in weapon_code:
            print("  ✓ _bbox_to_grid() found in weapon.py")
        else:
            print("  ✗ _bbox_to_grid() missing in weapon.py")
            errors.append("_bbox_to_grid() missing")
        
        if "_recent_detections" in weapon_code:
            print("  ✓ Deduplication tracking found in weapon.py")
        else:
            print("  ✗ Deduplication tracking missing in weapon.py")
            errors.append("Deduplication tracking missing")
        
        # Check fire_smoke.py
        with open("src/kvs_infer/detectors/fire_smoke.py") as f:
            fire_code = f.read()
        
        if "_detection_hash" in fire_code:
            print("  ✓ _detection_hash() found in fire_smoke.py")
        else:
            print("  ✗ _detection_hash() missing in fire_smoke.py")
            errors.append("_detection_hash() missing in fire_smoke")
        
        # Check alpr.py
        with open("src/kvs_infer/detectors/alpr.py") as f:
            alpr_code = f.read()
        
        if "_detection_hash" in alpr_code:
            print("  ✓ _detection_hash() found in alpr.py")
        else:
            print("  ✗ _detection_hash() missing in alpr.py")
            errors.append("_detection_hash() missing in alpr")
        
    except Exception as e:
        print(f"  ✗ Deduplication check failed: {e}")
        errors.append(f"Deduplication check failed")
    
    print()
    
    # 6. Check temporal confirmation
    print("6. Temporal Confirmation")
    
    try:
        from kvs_infer.detectors.weapon import WeaponDetector
        
        detector = WeaponDetector()
        
        if hasattr(detector, "temporal_helper"):
            print("  ✓ temporal_helper attribute exists")
        else:
            print("  ✗ temporal_helper attribute missing")
            errors.append("temporal_helper missing")
        
        # Check fire_smoke
        from kvs_infer.detectors.fire_smoke import FireSmokeDetector
        detector2 = FireSmokeDetector()
        
        if hasattr(detector2, "temporal_helper"):
            print("  ✓ FireSmokeDetector has temporal_helper")
        else:
            print("  ✗ FireSmokeDetector missing temporal_helper")
            errors.append("FireSmokeDetector temporal_helper missing")
        
        # Check alpr
        from kvs_infer.detectors.alpr import ALPRDetector
        detector3 = ALPRDetector()
        
        if hasattr(detector3, "temporal_helper"):
            print("  ✓ ALPRDetector has temporal_helper")
        else:
            print("  ✗ ALPRDetector missing temporal_helper")
            errors.append("ALPRDetector temporal_helper missing")
        
    except Exception as e:
        print(f"  ✗ Temporal confirmation check failed: {e}")
        errors.append(f"Temporal confirmation check failed")
    
    print()
    
    # 7. Check ROI filtering integration
    print("7. ROI Filtering Integration")
    
    try:
        # Check for filter_detections usage
        with open("src/kvs_infer/detectors/weapon.py") as f:
            weapon_code = f.read()
        
        if "filter_detections" in weapon_code:
            print("  ✓ filter_detections() used in weapon.py")
        else:
            print("  ✗ filter_detections() not used in weapon.py")
            errors.append("ROI filtering missing in weapon")
        
        with open("src/kvs_infer/detectors/fire_smoke.py") as f:
            fire_code = f.read()
        
        if "filter_detections" in fire_code:
            print("  ✓ filter_detections() used in fire_smoke.py")
        else:
            print("  ✗ filter_detections() not used in fire_smoke.py")
            errors.append("ROI filtering missing in fire_smoke")
        
        with open("src/kvs_infer/detectors/alpr.py") as f:
            alpr_code = f.read()
        
        if "filter_detections" in alpr_code:
            print("  ✓ filter_detections() used in alpr.py")
        else:
            print("  ✗ filter_detections() not used in alpr.py")
            errors.append("ROI filtering missing in alpr")
        
    except Exception as e:
        print(f"  ✗ ROI filtering check failed: {e}")
        errors.append(f"ROI filtering check failed")
    
    print()
    
    # 8. Check ALPR-specific features
    print("8. ALPR-Specific Features")
    
    try:
        with open("src/kvs_infer/detectors/alpr.py") as f:
            alpr_code = f.read()
        
        if "_crop_and_pad_plate" in alpr_code:
            print("  ✓ _crop_and_pad_plate() found")
        else:
            print("  ✗ _crop_and_pad_plate() missing")
            errors.append("_crop_and_pad_plate() missing")
        
        if "ocr_engine" in alpr_code:
            print("  ✓ OCR engine configuration found")
        else:
            print("  ✗ OCR engine configuration missing")
            errors.append("OCR engine config missing")
        
        if "paddleocr" in alpr_code.lower():
            print("  ✓ PaddleOCR support found")
        else:
            print("  ✗ PaddleOCR support missing")
            errors.append("PaddleOCR support missing")
        
        if "tesseract" in alpr_code.lower() or "pytesseract" in alpr_code:
            print("  ✓ Tesseract support found")
        else:
            print("  ✗ Tesseract support missing")
            errors.append("Tesseract support missing")
        
        if '"text":' in alpr_code and '"ocr_conf":' in alpr_code:
            print("  ✓ OCR results in extras field")
        else:
            print("  ✗ OCR results not properly added to extras")
            errors.append("OCR extras missing")
        
    except Exception as e:
        print(f"  ✗ ALPR feature check failed: {e}")
        errors.append(f"ALPR feature check failed")
    
    print()
    
    # 9. Check fire/smoke separate thresholds
    print("9. Fire/Smoke Separate Thresholds")
    
    try:
        with open("src/kvs_infer/detectors/fire_smoke.py") as f:
            fire_code = f.read()
        
        if "fire_conf_threshold" in fire_code:
            print("  ✓ fire_conf_threshold found")
        else:
            print("  ✗ fire_conf_threshold missing")
            errors.append("fire_conf_threshold missing")
        
        if "smoke_conf_threshold" in fire_code:
            print("  ✓ smoke_conf_threshold found")
        else:
            print("  ✗ smoke_conf_threshold missing")
            errors.append("smoke_conf_threshold missing")
        
        if "fire_labels" in fire_code and "smoke_labels" in fire_code:
            print("  ✓ Separate fire/smoke labels")
        else:
            print("  ✗ Separate fire/smoke labels missing")
            errors.append("Separate labels missing")
        
        if 'type="fire"' in fire_code or 'type="smoke"' in fire_code:
            print("  ✓ Event type differentiation (fire vs smoke)")
        else:
            print("  ✗ Event type differentiation missing")
            errors.append("Event type differentiation missing")
        
    except Exception as e:
        print(f"  ✗ Fire/smoke threshold check failed: {e}")
        errors.append(f"Fire/smoke threshold check failed")
    
    print()
    
    # Summary
    print("=" * 80)
    if errors:
        print("❌ STEP 4 VALIDATION FAILED!")
        print()
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ STEP 4 VALIDATION COMPLETE!")
        print()
        print("All checks passed. Detector implementations are complete.")
        print()
        print("Summary:")
        print("  • Weapon detector: Complete")
        print("  • Fire/Smoke detector: Complete")
        print("  • ALPR detector: Complete")
        print("  • Temporal confirmation: Complete")
        print("  • Deduplication: Complete")
        print("  • ROI filtering: Complete")
        print()
        print("Next Steps:")
        print("  1. Create unit tests for each detector")
        print("  2. Test with actual YOLO models")
        print("  3. Test OCR engines (PaddleOCR, Tesseract)")
        print("  4. Integrate with CameraWorker in app.py")
    
    print("=" * 80)
    print()
    
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
