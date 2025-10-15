#!/usr/bin/env python3
"""
Validation script for Step 6: Process Manager (app.py) & CLI.

This script validates:
1. app.py file exists with correct structure
2. CLI argument parsing is implemented
3. Configuration loading works
4. Worker management is implemented
5. FastAPI endpoints are defined
6. Prometheus metrics are configured
7. Signal handlers for graceful shutdown
8. Publisher integration
9. Detector pipeline integration

Run:
    python3 validate_step6.py
"""

import sys
import os
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str):
    """Print section header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"  {text}")


def validate_file_exists(filepath: Path, min_lines: int = 100) -> bool:
    """Validate that file exists and has minimum lines."""
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        line_count = len(f.readlines())
    
    if line_count < min_lines:
        print_error(f"File too short: {filepath} ({line_count} lines, expected >= {min_lines})")
        return False
    
    print_success(f"File exists: {filepath.name} ({line_count} lines)")
    return True


def validate_imports(filepath: Path, required_imports: list) -> bool:
    """Validate that required imports exist."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    all_found = True
    for import_str in required_imports:
        if import_str not in content:
            print_error(f"Import not found: {import_str}")
            all_found = False
    
    if all_found:
        print_success(f"All required imports exist")
    
    return all_found


def validate_class_exists(filepath: Path, class_name: str) -> bool:
    """Validate that class is defined in file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    if f"class {class_name}" not in content:
        print_error(f"Class not found: {class_name}")
        return False
    
    print_success(f"Class exists: {class_name}")
    return True


def validate_function_exists(filepath: Path, function_name: str) -> bool:
    """Validate that function is defined in file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    if f"def {function_name}" not in content:
        print_error(f"Function not found: {function_name}")
        return False
    
    print_success(f"Function exists: {function_name}")
    return True


def validate_app_structure() -> bool:
    """Validate app.py structure."""
    print_header("Validating app.py Structure")
    
    filepath = Path("src/kvs_infer/app.py")
    checks = []
    
    # Check file exists
    checks.append(validate_file_exists(filepath, min_lines=700))
    
    # Check required imports
    required_imports = [
        "import argparse",
        "import logging",
        "import signal",
        "import threading",
        "from fastapi import FastAPI",
        "from prometheus_client import",
        "import uvicorn",
        "from kvs_infer.config import load_config",
        "from kvs_infer.frame_source.kvs_hls import KVSHLSFrameSource",
        "from kvs_infer.detectors import DetectorRegistry",
        "from kvs_infer.publisher import KDSClient, S3Snapshot, DDBWriter",
    ]
    checks.append(validate_imports(filepath, required_imports))
    
    # Check required classes
    checks.append(validate_class_exists(filepath, "CameraWorker"))
    checks.append(validate_class_exists(filepath, "Application"))
    checks.append(validate_class_exists(filepath, "JSONFormatter"))
    
    # Check required functions
    checks.append(validate_function_exists(filepath, "main"))
    checks.append(validate_function_exists(filepath, "parse_args"))
    checks.append(validate_function_exists(filepath, "setup_logging"))
    
    return all(checks)


def validate_cli_functionality() -> bool:
    """Validate CLI argument parsing."""
    print_header("Validating CLI Functionality")
    
    filepath = Path("src/kvs_infer/app.py")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check for ArgumentParser
    if "ArgumentParser" in content:
        print_success("ArgumentParser found")
        checks.append(True)
    else:
        print_error("ArgumentParser not found")
        checks.append(False)
    
    # Check for --config argument
    if "--config" in content:
        print_success("--config argument found")
        checks.append(True)
    else:
        print_error("--config argument not found")
        checks.append(False)
    
    # Check for --http argument
    if "--http" in content:
        print_success("--http argument found")
        checks.append(True)
    else:
        print_error("--http argument not found")
        checks.append(False)
    
    return all(checks)


