#!/usr/bin/env python3
"""
Validation script for Step 7: ROI & Temporal smoothing

Validates:
1. utils/roi.py structure and functions
2. Point-in-polygon implementation (Shapely-free)
3. IoU calculation (Shapely-free)
4. filter_boxes_by_roi with multiple modes
5. TemporalBuffer class and operations
6. temporal_confirm function
7. Detector integration (weapon, fire_smoke)
8. ROI filtering modes
9. Temporal confirmation logic

Run: python3 validate_step7.py
"""

import sys
from pathlib import Path
import inspect

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_mark(passed: bool) -> str:
    """Return colored checkmark or X."""
    return f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"


def print_header(text: str):
    """Print section header."""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")


def validate_roi_file_structure() -> bool:
    """Validate utils/roi.py file structure and exports."""
    print("\n📁 Validating utils/roi.py file structure...")
    
    try:
        roi_file = Path("src/kvs_infer/utils/roi.py")
        
        if not roi_file.exists():
            print(f"{RED}✗ File not found: {roi_file}{RESET}")
            return False
        
        print(f"{GREEN}✓ File exists: {roi_file}{RESET}")
        
        # Read file content
        content = roi_file.read_text()
        
        # Check for required functions
        required_functions = [
            "point_in_polygon",
            "iou",
            "filter_boxes_by_roi",
            "bbox_overlaps_roi",
            "temporal_confirm",
        ]
        
        for func in required_functions:
            if f"def {func}" in content:
                print(f"{GREEN}✓ Function exists: {func}{RESET}")
            else:
                print(f"{RED}✗ Function missing: {func}{RESET}")
                return False
        
        # Check for TemporalBuffer class
        if "class TemporalBuffer" in content:
            print(f"{GREEN}✓ Class exists: TemporalBuffer{RESET}")
        else:
            print(f"{RED}✗ Class missing: TemporalBuffer{RESET}")
            return False
        
        # Check for key phrases (Shapely-free implementation)
        if "Shapely-free" in content:
            print(f"{GREEN}✓ Shapely-free implementation confirmed{RESET}")
        else:
            print(f"{YELLOW}⚠ No explicit 'Shapely-free' mention{RESET}")
        
        # Check file size
        lines = content.count('\n')
        print(f"{GREEN}✓ File size: {lines} lines{RESET}")
        
        if lines < 400:
            print(f"{YELLOW}⚠ File seems small ({lines} lines), expected ~500+{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error validating file: {e}{RESET}")
        return False


