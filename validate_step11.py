#!/usr/bin/env python3
"""
Validation script for Step 11: Automated Testing Suite

This script validates that all required test files exist, pytest can discover tests,
and the testing infrastructure is properly configured.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(message: str) -> None:
    """Print success message in green."""
    print(f"{GREEN}✓{RESET} {message}")


def print_error(message: str) -> None:
    """Print error message in red."""
    print(f"{RED}✗{RESET} {message}")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    print(f"{YELLOW}⚠{RESET} {message}")


def print_info(message: str) -> None:
    """Print info message in blue."""
    print(f"{BLUE}ℹ{RESET} {message}")


def print_section(title: str) -> None:
    """Print section header."""
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}\n")


def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if a file exists and print result."""
    if filepath.exists():
        size_kb = filepath.stat().st_size / 1024
        print_success(f"{description}: {filepath} ({size_kb:.1f} KB)")
        return True
    else:
        print_error(f"{description} NOT FOUND: {filepath}")
        return False


def count_lines(filepath: Path) -> int:
    """Count non-empty lines in a file."""
    try:
        with open(filepath, "r") as f:
            return sum(1 for line in f if line.strip())
    except Exception as e:
        print_warning(f"Could not count lines in {filepath}: {e}")
        return 0


def check_test_files() -> Tuple[bool, Dict[str, int]]:
    """Check that all required test files exist."""
    print_section("Step 1: Checking Test Files")
    
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"
    
    required_files = {
        "tests/__init__.py": "Test package initialization",
        "tests/conftest.py": "Pytest configuration and fixtures",
        "tests/test_config.py": "Configuration validation tests",
        "tests/test_roi.py": "ROI geometry tests",
        "tests/test_yolo_common.py": "YOLO detector tests",
        "tests/test_publishers.py": "AWS publisher tests",
    }
    
    all_exist = True
    line_counts = {}
    
    for file_path, description in required_files.items():
        filepath = project_root / file_path
        if check_file_exists(filepath, description):
            lines = count_lines(filepath)
            line_counts[file_path] = lines
            print_info(f"  → {lines} lines of code")
        else:
            all_exist = False
    
    return all_exist, line_counts


def check_config_files() -> bool:
    """Check that pytest configuration files exist."""
    print_section("Step 2: Checking Configuration Files")
    
    project_root = Path(__file__).parent
    
    config_files = {
        "pytest.ini": "Pytest configuration",
        "requirements-test.txt": "Test dependencies",
        "tests/README.md": "Test documentation",
    }
    
    all_exist = True
    for file_path, description in config_files.items():
        filepath = project_root / file_path
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist


def check_pytest_markers() -> bool:
    """Check that pytest markers are properly configured."""
    print_section("Step 3: Checking Pytest Markers")
    
    project_root = Path(__file__).parent
    pytest_ini = project_root / "pytest.ini"
    
    if not pytest_ini.exists():
        print_error("pytest.ini not found")
        return False
    
    required_markers = ["unit", "integration", "slow", "gpu", "aws"]
    found_markers = []
    
    try:
        with open(pytest_ini, "r") as f:
            content = f.read()
            for marker in required_markers:
                if f"{marker}:" in content or f"{marker} :" in content:
                    found_markers.append(marker)
                    print_success(f"Marker '{marker}' configured")
                else:
                    print_error(f"Marker '{marker}' NOT configured")
        
        return len(found_markers) == len(required_markers)
    except Exception as e:
        print_error(f"Error reading pytest.ini: {e}")
        return False


def check_test_dependencies() -> bool:
    """Check that test dependencies are specified."""
    print_section("Step 4: Checking Test Dependencies")
    
    project_root = Path(__file__).parent
    req_file = project_root / "requirements-test.txt"
    
    if not req_file.exists():
        print_error("requirements-test.txt not found")
        return False
    
    required_deps = [
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "moto",
        "black",
        "flake8",
        "mypy",
    ]
    
    found_deps = []
    
    try:
        with open(req_file, "r") as f:
            content = f.read().lower()
            for dep in required_deps:
                if dep.lower() in content:
                    found_deps.append(dep)
                    print_success(f"Dependency '{dep}' specified")
                else:
                    print_error(f"Dependency '{dep}' NOT specified")
        
        return len(found_deps) == len(required_deps)
    except Exception as e:
        print_error(f"Error reading requirements-test.txt: {e}")
        return False