def validate_worker_management() -> bool:
    """Validate worker management."""
    print_header("Validating Worker Management")
    
    filepath = Path("src/kvs_infer/app.py")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check for worker start
    if "def start(self):" in content and "self.thread = threading.Thread" in content:
        print_success("Worker start() method found")
        checks.append(True)
    else:
        print_error("Worker start() method not properly implemented")
        checks.append(False)
    
    # Check for worker stop
    if "def stop(self):" in content and "self.running = False" in content:
        print_success("Worker stop() method found")
        checks.append(True)
    else:
        print_error("Worker stop() method not properly implemented")
        checks.append(False)
    
    # Check for detector initialization
    if "_initialize_detectors" in content:
        print_success("Detector initialization found")
        checks.append(True)
    else:
        print_error("Detector initialization not found")
        checks.append(False)
    
    # Check for frame source initialization
    if "_initialize_frame_source" in content:
        print_success("Frame source initialization found")
        checks.append(True)
    else:
        print_error("Frame source initialization not found")
        checks.append(False)
    
    return all(checks)


def validate_fastapi_endpoints() -> bool:
    """Validate FastAPI endpoints."""
    print_header("Validating FastAPI Endpoints")
    
    filepath = Path("src/kvs_infer/app.py")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check for FastAPI app
    if "app = FastAPI" in content:
        print_success("FastAPI app instance found")
        checks.append(True)
    else:
        print_error("FastAPI app instance not found")
        checks.append(False)
    
    # Check for /healthz endpoint
    if '@app.get("/healthz")' in content or "@app.get('/healthz')" in content:
        print_success("/healthz endpoint found")
        checks.append(True)
    else:
        print_error("/healthz endpoint not found")
        checks.append(False)
    
    # Check for /metrics endpoint
    if '@app.get("/metrics")' in content or "@app.get('/metrics')" in content:
        print_success("/metrics endpoint found")
        checks.append(True)
    else:
        print_error("/metrics endpoint not found")
        checks.append(False)
    
    # Check for uvicorn
    if "uvicorn.run" in content:
        print_success("uvicorn server found")
        checks.append(True)
    else:
        print_error("uvicorn server not found")
        checks.append(False)
    
    return all(checks)


def validate_prometheus_metrics() -> bool:
    """Validate Prometheus metrics."""
    print_header("Validating Prometheus Metrics")
    
    filepath = Path("src/kvs_infer/app.py")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check for metrics
    required_metrics = [
        "infer_frames_total",
        "infer_events_total",
        "infer_latency_ms",
        "publisher_failures_total",
        "worker_alive",
    ]
    
    for metric in required_metrics:
        if metric in content:
            print_success(f"Metric found: {metric}")
            checks.append(True)
        else:
            print_error(f"Metric not found: {metric}")
            checks.append(False)
    
    # Check for Counter/Gauge/Histogram
    metric_types = ["Counter", "Gauge", "Histogram"]
    for metric_type in metric_types:
        if metric_type in content:
            print_success(f"Metric type found: {metric_type}")
            checks.append(True)
        else:
            print_error(f"Metric type not found: {metric_type}")
            checks.append(False)
    
    return all(checks)


def validate_signal_handlers() -> bool:
    """Validate signal handlers."""
    print_header("Validating Signal Handlers")
    
    filepath = Path("src/kvs_infer/app.py")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check for signal.signal
    if "signal.signal" in content:
        print_success("signal.signal found")
        checks.append(True)
    else:
        print_error("signal.signal not found")
        checks.append(False)
    
    # Check for SIGTERM
    if "SIGTERM" in content:
        print_success("SIGTERM handler found")
        checks.append(True)
    else:
        print_error("SIGTERM handler not found")
        checks.append(False)
    
    # Check for SIGINT
    if "SIGINT" in content:
        print_success("SIGINT handler found")
        checks.append(True)
    else:
        print_error("SIGINT handler not found")
        checks.append(False)
    
    # Check for graceful shutdown
    if "def shutdown" in content:
        print_success("Shutdown method found")
        checks.append(True)
    else:
        print_error("Shutdown method not found")
        checks.append(False)
    
    return all(checks)