def validate_point_in_polygon() -> bool:
    """Validate point_in_polygon function."""
    print("\n🔺 Validating point_in_polygon function...")
    
    try:
        from src.kvs_infer.utils import point_in_polygon
        
        # Test 1: Point inside square
        square = [(0, 0), (100, 0), (100, 100), (0, 100)]
        inside_point = (50, 50)
        
        result = point_in_polygon(inside_point, square)
        if result:
            print(f"{GREEN}✓ Test 1 passed: Point (50, 50) inside square{RESET}")
        else:
            print(f"{RED}✗ Test 1 failed: Point (50, 50) should be inside square{RESET}")
            return False
        
        # Test 2: Point outside square
        outside_point = (150, 50)
        result = point_in_polygon(outside_point, square)
        if not result:
            print(f"{GREEN}✓ Test 2 passed: Point (150, 50) outside square{RESET}")
        else:
            print(f"{RED}✗ Test 2 failed: Point (150, 50) should be outside square{RESET}")
            return False
        
        # Test 3: Point on edge (boundary case)
        edge_point = (0, 50)
        result = point_in_polygon(edge_point, square)
        print(f"{GREEN}✓ Test 3: Point (0, 50) on edge = {result}{RESET}")
        
        # Test 4: Complex polygon (triangle)
        triangle = [(0, 0), (100, 0), (50, 100)]
        result = point_in_polygon((50, 30), triangle)
        if result:
            print(f"{GREEN}✓ Test 4 passed: Point inside triangle{RESET}")
        else:
            print(f"{RED}✗ Test 4 failed: Point should be inside triangle{RESET}")
            return False
        
        # Test 5: Empty polygon
        result = point_in_polygon((50, 50), [])
        if not result:
            print(f"{GREEN}✓ Test 5 passed: Empty polygon returns False{RESET}")
        else:
            print(f"{RED}✗ Test 5 failed: Empty polygon should return False{RESET}")
            return False
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def validate_iou() -> bool:
    """Validate IoU calculation."""
    print("\n📐 Validating iou function...")
    
    try:
        from src.kvs_infer.utils import iou
        
        # Test 1: Perfect overlap (identical boxes)
        box1 = [0, 0, 100, 100]
        box2 = [0, 0, 100, 100]
        result = iou(box1, box2)
        
        if abs(result - 1.0) < 0.001:
            print(f"{GREEN}✓ Test 1 passed: Identical boxes IoU = {result:.3f}{RESET}")
        else:
            print(f"{RED}✗ Test 1 failed: IoU should be 1.0, got {result:.3f}{RESET}")
            return False
        
        # Test 2: No overlap
        box1 = [0, 0, 50, 50]
        box2 = [100, 100, 150, 150]
        result = iou(box1, box2)
        
        if result == 0.0:
            print(f"{GREEN}✓ Test 2 passed: No overlap IoU = {result}{RESET}")
        else:
            print(f"{RED}✗ Test 2 failed: IoU should be 0.0, got {result:.3f}{RESET}")
            return False
        
        # Test 3: Partial overlap
        box1 = [0, 0, 100, 100]
        box2 = [50, 50, 150, 150]
        result = iou(box1, box2)
        
        # Expected: intersection = 50x50 = 2500
        # Union = 10000 + 10000 - 2500 = 17500
        # IoU = 2500 / 17500 = 0.142857
        expected = 2500 / 17500
        
        if abs(result - expected) < 0.001:
            print(f"{GREEN}✓ Test 3 passed: Partial overlap IoU = {result:.3f} (expected {expected:.3f}){RESET}")
        else:
            print(f"{RED}✗ Test 3 failed: IoU should be {expected:.3f}, got {result:.3f}{RESET}")
            return False
        
        # Test 4: One box inside another
        box1 = [0, 0, 100, 100]
        box2 = [25, 25, 75, 75]
        result = iou(box1, box2)
        
        # intersection = 50x50 = 2500
        # union = 10000 + 2500 - 2500 = 10000
        # IoU = 2500 / 10000 = 0.25
        expected = 0.25
        
        if abs(result - expected) < 0.001:
            print(f"{GREEN}✓ Test 4 passed: Nested boxes IoU = {result:.3f}{RESET}")
        else:
            print(f"{RED}✗ Test 4 failed: IoU should be {expected:.3f}, got {result:.3f}{RESET}")
            return False
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def validate_filter_boxes_by_roi() -> bool:
    """Validate filter_boxes_by_roi function."""
    print("\n🎯 Validating filter_boxes_by_roi function...")
    
    try:
        from src.kvs_infer.utils import filter_boxes_by_roi
        
        # Test data
        boxes = [
            ("person", 0.9, [20, 20, 80, 80]),    # Inside ROI
            ("person", 0.85, [150, 150, 210, 210]),  # Outside ROI
            ("car", 0.75, [90, 90, 150, 150]),    # Partially overlapping
        ]
        
        roi = [(0, 0), (100, 0), (100, 100), (0, 100)]  # Left square
        
        # Test 1: Mode "center"
        filtered = filter_boxes_by_roi(boxes, [roi], mode="center")
        
        if len(filtered) == 1 and filtered[0][0] == "person":
            print(f"{GREEN}✓ Test 1 passed: Mode 'center' filtered correctly (1 box){RESET}")
        else:
            print(f"{RED}✗ Test 1 failed: Expected 1 box, got {len(filtered)}{RESET}")
            return False
        
        # Test 2: Mode "any" (any corner inside)
        filtered = filter_boxes_by_roi(boxes, [roi], mode="any")
        
        if len(filtered) >= 1:
            print(f"{GREEN}✓ Test 2 passed: Mode 'any' filtered correctly ({len(filtered)} boxes){RESET}")
        else:
            print(f"{RED}✗ Test 2 failed: Expected at least 1 box{RESET}")
            return False
        
        # Test 3: No ROI (should return all boxes)
        filtered = filter_boxes_by_roi(boxes, None, mode="center")
        
        if len(filtered) == 3:
            print(f"{GREEN}✓ Test 3 passed: No ROI returns all boxes{RESET}")
        else:
            print(f"{RED}✗ Test 3 failed: Expected 3 boxes, got {len(filtered)}{RESET}")
            return False
        
        # Test 4: Empty ROI list (should return all boxes)
        filtered = filter_boxes_by_roi(boxes, [], mode="center")
        
        if len(filtered) == 3:
            print(f"{GREEN}✓ Test 4 passed: Empty ROI list returns all boxes{RESET}")
        else:
            print(f"{RED}✗ Test 4 failed: Expected 3 boxes, got {len(filtered)}{RESET}")
            return False
        
        # Test 5: Invalid mode (should raise error)
        try:
            filtered = filter_boxes_by_roi(boxes, [roi], mode="invalid")
            print(f"{RED}✗ Test 5 failed: Should raise ValueError for invalid mode{RESET}")
            return False
        except ValueError:
            print(f"{GREEN}✓ Test 5 passed: Raises ValueError for invalid mode{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def validate_temporal_buffer() -> bool:
    """Validate TemporalBuffer class."""
    print("\n⏱️  Validating TemporalBuffer class...")
    
    try:
        from src.kvs_infer.utils import TemporalBuffer
        
        # Test 1: Create buffer
        buffer = TemporalBuffer(maxlen=5)
        
        if buffer.size() == 0 and buffer.is_empty():
            print(f"{GREEN}✓ Test 1 passed: Buffer initialized (empty){RESET}")
        else:
            print(f"{RED}✗ Test 1 failed: Buffer should be empty{RESET}")
            return False
        
        # Test 2: Add detections
        buffer.add("weapon", [100, 100, 200, 200], 0.9, frame_idx=1)
        buffer.add("weapon", [102, 98, 202, 198], 0.88, frame_idx=2)
        buffer.add("weapon", [101, 99, 201, 199], 0.91, frame_idx=3)
        
        if buffer.size() == 3:
            print(f"{GREEN}✓ Test 2 passed: Added 3 detections (size={buffer.size()}){RESET}")
        else:
            print(f"{RED}✗ Test 2 failed: Expected size=3, got {buffer.size()}{RESET}")
            return False
        
        # Test 3: Count similar detections
        count = buffer.count_similar("weapon", [101, 100, 201, 200], iou_threshold=0.5)
        
        if count >= 2:
            print(f"{GREEN}✓ Test 3 passed: Found {count} similar detections{RESET}")
        else:
            print(f"{RED}✗ Test 3 failed: Expected at least 2 similar, got {count}{RESET}")
            return False
        
        # Test 4: Get recent detections
        recent = buffer.get_recent(n=2)
        
        if len(recent) == 2:
            print(f"{GREEN}✓ Test 4 passed: Retrieved {len(recent)} recent detections{RESET}")
        else:
            print(f"{RED}✗ Test 4 failed: Expected 2 recent, got {len(recent)}{RESET}")
            return False
        
        # Test 5: Clear buffer
        buffer.clear()
        
        if buffer.is_empty():
            print(f"{GREEN}✓ Test 5 passed: Buffer cleared{RESET}")
        else:
            print(f"{RED}✗ Test 5 failed: Buffer should be empty after clear{RESET}")
            return False
        
        # Test 6: Maxlen enforcement
        buffer = TemporalBuffer(maxlen=3)
        for i in range(5):
            buffer.add("test", [0, 0, 10, 10], 0.9, frame_idx=i)
        
        if buffer.size() == 3:
            print(f"{GREEN}✓ Test 6 passed: Maxlen enforced (size={buffer.size()}){RESET}")
        else:
            print(f"{RED}✗ Test 6 failed: Expected size=3 (maxlen), got {buffer.size()}{RESET}")
            return False
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def validate_temporal_confirm() -> bool:
    """Validate temporal_confirm function."""
    print("\n✅ Validating temporal_confirm function...")
    
    try:
        from src.kvs_infer.utils import TemporalBuffer, temporal_confirm
        
        # Test 1: Progressive confirmation
        buffer = TemporalBuffer(maxlen=10)
        
        # Frame 1 - not confirmed yet
        confirmed = temporal_confirm(buffer, "weapon", [100, 100, 200, 200], 0.9, min_confirmations=3)
        if not confirmed:
            print(f"{GREEN}✓ Test 1a passed: Frame 1 not confirmed (need 3){RESET}")
        else:
            print(f"{RED}✗ Test 1a failed: Should not be confirmed on frame 1{RESET}")
            return False
        
        # Frame 2 - still not confirmed
        confirmed = temporal_confirm(buffer, "weapon", [102, 98, 202, 198], 0.88, min_confirmations=3)
        if not confirmed:
            print(f"{GREEN}✓ Test 1b passed: Frame 2 not confirmed (need 3){RESET}")
        else:
            print(f"{RED}✗ Test 1b failed: Should not be confirmed on frame 2{RESET}")
            return False
        
        # Frame 3 - NOW confirmed!
        confirmed = temporal_confirm(buffer, "weapon", [101, 99, 201, 199], 0.91, min_confirmations=3)
        if confirmed:
            print(f"{GREEN}✓ Test 1c passed: Frame 3 CONFIRMED (3 similar detections){RESET}")
        else:
            print(f"{RED}✗ Test 1c failed: Should be confirmed on frame 3{RESET}")
            return False
        
        # Test 2: Different label (shouldn't match)
        buffer2 = TemporalBuffer(maxlen=10)
        buffer2.add("weapon", [100, 100, 200, 200], 0.9)
        buffer2.add("weapon", [102, 98, 202, 198], 0.88)
        
        confirmed = temporal_confirm(buffer2, "knife", [101, 99, 201, 199], 0.91, min_confirmations=2)
        if not confirmed:
            print(f"{GREEN}✓ Test 2 passed: Different label not confirmed{RESET}")
        else:
            print(f"{RED}✗ Test 2 failed: Different label should not match{RESET}")
            return False
        
        # Test 3: Low IoU (shouldn't match)
        buffer3 = TemporalBuffer(maxlen=10)
        buffer3.add("weapon", [10, 10, 50, 50], 0.9)
        buffer3.add("weapon", [12, 12, 52, 52], 0.88)
        
        confirmed = temporal_confirm(
            buffer3, "weapon", [500, 500, 600, 600], 0.91,
            min_confirmations=2, iou_threshold=0.5
        )
        if not confirmed:
            print(f"{GREEN}✓ Test 3 passed: Low IoU not confirmed{RESET}")
        else:
            print(f"{RED}✗ Test 3 failed: Low IoU should not match{RESET}")
            return False
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def validate_detector_integration() -> bool:
    """Validate detector integration with new ROI and temporal utilities."""
    print("\n🔧 Validating detector integration...")
    
    try:
        # Check weapon detector
        weapon_file = Path("src/kvs_infer/detectors/weapon.py")
        weapon_content = weapon_file.read_text()
        
        # Check imports
        if "from ..utils import filter_boxes_by_roi" in weapon_content:
            print(f"{GREEN}✓ WeaponDetector imports filter_boxes_by_roi{RESET}")
        else:
            print(f"{RED}✗ WeaponDetector missing filter_boxes_by_roi import{RESET}")
            return False
        
        if "TemporalBuffer" in weapon_content:
            print(f"{GREEN}✓ WeaponDetector imports TemporalBuffer{RESET}")
        else:
            print(f"{RED}✗ WeaponDetector missing TemporalBuffer import{RESET}")
            return False
        
        # Check configuration options
        if "roi_filter_mode" in weapon_content:
            print(f"{GREEN}✓ WeaponDetector has roi_filter_mode config{RESET}")
        else:
            print(f"{YELLOW}⚠ WeaponDetector missing roi_filter_mode config{RESET}")
        
        if "use_temporal_buffer" in weapon_content:
            print(f"{GREEN}✓ WeaponDetector has use_temporal_buffer config{RESET}")
        else:
            print(f"{YELLOW}⚠ WeaponDetector missing use_temporal_buffer config{RESET}")
        
        # Check process method usage
        if "filter_boxes_by_roi(" in weapon_content:
            print(f"{GREEN}✓ WeaponDetector uses filter_boxes_by_roi in process(){RESET}")
        else:
            print(f"{RED}✗ WeaponDetector not using filter_boxes_by_roi{RESET}")
            return False
        
        # Check fire_smoke detector
        fire_smoke_file = Path("src/kvs_infer/detectors/fire_smoke.py")
        fire_smoke_content = fire_smoke_file.read_text()
        
        if "from ..utils import filter_boxes_by_roi" in fire_smoke_content:
            print(f"{GREEN}✓ FireSmokeDetector imports filter_boxes_by_roi{RESET}")
        else:
            print(f"{YELLOW}⚠ FireSmokeDetector missing new imports (optional){RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def validate_utils_exports() -> bool:
    """Validate utils/__init__.py exports."""
    print("\n📦 Validating utils/__init__.py exports...")
    
    try:
        from src.kvs_infer import utils
        
        required_exports = [
            "point_in_polygon",
            "iou",
            "filter_boxes_by_roi",
            "TemporalBuffer",
            "temporal_confirm",
        ]
        
        for export in required_exports:
            if hasattr(utils, export):
                print(f"{GREEN}✓ Exported: {export}{RESET}")
            else:
                print(f"{RED}✗ Not exported: {export}{RESET}")
                return False
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation checks."""
    print_header("Step 7: ROI & Temporal Smoothing Validation")
    
    checks = [
        ("ROI File Structure", validate_roi_file_structure),
        ("Point-in-Polygon", validate_point_in_polygon),
        ("IoU Calculation", validate_iou),
        ("Filter Boxes by ROI", validate_filter_boxes_by_roi),
        ("Temporal Buffer", validate_temporal_buffer),
        ("Temporal Confirm", validate_temporal_confirm),
        ("Detector Integration", validate_detector_integration),
        ("Utils Exports", validate_utils_exports),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            passed = check_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n{RED}✗ {name} raised exception: {e}{RESET}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print_header("Validation Summary")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = f"{GREEN}PASSED{RESET}" if passed else f"{RED}FAILED{RESET}"
        print(f"{check_mark(passed)} {name}: {status}")
    
    print(f"\n{BLUE}{'='*80}{RESET}")
    
    if passed_count == total_count:
        print(f"{GREEN}✓ All checks passed ({passed_count}/{total_count}){RESET}")
        print(f"{GREEN}Step 7 implementation is complete and valid!{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some checks failed ({passed_count}/{total_count}){RESET}")
        print(f"{RED}Please review the failures above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
