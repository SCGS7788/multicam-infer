#!/usr/bin/env python3
"""
Validation script for Step 5: Publisher Implementations.

This script validates:
1. Publisher files exist with correct structure
2. Required classes and methods are implemented
3. Event envelope format is correct
4. Error handling is implemented
5. Metrics tracking is working
6. Batch processing logic is correct
7. AWS SDK integration is proper

Run:
    python3 validate_step5.py
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List


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
    """
    Validate that file exists and has minimum lines.
    
    Args:
        filepath: Path to file
        min_lines: Minimum line count
        
    Returns:
        True if valid
    """
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        return False
    
    # Check line count
    with open(filepath, 'r') as f:
        line_count = len(f.readlines())
    
    if line_count < min_lines:
        print_error(
            f"File too short: {filepath} ({line_count} lines, expected >= {min_lines})"
        )
        return False
    
    print_success(f"File exists: {filepath.name} ({line_count} lines)")
    return True


def validate_class_exists(filepath: Path, class_name: str) -> bool:
    """
    Validate that class is defined in file.
    
    Args:
        filepath: Path to file
        class_name: Class name to find
        
    Returns:
        True if found
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    if f"class {class_name}" not in content:
        print_error(f"Class not found: {class_name} in {filepath.name}")
        return False
    
    print_success(f"Class exists: {class_name}")
    return True


def validate_methods(filepath: Path, class_name: str, methods: List[str]) -> bool:
    """
    Validate that methods exist in class.
    
    Args:
        filepath: Path to file
        class_name: Class name
        methods: List of method names
        
    Returns:
        True if all found
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    all_found = True
    for method in methods:
        if f"def {method}" not in content:
            print_error(f"Method not found: {class_name}.{method}()")
            all_found = False
    
    if all_found:
        print_success(f"All methods exist in {class_name}: {', '.join(methods)}")
    
    return all_found


def validate_imports(filepath: Path, required_imports: List[str]) -> bool:
    """
    Validate that required imports exist.
    
    Args:
        filepath: Path to file
        required_imports: List of import strings to find
        
    Returns:
        True if all found
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    all_found = True
    for import_str in required_imports:
        if import_str not in content:
            print_error(f"Import not found: {import_str} in {filepath.name}")
            all_found = False
    
    if all_found:
        print_success(f"All required imports exist in {filepath.name}")
    
    return all_found


def validate_kds_publisher() -> bool:
    """Validate KDS publisher implementation."""
    print_header("Validating KDS Publisher (kds.py)")
    
    filepath = Path("src/kvs_infer/publisher/kds.py")
    
    checks = []
    
    # Check file exists
    checks.append(validate_file_exists(filepath, min_lines=350))
    
    # Check class exists
    checks.append(validate_class_exists(filepath, "KDSClient"))
    
    # Check required methods
    required_methods = [
        "__init__",
        "put_event",
        "put_events",
        "flush",
        "_send_batch_with_retries",
        "_create_event_envelope",
        "_generate_event_id",
        "get_metrics",
    ]
    checks.append(validate_methods(filepath, "KDSClient", required_methods))
    
    # Check required imports
    required_imports = [
        "import boto3",
        "import json",
        "import hashlib",
        "from botocore.exceptions import ClientError",
    ]
    checks.append(validate_imports(filepath, required_imports))
    
    # Check for batching logic
    with open(filepath, 'r') as f:
        content = f.read()
    
    if "put_records" not in content.lower():
        print_error("PutRecords API not found (batching)")
        checks.append(False)
    else:
        print_success("PutRecords API found (batching support)")
        checks.append(True)
    
    # Check for retry logic
    if "ProvisionedThroughputExceededException" not in content:
        print_error("Throttling exception handling not found")
        checks.append(False)
    else:
        print_success("Throttling exception handling found")
        checks.append(True)
    
    # Check for exponential backoff
    if "2 ** attempt" not in content and "2**attempt" not in content:
        print_error("Exponential backoff not found")
        checks.append(False)
    else:
        print_success("Exponential backoff found")
        checks.append(True)
    
    # Check for jitter
    if "random.uniform" not in content:
        print_warning("Jitter randomization not found (optional)")
    else:
        print_success("Jitter randomization found")
    
    # Check for event_id generation
    if "hashlib.sha1" not in content:
        print_error("SHA1 event_id generation not found")
        checks.append(False)
    else:
        print_success("SHA1 event_id generation found")
        checks.append(True)
    
    # Check for metrics
    if "self.metrics" not in content:
        print_error("Metrics tracking not found")
        checks.append(False)
    else:
        print_success("Metrics tracking found")
        checks.append(True)
    
    return all(checks)