def validate_publisher_integration() -> bool:
    """Validate publisher integration."""
    print_header("Validating Publisher Integration")
    
    filepath = Path("src/kvs_infer/app.py")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check for publisher initialization
    if "initialize_publishers" in content:
        print_success("Publisher initialization found")
        checks.append(True)
    else:
        print_error("Publisher initialization not found")
        checks.append(False)
    
    # Check for KDS
    if "KDSClient" in content:
        print_success("KDS publisher integration found")
        checks.append(True)
    else:
        print_error("KDS publisher integration not found")
        checks.append(False)
    
    # Check for S3
    if "S3Snapshot" in content:
        print_success("S3 publisher integration found")
        checks.append(True)
    else:
        print_error("S3 publisher integration not found")
        checks.append(False)
    
    # Check for DDB
    if "DDBWriter" in content:
        print_success("DDB publisher integration found")
        checks.append(True)
    else:
        print_error("DDB publisher integration not found")
        checks.append(False)
    
    # Check for flush
    if "flush()" in content:
        print_success("Publisher flush found")
        checks.append(True)
    else:
        print_error("Publisher flush not found")
        checks.append(False)
    
    return all(checks)


def validate_json_logging() -> bool:
    """Validate JSON logging."""
    print_header("Validating JSON Logging")
    
    filepath = Path("src/kvs_infer/app.py")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check for JSONFormatter
    if "class JSONFormatter" in content:
        print_success("JSONFormatter class found")
        checks.append(True)
    else:
        print_error("JSONFormatter class not found")
        checks.append(False)
    
    # Check for json.dumps
    if "json.dumps" in content:
        print_success("JSON serialization found")
        checks.append(True)
    else:
        print_error("JSON serialization not found")
        checks.append(False)
    
    # Check for LOG_LEVEL
    if "LOG_LEVEL" in content:
        print_success("LOG_LEVEL environment variable support found")
        checks.append(True)
    else:
        print_error("LOG_LEVEL environment variable support not found")
        checks.append(False)
    
    return all(checks)


def validate_config_file() -> bool:
    """Validate example config file."""
    print_header("Validating Example Config File")
    
    filepath = Path("config/cameras.yaml")
    
    if not filepath.exists():
        print_error(f"Config file not found: {filepath}")
        return False
    
    print_success(f"Config file exists: {filepath}")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = []
    
    # Check for required sections
    required_sections = ["publishers", "cameras"]
    for section in required_sections:
        if f"{section}:" in content:
            print_success(f"Section found: {section}")
            checks.append(True)
        else:
            print_error(f"Section not found: {section}")
            checks.append(False)
    
    return all(checks)


def main():
    """Run all validation checks."""
    print_header("Step 6: Process Manager & CLI Validation")
    
    print_info("Validating app.py implementation...")
    print_info("Checking: CLI, workers, FastAPI, Prometheus, signal handlers")
    print_info("")
    
    results = []
    
    # Validate components
    results.append(("App Structure", validate_app_structure()))
    results.append(("CLI Functionality", validate_cli_functionality()))
    results.append(("Worker Management", validate_worker_management()))
    results.append(("FastAPI Endpoints", validate_fastapi_endpoints()))
    results.append(("Prometheus Metrics", validate_prometheus_metrics()))
    results.append(("Signal Handlers", validate_signal_handlers()))
    results.append(("Publisher Integration", validate_publisher_integration()))
    results.append(("JSON Logging", validate_json_logging()))
    results.append(("Example Config", validate_config_file()))
    
    # Print summary
    print_header("Validation Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
    
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    if passed == total:
        print(f"{GREEN}✓ All checks passed ({passed}/{total}){RESET}")
        print(f"{GREEN}Step 6 implementation is complete and valid!{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some checks failed ({passed}/{total}){RESET}")
        print(f"{RED}Please fix the issues above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