def check_github_workflow() -> bool:
    """Check that GitHub Actions workflow exists."""
    print_section("Step 5: Checking GitHub Actions Workflow")
    
    project_root = Path(__file__).parent
    workflow_file = project_root / ".github" / "workflows" / "test.yml"
    
    if not workflow_file.exists():
        print_error("GitHub Actions workflow test.yml not found")
        return False
    
    print_success(f"GitHub Actions workflow exists: {workflow_file}")
    
    # Check for key workflow components
    try:
        with open(workflow_file, "r") as f:
            content = f.read()
            
            checks = {
                "pull_request trigger": "pull_request" in content,
                "pytest execution": "pytest" in content,
                "coverage reporting": "cov" in content or "coverage" in content,
                "Python setup": "setup-python" in content,
                "dependency installation": "pip install" in content,
            }
            
            for check_name, passed in checks.items():
                if passed:
                    print_success(f"Workflow has {check_name}")
                else:
                    print_warning(f"Workflow may be missing {check_name}")
            
            return all(checks.values())
    except Exception as e:
        print_error(f"Error reading workflow file: {e}")
        return False


def try_import_pytest() -> bool:
    """Try to import pytest to check if it's installed."""
    print_section("Step 6: Checking Pytest Installation")
    
    try:
        import pytest
        version = pytest.__version__
        print_success(f"pytest is installed (version {version})")
        return True
    except ImportError:
        print_error("pytest is NOT installed")
        print_info("  → Install with: pip install -r requirements-test.txt")
        return False


def discover_tests() -> Tuple[bool, int]:
    """Discover pytest tests without running them."""
    print_section("Step 7: Discovering Tests")
    
    try:
        import pytest
        
        project_root = Path(__file__).parent
        tests_dir = project_root / "tests"
        
        # Collect tests without running
        result = pytest.main([
            str(tests_dir),
            "--collect-only",
            "-q",
            "--tb=no"
        ])
        
        # Note: We can't easily get the count from pytest.main
        # So we'll just check if it succeeded
        if result == 0:
            print_success("Pytest can discover tests successfully")
            print_info("  → Run 'pytest --collect-only' to see all tests")
            return True, 0
        else:
            print_error("Pytest failed to discover tests")
            return False, 0
    except ImportError:
        print_warning("Pytest not installed, skipping test discovery")
        return False, 0
    except Exception as e:
        print_error(f"Error during test discovery: {e}")
        return False, 0


def check_example_config() -> bool:
    """Check that cameras.example.yaml exists for tests."""
    print_section("Step 8: Checking Example Configuration")
    
    project_root = Path(__file__).parent
    example_config = project_root / "cameras.example.yaml"
    
    if example_config.exists():
        print_success(f"Example configuration exists: {example_config}")
        return True
    else:
        print_error("cameras.example.yaml not found (required by test_config.py)")
        return False


def generate_summary(results: Dict[str, bool], line_counts: Dict[str, int]) -> None:
    """Generate validation summary."""
    print_section("Validation Summary")
    
    total_checks = len(results)
    passed_checks = sum(1 for passed in results.values() if passed)
    
    # Calculate total lines of test code
    total_lines = sum(line_counts.values())
    
    print(f"Total checks: {total_checks}")
    print(f"Passed: {GREEN}{passed_checks}{RESET}")
    print(f"Failed: {RED}{total_checks - passed_checks}{RESET}")
    print(f"\nTotal lines of test code: {BLUE}{total_lines}{RESET}")
    
    print("\nDetailed Results:")
    for check_name, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {status} - {check_name}")
    
    if passed_checks == total_checks:
        print(f"\n{GREEN}{'=' * 70}{RESET}")
        print(f"{GREEN}✓ All validation checks passed!{RESET}")
        print(f"{GREEN}{'=' * 70}{RESET}\n")
        print_info("Next steps:")
        print_info("  1. Install test dependencies: pip install -r requirements-test.txt")
        print_info("  2. Run tests: pytest")
        print_info("  3. Generate coverage: pytest --cov=src/kvs_infer --cov-report=html")
        print_info("  4. View coverage: open htmlcov/index.html")
        return True
    else:
        print(f"\n{RED}{'=' * 70}{RESET}")
        print(f"{RED}✗ Some validation checks failed{RESET}")
        print(f"{RED}{'=' * 70}{RESET}\n")
        print_warning("Please fix the failed checks before proceeding.")
        return False


def main() -> int:
    """Main validation function."""
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}Step 11 Validation: Automated Testing Suite{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}\n")
    
    results = {}
    line_counts = {}
    
    # Run all validation checks
    results["Test Files"], line_counts = check_test_files()
    results["Config Files"] = check_config_files()
    results["Pytest Markers"] = check_pytest_markers()
    results["Test Dependencies"] = check_test_dependencies()
    results["GitHub Workflow"] = check_github_workflow()
    results["Example Config"] = check_example_config()
    
    # Optional checks (won't fail validation)
    pytest_installed = try_import_pytest()
    if pytest_installed:
        test_discovery, test_count = discover_tests()
        results["Test Discovery"] = test_discovery
    
    # Generate summary
    all_passed = generate_summary(results, line_counts)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
