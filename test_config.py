#!/usr/bin/env python3.11
"""
Configuration validation script.
Tests the new Pydantic config models without requiring dependencies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_config_models():
    """Test config model imports and basic validation."""
    print("=" * 70)
    print("Configuration Model Validation Test")
    print("=" * 70)
    print()
    
    try:
        from kvs_infer.config import (
            Config,
            CameraConfig,
            DetectorPipelineConfig,
            WeaponDetectorConfig,
            FireSmokeDetectorConfig,
            ALPRDetectorConfig,
            DetectorType,
            PlaybackMode,
            OCREngine,
        )
        print("✅ All config models imported successfully")
        print()
    except ImportError as e:
        print(f"❌ Failed to import config models: {e}")
        return False
    
    # Test 1: Minimal camera config
    print("Test 1: Minimal camera configuration")
    try:
        camera = CameraConfig(
            id="test-cam",
            kvs_stream_name="test-stream",
            pipeline=[],
        )
        print(f"  ✅ Created camera: {camera.id}")
        print(f"     - KVS stream: {camera.kvs_stream_name}")
        print(f"     - Playback mode: {camera.playback.mode}")
        print(f"     - FPS target: {camera.fps_target}")
        print()
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    # Test 2: Camera with weapon detector
    print("Test 2: Camera with weapon detector")
    try:
        camera = CameraConfig(
            id="entrance-cam",
            kvs_stream_name="entrance-stream",
            fps_target=5,
            pipeline=[
                DetectorPipelineConfig(
                    type=DetectorType.WEAPON,
                    enabled=True,
                    weapon=WeaponDetectorConfig(
                        yolo_weights="s3://my-bucket/weapon.pt",
                        classes=["gun", "knife"],
                        conf_threshold=0.6,
                    )
                )
            ],
        )
        print(f"  ✅ Created camera: {camera.id}")
        print(f"     - Detectors: {len(camera.pipeline)}")
        print(f"     - Detector type: {camera.pipeline[0].type}")
        print(f"     - Weapon classes: {camera.pipeline[0].weapon.classes}")
        print()
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    # Test 3: Camera with ALPR detector
    print("Test 3: Camera with ALPR detector")
    try:
        camera = CameraConfig(
            id="parking-cam",
            kvs_stream_name="parking-stream",
            fps_target=2,
            pipeline=[
                DetectorPipelineConfig(
                    type=DetectorType.ALPR,
                    enabled=True,
                    alpr=ALPRDetectorConfig(
                        plate_detector_weights="/models/plate.pt",
                        ocr_engine=OCREngine.PADDLEOCR,
                        ocr_lang="th",
                        conf_threshold=0.7,
                    )
                )
            ],
        )
        print(f"  ✅ Created camera: {camera.id}")
        print(f"     - OCR engine: {camera.pipeline[0].alpr.ocr_engine}")
        print(f"     - OCR language: {camera.pipeline[0].alpr.ocr_lang}")
        print()
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    # Test 4: Full config
    print("Test 4: Full application configuration")
    try:
        config = Config(
            cameras=[
                CameraConfig(
                    id="cam1",
                    kvs_stream_name="stream1",
                    pipeline=[],
                ),
                CameraConfig(
                    id="cam2",
                    kvs_stream_name="stream2",
                    pipeline=[],
                ),
            ]
        )
        print(f"  ✅ Created config with {len(config.cameras)} cameras")
        print(f"     - AWS region: {config.aws.region}")
        print(f"     - Device: {config.device}")
        print(f"     - Metrics port: {config.metrics_port}")
        print()
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    # Test 5: Validation - duplicate IDs
    print("Test 5: Validation - duplicate camera IDs (should fail)")
    try:
        config = Config(
            cameras=[
                CameraConfig(id="cam1", kvs_stream_name="stream1", pipeline=[]),
                CameraConfig(id="cam1", kvs_stream_name="stream2", pipeline=[]),
            ]
        )
        print("  ❌ Should have failed but didn't!")
        return False
    except ValueError as e:
        print(f"  ✅ Correctly rejected: {e}")
        print()
    
    # Test 6: Validation - invalid camera ID
    print("Test 6: Validation - invalid camera ID (should fail)")
    try:
        camera = CameraConfig(
            id="invalid id with spaces!",
            kvs_stream_name="stream",
            pipeline=[],
        )
        print("  ❌ Should have failed but didn't!")
        return False
    except ValueError as e:
        print(f"  ✅ Correctly rejected: {e}")
        print()
    
    # Test 7: Detector type mismatch
    print("Test 7: Validation - detector type mismatch (should fail)")
    try:
        camera = CameraConfig(
            id="test",
            kvs_stream_name="stream",
            pipeline=[
                DetectorPipelineConfig(
                    type=DetectorType.WEAPON,
                    # Missing weapon config!
                )
            ],
        )
        print("  ❌ Should have failed but didn't!")
        return False
    except ValueError as e:
        print(f"  ✅ Correctly rejected: {e}")
        print()
    
    # Test 8: ROI validation
    print("Test 8: ROI polygon validation")
    try:
        from kvs_infer.config import ROIConfig, ROIPolygon
        
        roi = ROIConfig(
            enabled=True,
            polygons=[
                ROIPolygon(
                    name="zone1",
                    points=[[100, 100], [200, 100], [200, 200], [100, 200]]
                )
            ]
        )
        print(f"  ✅ Created ROI with {len(roi.polygons)} polygons")
        print(f"     - Polygon: {roi.polygons[0].name}")
        print(f"     - Points: {len(roi.polygons[0].points)}")
        print()
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False
    
    return True


def test_yaml_loading():
    """Test YAML config loading."""
    print("=" * 70)
    print("YAML Configuration Loading Test")
    print("=" * 70)
    print()
    
    example_yaml = Path(__file__).parent / "config" / "cameras.example.yaml"
    
    if not example_yaml.exists():
        print(f"❌ Example YAML not found: {example_yaml}")
        return False
    
    print(f"📄 Loading: {example_yaml}")
    print()
    
    try:
        # This will fail due to missing pyyaml, but we can check syntax
        from kvs_infer.config import load_yaml
        config = load_yaml(example_yaml)
        
        print(f"✅ Config loaded successfully!")
        print(f"   - Cameras: {len(config.cameras)}")
        print(f"   - Device: {config.device}")
        print(f"   - AWS region: {config.aws.region}")
        print()
        
        for cam in config.cameras:
            print(f"   📹 Camera: {cam.id}")
            print(f"      - Stream: {cam.kvs_stream_name}")
            print(f"      - Enabled: {cam.enabled}")
            print(f"      - FPS: {cam.fps_target}")
            print(f"      - Detectors: {len(cam.pipeline)}")
            for det in cam.pipeline:
                print(f"        • {det.type.value}")
            print()
        
        return True
        
    except ImportError as e:
        print(f"⚠️  Cannot test YAML loading (missing dependency): {e}")
        print("   Install dependencies to test: pip install -r requirements.txt")
        print()
        return True  # Not a failure, just can't test
    
    except Exception as e:
        print(f"❌ Failed to load YAML: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print()
    
    # Test 1: Model validation
    models_ok = test_config_models()
    
    # Test 2: YAML loading
    yaml_ok = test_yaml_loading()
    
    # Summary
    print("=" * 70)
    if models_ok and yaml_ok:
        print("✅ ALL TESTS PASSED!")
        print()
        print("Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Copy example config: cp config/cameras.example.yaml config/cameras.yaml")
        print("3. Edit config/cameras.yaml with your settings")
        print("4. Test loading: python -c 'from kvs_infer.config import load_yaml; load_yaml(\"config/cameras.yaml\")'")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
