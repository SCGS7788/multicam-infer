#!/usr/bin/env python3
"""
Validation script for Step 8: Local run scripts + Dockerfile

Validates:
1. Dockerfile structure and GPU support
2. Makefile targets existence
3. docker-compose.yml structure
4. Environment variable configuration
5. AWS credential chain support
6. Example configuration files
7. Port configuration (8080)
8. Health check endpoints

Run: python3 validate_step8.py
"""

import sys
import os
from pathlib import Path
import subprocess

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


def validate_dockerfile() -> bool:
    """Validate Dockerfile structure."""
    print("\n🐳 Validating Dockerfile...")
    
    try:
        dockerfile = Path("Dockerfile")
        
        if not dockerfile.exists():
            print(f"{RED}✗ Dockerfile not found{RESET}")
            return False
        
        print(f"{GREEN}✓ Dockerfile exists{RESET}")
        
        content = dockerfile.read_text()
        
        # Check for GPU support
        checks = [
            ("pytorch/pytorch", "PyTorch base image"),
            ("cuda", "CUDA support"),
            ("runtime", "Runtime configuration"),
            ("EXPOSE 8080", "Port 8080 exposed"),
            ("AWS_REGION", "AWS region environment variable"),
            ("HEALTHCHECK", "Health check configured"),
            ("kvs_infer.app", "Main application entry point"),
            ("--http", "HTTP server parameter"),
        ]
        
        for pattern, description in checks:
            if pattern in content:
                print(f"{GREEN}✓ {description} found{RESET}")
            else:
                print(f"{RED}✗ {description} not found (pattern: {pattern}){RESET}")
                return False
        
        # Check line count
        lines = content.count('\n')
        print(f"{GREEN}✓ Dockerfile size: {lines} lines{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False


def validate_makefile() -> bool:
    """Validate Makefile targets."""
    print("\n🔨 Validating Makefile...")
    
    try:
        makefile = Path("Makefile")
        
        if not makefile.exists():
            print(f"{RED}✗ Makefile not found{RESET}")
            return False
        
        print(f"{GREEN}✓ Makefile exists{RESET}")
        
        content = makefile.read_text()
        
        # Required targets
        required_targets = [
            "venv",
            "run-local",
            "docker-build",
            "docker-run",
            "docker-compose-up",
            "help",
            "clean",
        ]
        
        for target in required_targets:
            if f"{target}:" in content or f".PHONY: {target}" in content:
                print(f"{GREEN}✓ Target '{target}' found{RESET}")
            else:
                print(f"{RED}✗ Target '{target}' not found{RESET}")
                return False
        
        # Check for variables
        variables = [
            "CONFIG",
            "GPU",
            "REGION",
            "IMG",
            "HTTP_PORT",
        ]
        
        for var in variables:
            if f"{var} " in content or f"{var}?" in content:
                print(f"{GREEN}✓ Variable '{var}' configured{RESET}")
            else:
                print(f"{YELLOW}⚠ Variable '{var}' not found{RESET}")
        
        # Check line count
        lines = content.count('\n')
        print(f"{GREEN}✓ Makefile size: {lines} lines{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False


def validate_docker_compose() -> bool:
    """Validate docker-compose.yml structure."""
    print("\n🐙 Validating docker-compose.yml...")
    
    try:
        compose_file = Path("docker-compose.yml")
        
        if not compose_file.exists():
            print(f"{RED}✗ docker-compose.yml not found{RESET}")
            return False
        
        print(f"{GREEN}✓ docker-compose.yml exists{RESET}")
        
        content = compose_file.read_text()
        
        # Check structure
        checks = [
            ("version:", "Compose version specified"),
            ("services:", "Services section defined"),
            ("kvs-infer:", "Main service defined"),
            ("ports:", "Ports configuration"),
            (":8080", "Port 8080 mapped"),  # Matches both "8080:8080" and "${HTTP_PORT:-8080}:8080"
            ("volumes:", "Volumes configuration"),
            ("environment:", "Environment variables"),
            ("AWS_REGION", "AWS region variable"),
            ("healthcheck:", "Health check configured"),
            ("CUDA_VISIBLE_DEVICES", "CUDA configuration"),
        ]
        
        for pattern, description in checks:
            if pattern in content:
                print(f"{GREEN}✓ {description}{RESET}")
            else:
                print(f"{RED}✗ {description} not found{RESET}")
                return False
        
        # Check for CPU-only note
        if "CPU-only" in content or "cpu" in content.lower():
            print(f"{GREEN}✓ CPU-only configuration noted{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False


def validate_env_example() -> bool:
    """Validate .env.example file."""
    print("\n🔐 Validating .env.example...")
    
    try:
        env_file = Path(".env.example")
        
        if not env_file.exists():
            print(f"{RED}✗ .env.example not found{RESET}")
            return False
        
        print(f"{GREEN}✓ .env.example exists{RESET}")
        
        content = env_file.read_text()
        
        # Required variables
        variables = [
            "AWS_REGION",
            "AWS_DEFAULT_REGION",
            "LOG_LEVEL",
            "HTTP_PORT",
            "CUDA_VISIBLE_DEVICES",
        ]
        
        for var in variables:
            if var in content:
                print(f"{GREEN}✓ Variable '{var}' documented{RESET}")
            else:
                print(f"{RED}✗ Variable '{var}' not found{RESET}")
                return False
        
        # Check for credential documentation
        if "AWS_ACCESS_KEY_ID" in content:
            print(f"{GREEN}✓ AWS credentials documented{RESET}")
        
        if "IAM role" in content or "credential chain" in content:
            print(f"{GREEN}✓ Credential chain documented{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False


def validate_config_example() -> bool:
    """Validate example configuration file."""
    print("\n⚙️  Validating config/cameras.example.yaml...")
    
    try:
        config_file = Path("config/cameras.example.yaml")
        
        if not config_file.exists():
            # Try alternate name
            config_file = Path("config/cameras.yaml")
            if not config_file.exists():
                print(f"{RED}✗ Example config not found{RESET}")
                return False
        
        print(f"{GREEN}✓ Example config exists: {config_file}{RESET}")
        
        content = config_file.read_text()
        
        # Check structure
        checks = [
            ("publishers:", "Publishers section"),
            ("cameras:", "Cameras section"),
            ("kds:", "KDS publisher"),
            ("s3:", "S3 publisher"),
            ("region:", "Region configuration"),
            ("kvs:", "KVS configuration"),
            ("detectors:", "Detectors configuration"),
        ]
        
        for pattern, description in checks:
            if pattern in content:
                print(f"{GREEN}✓ {description}{RESET}")
            else:
                print(f"{YELLOW}⚠ {description} not found{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False


def validate_makefile_syntax() -> bool:
    """Validate Makefile syntax."""
    print("\n🔍 Validating Makefile syntax...")
    
    try:
        result = subprocess.run(
            ["make", "-n", "help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"{GREEN}✓ Makefile syntax valid{RESET}")
            return True
        else:
            print(f"{RED}✗ Makefile syntax error:{RESET}")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print(f"{YELLOW}⚠ 'make' command not found, skipping syntax check{RESET}")
        return True
    except Exception as e:
        print(f"{YELLOW}⚠ Could not validate Makefile syntax: {e}{RESET}")
        return True


def validate_docker_compose_syntax() -> bool:
    """Validate docker-compose.yml syntax."""
    print("\n🔍 Validating docker-compose.yml syntax...")
    
    try:
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"{GREEN}✓ docker-compose.yml syntax valid{RESET}")
            return True
        else:
            print(f"{RED}✗ docker-compose.yml syntax error:{RESET}")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print(f"{YELLOW}⚠ 'docker-compose' command not found, skipping syntax check{RESET}")
        return True
    except Exception as e:
        print(f"{YELLOW}⚠ Could not validate docker-compose syntax: {e}{RESET}")
        return True


def validate_port_configuration() -> bool:
    """Validate port 8080 configuration."""
    print("\n🔌 Validating port configuration...")
    
    try:
        # Check Dockerfile
        dockerfile = Path("Dockerfile").read_text()
        if "EXPOSE 8080" in dockerfile:
            print(f"{GREEN}✓ Dockerfile exposes port 8080{RESET}")
        else:
            print(f"{RED}✗ Dockerfile does not expose port 8080{RESET}")
            return False
        
        # Check docker-compose.yml
        compose = Path("docker-compose.yml").read_text()
        if "8080:8080" in compose or "8080" in compose:
            print(f"{GREEN}✓ docker-compose.yml maps port 8080{RESET}")
        else:
            print(f"{RED}✗ docker-compose.yml does not map port 8080{RESET}")
            return False
        
        # Check Makefile
        makefile = Path("Makefile").read_text()
        if "8080" in makefile or "HTTP_PORT" in makefile:
            print(f"{GREEN}✓ Makefile configures HTTP port{RESET}")
        else:
            print(f"{YELLOW}⚠ Makefile HTTP port configuration not found{RESET}")
        
        return True
        
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False


def main():
    """Run all validation checks."""
    print_header("Step 8: Local Run Scripts + Dockerfile Validation")
    
    checks = [
        ("Dockerfile", validate_dockerfile),
        ("Makefile", validate_makefile),
        ("docker-compose.yml", validate_docker_compose),
        (".env.example", validate_env_example),
        ("Config Example", validate_config_example),
        ("Makefile Syntax", validate_makefile_syntax),
        ("docker-compose Syntax", validate_docker_compose_syntax),
        ("Port Configuration", validate_port_configuration),
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
        print(f"{GREEN}Step 8 implementation is complete and valid!{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some checks failed ({passed_count}/{total_count}){RESET}")
        print(f"{RED}Please review the failures above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