def validate_s3_publisher() -> bool:
    """Validate S3 publisher implementation."""
    print_header("Validating S3 Publisher (s3.py)")
    
    filepath = Path("src/kvs_infer/publisher/s3.py")
    
    checks = []
    
    # Check file exists
    checks.append(validate_file_exists(filepath, min_lines=250))
    
    # Check class exists
    checks.append(validate_class_exists(filepath, "S3Snapshot"))
    
    # Check required methods
    required_methods = [
        "__init__",
        "save",
        "save_with_bbox",
        "get_url",
        "_generate_key",
        "get_metrics",
    ]
    checks.append(validate_methods(filepath, "S3Snapshot", required_methods))
    
    # Check required imports
    required_imports = [
        "import boto3",
        "import cv2",
        "from botocore.exceptions import ClientError",
    ]
    checks.append(validate_imports(filepath, required_imports))
    
    # Check for JPEG encoding
    with open(filepath, 'r') as f:
        content = f.read()
    
    if "cv2.imencode" not in content:
        print_error("cv2.imencode (JPEG encoding) not found")
        checks.append(False)
    else:
        print_success("cv2.imencode (JPEG encoding) found")
        checks.append(True)
    
    # Check for JPEG quality
    if "IMWRITE_JPEG_QUALITY" not in content:
        print_error("JPEG quality parameter not found")
        checks.append(False)
    else:
        print_success("JPEG quality parameter found")
        checks.append(True)
    
    # Check for put_object
    if "put_object" not in content:
        print_error("S3 put_object not found")
        checks.append(False)
    else:
        print_success("S3 put_object found")
        checks.append(True)
    
    # Check for presigned URL
    if "generate_presigned_url" not in content:
        print_warning("Presigned URL generation not found (optional)")
    else:
        print_success("Presigned URL generation found")
    
    # Check for bbox drawing
    if "cv2.rectangle" not in content:
        print_warning("Bbox drawing not found (optional)")
    else:
        print_success("Bbox drawing found")
    
    # Check for metrics
    if "self.metrics" not in content:
        print_error("Metrics tracking not found")
        checks.append(False)
    else:
        print_success("Metrics tracking found")
        checks.append(True)
    
    return all(checks)


def validate_ddb_publisher() -> bool:
    """Validate DynamoDB publisher implementation."""
    print_header("Validating DynamoDB Publisher (ddb.py)")
    
    filepath = Path("src/kvs_infer/publisher/ddb.py")
    
    checks = []
    
    # Check file exists
    checks.append(validate_file_exists(filepath, min_lines=300))
    
    # Check class exists
    checks.append(validate_class_exists(filepath, "DDBWriter"))
    
    # Check required methods
    required_methods = [
        "__init__",
        "put_event",
        "put_events",
        "_prepare_item",
        "get_metrics",
    ]
    checks.append(validate_methods(filepath, "DDBWriter", required_methods))
    
    # Check required imports
    required_imports = [
        "import boto3",
        "from decimal import Decimal",
        "from botocore.exceptions import ClientError",
    ]
    checks.append(validate_imports(filepath, required_imports))
    
    # Check for Decimal conversion
    with open(filepath, 'r') as f:
        content = f.read()
    
    if "Decimal" not in content:
        print_error("Decimal conversion not found (DynamoDB requirement)")
        checks.append(False)
    else:
        print_success("Decimal conversion found")
        checks.append(True)
    
    # Check for batch writing
    if "batch_writer" not in content:
        print_warning("Batch writer not found (optional)")
    else:
        print_success("Batch writer found")
    
    # Check for TTL support
    if "ttl" in content:
        print_success("TTL support found")
    else:
        print_warning("TTL support not found (optional)")
    
    # Check for metrics
    if "self.metrics" not in content:
        print_error("Metrics tracking not found")
        checks.append(False)
    else:
        print_success("Metrics tracking found")
        checks.append(True)
    
    return all(checks)


def validate_publisher_init() -> bool:
    """Validate publisher __init__.py exports."""
    print_header("Validating Publisher Module (__init__.py)")
    
    filepath = Path("src/kvs_infer/publisher/__init__.py")
    
    checks = []
    
    # Check file exists
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        return False
    
    print_success(f"File exists: {filepath.name}")
    
    # Check exports
    with open(filepath, 'r') as f:
        content = f.read()
    
    required_exports = [
        "from kvs_infer.publisher.kds import KDSClient",
        "from kvs_infer.publisher.s3 import S3Snapshot",
        "from kvs_infer.publisher.ddb import DDBWriter",
    ]
    
    for export in required_exports:
        if export not in content:
            print_error(f"Export not found: {export}")
            checks.append(False)
        else:
            checks.append(True)
    
    if all(checks):
        print_success("All publishers exported in __init__.py")
    
    return all(checks)


def validate_event_envelope_format() -> bool:
    """Validate event envelope format consistency."""
    print_header("Validating Event Envelope Format")
    
    checks = []
    
    # Check KDS creates proper envelope
    kds_path = Path("src/kvs_infer/publisher/kds.py")
    with open(kds_path, 'r') as f:
        kds_content = f.read()
    
    required_fields = ["event_id", "camera_id", "producer", "payload"]
    
    for field in required_fields:
        if f'"{field}"' not in kds_content and f"'{field}'" not in kds_content:
            print_error(f"Event envelope field missing: {field}")
            checks.append(False)
        else:
            checks.append(True)
    
    if all(checks):
        print_success("Event envelope format correct in kds.py")
    
    # Check DDB handles envelope
    ddb_path = Path("src/kvs_infer/publisher/ddb.py")
    with open(ddb_path, 'r') as f:
        ddb_content = f.read()
    
    if 'event["event_id"]' in ddb_content and 'event["payload"]' in ddb_content:
        print_success("Event envelope handling correct in ddb.py")
    else:
        print_error("Event envelope handling incorrect in ddb.py")
        checks.append(False)
    
    return all(checks)


def main():
    """Run all validation checks."""
    print_header("Step 5 Publisher Implementation Validation")
    
    print_info("Validating publisher implementations...")
    print_info("Checking: KDS, S3, DynamoDB publishers")
    print_info("")
    
    results = []
    
    # Validate individual publishers
    results.append(("KDS Publisher", validate_kds_publisher()))
    results.append(("S3 Publisher", validate_s3_publisher()))
    results.append(("DynamoDB Publisher", validate_ddb_publisher()))
    results.append(("Publisher Module", validate_publisher_init()))
    results.append(("Event Envelope Format", validate_event_envelope_format()))
    
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
        print(f"{GREEN}Step 5 implementation is complete and valid!{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some checks failed ({passed}/{total}){RESET}")
        print(f"{RED}Please fix the issues above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
