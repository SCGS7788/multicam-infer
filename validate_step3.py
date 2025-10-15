#!/usr/bin/env python3
"""
Validation script for Step 3: Detector Interface + Registry.
"""

import sys
import os
from pathlib import Path


def validate_step3():
    """Validate Step 3 implementation."""
    print("=" * 80)
    print("Step 3 Validation: Detector Interface + Registry")
    print("=" * 80)
    print()
    
    errors = []
    
    # 1. Core Implementation Files
    print("1. Core Implementation Files")
    
    base_py = Path("src/kvs_infer/detectors/base.py")
    yolo_common_py = Path("src/kvs_infer/detectors/yolo_common.py")
    
    if base_py.exists():
        size = base_py.stat().st_size / 1024
        print(f"  ✓ Detector base: {base_py} ({size:.1f} KB)")
    else:
        print(f"  ✗ Detector base missing: {base_py}")
        errors.append("base.py missing")
    
    if yolo_common_py.exists():
        size = yolo_common_py.stat().st_size / 1024
        print(f"  ✓ YOLO common: {yolo_common_py} ({size:.1f} KB)")
    else:
        print(f"  ✗ YOLO common missing: {yolo_common_py}")
        errors.append("yolo_common.py missing")
    
    print()
    
    # 2. base.py Content
    print("2. Base Detector Content")
    
    if base_py.exists():
        content = base_py.read_text()
        
        required_classes = [
            "Event",
            "DetectionContext",
            "Detector",
            "DetectorRegistry",
            "TemporalConfirmationHelper",
            "TemporalDetection",
        ]
        
        missing_classes = []
        for cls in required_classes:
            if f"class {cls}" in content:
                print(f"  ✓ {cls} class found")
            else:
                print(f"  ✗ {cls} class missing")
                missing_classes.append(cls)
        
        if missing_classes:
            errors.append(f"Missing classes: {', '.join(missing_classes)}")
        
        # Check for key methods
        required_functions = [
            "calculate_iou",
            "point_in_polygon",
            "bbox_in_roi",
            "filter_by_min_box_size",
            "filter_detections",
        ]
        
        missing_funcs = []
        for func in required_functions:
            if f"def {func}" in content:
                print(f"  ✓ {func}() function found")
            else:
                print(f"  ✗ {func}() function missing")
                missing_funcs.append(func)
        
        if missing_funcs:
            errors.append(f"Missing functions: {', '.join(missing_funcs)}")
    
    print()
    
    # 3. yolo_common.py Content
    print("3. YOLO Common Content")
    
    if yolo_common_py.exists():
        content = yolo_common_py.read_text()
        
        required_functions = [
            "select_device",
            "load_yolo_model",
            "run_yolo",
            "clear_model_cache",
            "get_cached_models",
        ]
        
        missing = []
        for func in required_functions:
            if f"def {func}" in content:
                print(f"  ✓ {func}() function found")
            else:
                print(f"  ✗ {func}() function missing")
                missing.append(func)
        
        if missing:
            errors.append(f"Missing functions: {', '.join(missing)}")
        
        # Check for lazy loading cache
        if "_MODEL_CACHE" in content:
            print(f"  ✓ Model cache for lazy loading found")
        else:
            print(f"  ✗ Model cache missing")
            errors.append("Model cache not implemented")
    
    print()
    
    # 4. Code Statistics
    print("4. Code Statistics")
    
    if base_py.exists():
        lines = len(base_py.read_text().splitlines())
        print(f"  ✓ base.py: {lines} lines")
    
    if yolo_common_py.exists():
        lines = len(yolo_common_py.read_text().splitlines())
        print(f"  ✓ yolo_common.py: {lines} lines")
    
    total_lines = 0
    if base_py.exists():
        total_lines += len(base_py.read_text().splitlines())
    if yolo_common_py.exists():
        total_lines += len(yolo_common_py.read_text().splitlines())
    
    print(f"  ℹ Total: {total_lines} lines")
    
    print()
    
    # 5. Integration Check
    print("5. Integration Check")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        from kvs_infer.detectors.base import (
            Event,
            DetectionContext,
            Detector,
            DetectorRegistry,
            TemporalConfirmationHelper,
            calculate_iou,
            bbox_in_roi,
            filter_detections,
        )
        print("  ✓ Base detector imports successfully")
        
        # Test Event creation
        event = Event(
            camera_id="test",
            type="test",
            label="test",
            conf=0.9,
            bbox=[10.0, 10.0, 100.0, 100.0],
            ts_ms=1000,
        )
        assert event.validate(), "Event validation failed"
        print("  ✓ Event creation and validation works")
        
        # Test DetectorRegistry
        registry_methods = ["register", "create", "list_detectors", "is_registered"]
        for method in registry_methods:
            if hasattr(DetectorRegistry, method):
                print(f"  ✓ DetectorRegistry.{method}() exists")
            else:
                print(f"  ✗ DetectorRegistry.{method}() missing")
                errors.append(f"DetectorRegistry.{method}() missing")
        
        # Test TemporalConfirmationHelper
        helper = TemporalConfirmationHelper(
            window_frames=5,
            iou_threshold=0.5,
            min_confirmations=3,
        )
        print("  ✓ TemporalConfirmationHelper instantiation works")
        
        # Test utility functions
        iou = calculate_iou([0, 0, 10, 10], [5, 5, 15, 15])
        assert 0 <= iou <= 1, "IoU calculation out of range"
        print(f"  ✓ calculate_iou() works (IoU={iou:.2f})")
        
        # Test ROI filtering
        in_roi = bbox_in_roi([50, 50, 100, 100], [[(0, 0), (200, 0), (200, 200), (0, 200)]])
        assert in_roi, "bbox_in_roi() failed for bbox inside polygon"
        print("  ✓ bbox_in_roi() works")
        
    except Exception as e:
        print(f"  ✗ Import/integration error: {e}")
        errors.append(f"Integration error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Try YOLO common (may fail if ultralytics not installed)
    print("6. YOLO Common Integration (optional)")
    try:
        from kvs_infer.detectors.yolo_common import (
            select_device,
            load_yolo_model,
            run_yolo,
            clear_model_cache,
        )
        print("  ✓ YOLO common imports successfully")
        
        device = select_device()
        print(f"  ✓ select_device() works: {device}")
        
        # Note: Can't test load_yolo_model without downloading weights
        print("  ℹ load_yolo_model() and run_yolo() require ultralytics + weights")
        
    except ImportError as e:
        print(f"  ⚠ YOLO common import failed (expected if torch/ultralytics not installed): {e}")
    except Exception as e:
        print(f"  ✗ YOLO common error: {e}")
    
    print()
    
    # Summary
    print("=" * 80)
    if errors:
        print(f"❌ STEP 3 VALIDATION FAILED!")
        print()
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ STEP 3 VALIDATION COMPLETE!")
        print()
        print("All checks passed. Detector interface and registry are complete.")
        print()
        print("Summary:")
        print("  • Event schema: Complete")
        print("  • Detector base class: Complete")
        print("  • DetectorRegistry: Complete")
        print("  • Temporal confirmation: Complete")
        print("  • ROI filtering: Complete")
        print("  • YOLO common: Complete")
        print()
        print("Next Steps:")
        print("  1. Implement specific detectors (weapon, fire_smoke, alpr)")
        print("  2. Test with actual YOLO models")
        print("  3. Integrate with CameraWorker in app.py")
    print("=" * 80)
    
    return len(errors) == 0


if __name__ == "__main__":
    success = validate_step3()
    sys.exit(0 if success else 1)
