#!/usr/bin/env python3
"""
Validation script for Step 9: ECS (EC2 GPU) Deployment

Validates:
1. ECS task definition structure
2. ECS service definition structure
3. IAM task role policy
4. IAM execution role policy
5. README-ECS.md completeness
6. Deployment scripts
7. Configuration files
8. JSON syntax validation

Run: python3 validate_step9.py
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

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


def validate_json_file(filepath: Path, required_keys: List[str] = None) -> bool:
    """Validate JSON file syntax and structure."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        if required_keys:
            for key in required_keys:
                if key not in data:
                    print(f"{RED}✗ Missing required key: {key}{RESET}")
                    return False
        
        return True
    except json.JSONDecodeError as e:
        print(f"{RED}✗ JSON syntax error: {e}{RESET}")
        return False
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False


def validate_ecs_task_definition() -> bool:
    """Validate ECS task definition."""
    print("\n🐳 Validating ECS task definition...")
    
    task_def_file = Path("deployment/ecs/ecs-task-def.json")
    
    if not task_def_file.exists():
        print(f"{RED}✗ Task definition not found: {task_def_file}{RESET}")
        return False
    
    print(f"{GREEN}✓ Task definition file exists{RESET}")
    
    # Validate JSON syntax
    if not validate_json_file(task_def_file, ["family", "containerDefinitions"]):
        return False
    
    print(f"{GREEN}✓ JSON syntax valid{RESET}")
    
    # Load and validate content
    with open(task_def_file, 'r') as f:
        task_def = json.load(f)
    
    # Check required fields
    checks = [
        ("family" in task_def, "Task family defined"),
        ("networkMode" in task_def and task_def["networkMode"] == "awsvpc", "Network mode is awsvpc"),
        ("requiresCompatibilities" in task_def, "Compatibility requirements defined"),
        ("containerDefinitions" in task_def, "Container definitions present"),
        (len(task_def.get("containerDefinitions", [])) > 0, "At least one container defined"),
    ]
    
    for condition, description in checks:
        if condition:
            print(f"{GREEN}✓ {description}{RESET}")
        else:
            print(f"{RED}✗ {description}{RESET}")
            return False
    
    # Check container configuration
    container = task_def["containerDefinitions"][0]
    
    container_checks = [
        ("name" in container, "Container name defined"),
        ("image" in container, "Container image defined"),
        ("resourceRequirements" in container, "Resource requirements defined"),
        ("logConfiguration" in container, "Log configuration defined"),
        ("healthCheck" in container, "Health check configured"),
        ("portMappings" in container, "Port mappings defined"),
    ]
    
    for condition, description in container_checks:
        if condition:
            print(f"{GREEN}✓ {description}{RESET}")
        else:
            print(f"{RED}✗ {description}{RESET}")
            return False
    
    # Check GPU configuration
    resource_reqs = container.get("resourceRequirements", [])
    has_gpu = any(req.get("type") == "GPU" for req in resource_reqs)
    
    if has_gpu:
        print(f"{GREEN}✓ GPU resource requirement configured{RESET}")
    else:
        print(f"{RED}✗ GPU resource requirement not found{RESET}")
        return False
    
    # Check log configuration
    log_config = container.get("logConfiguration", {})
    if log_config.get("logDriver") == "awslogs":
        print(f"{GREEN}✓ CloudWatch Logs configured (awslogs){RESET}")
    else:
        print(f"{RED}✗ CloudWatch Logs not properly configured{RESET}")
        return False
    
    # Check environment variables
    env_vars = {env["name"]: env["value"] for env in container.get("environment", [])}
    
    required_env_vars = ["AWS_REGION", "LOG_LEVEL", "HTTP_PORT"]
    for var in required_env_vars:
        if var in env_vars:
            print(f"{GREEN}✓ Environment variable '{var}' defined{RESET}")
        else:
            print(f"{YELLOW}⚠ Environment variable '{var}' not found (may use placeholder){RESET}")
    
    # Check port 8080
    ports = [pm.get("containerPort") for pm in container.get("portMappings", [])]
    if 8080 in ports:
        print(f"{GREEN}✓ Port 8080 exposed{RESET}")
    else:
        print(f"{RED}✗ Port 8080 not exposed{RESET}")
        return False
    
    return True


def validate_ecs_service_definition() -> bool:
    """Validate ECS service definition."""
    print("\n📦 Validating ECS service definition...")
    
    service_def_file = Path("deployment/ecs/ecs-service.json")
    
    if not service_def_file.exists():
        print(f"{RED}✗ Service definition not found: {service_def_file}{RESET}")
        return False
    
    print(f"{GREEN}✓ Service definition file exists{RESET}")
    
    # Validate JSON syntax
    if not validate_json_file(service_def_file, ["serviceName", "cluster", "taskDefinition"]):
        return False
    
    print(f"{GREEN}✓ JSON syntax valid{RESET}")
    
    # Load and validate content
    with open(service_def_file, 'r') as f:
        service_def = json.load(f)
    
    # Check required fields
    checks = [
        ("serviceName" in service_def, "Service name defined"),
        ("cluster" in service_def, "Cluster name defined"),
        ("taskDefinition" in service_def, "Task definition reference present"),
        ("desiredCount" in service_def, "Desired count defined"),
        ("launchType" in service_def and service_def["launchType"] == "EC2", "Launch type is EC2"),
        ("networkConfiguration" in service_def, "Network configuration present"),
    ]
    
    for condition, description in checks:
        if condition:
            print(f"{GREEN}✓ {description}{RESET}")
        else:
            print(f"{RED}✗ {description}{RESET}")
            return False
    
    # Check network configuration
    net_config = service_def.get("networkConfiguration", {}).get("awsvpcConfiguration", {})
    
    net_checks = [
        ("subnets" in net_config, "Subnets defined"),
        ("securityGroups" in net_config, "Security groups defined"),
        ("assignPublicIp" in net_config, "Public IP assignment configured"),
    ]
    
    for condition, description in net_checks:
        if condition:
            print(f"{GREEN}✓ {description}{RESET}")
        else:
            print(f"{RED}✗ {description}{RESET}")
            return False
    
    # Check that public IP is disabled (private subnets)
    if net_config.get("assignPublicIp") == "DISABLED":
        print(f"{GREEN}✓ Public IP assignment disabled (private subnets){RESET}")
    else:
        print(f"{YELLOW}⚠ Public IP assignment not disabled{RESET}")
    
    # Check deployment configuration
    if "deploymentConfiguration" in service_def:
        print(f"{GREEN}✓ Deployment configuration present{RESET}")
        
        deploy_config = service_def["deploymentConfiguration"]
        if "deploymentCircuitBreaker" in deploy_config:
            print(f"{GREEN}✓ Deployment circuit breaker configured{RESET}")
    
    return True


def validate_iam_task_role() -> bool:
    """Validate IAM task role policy."""
    print("\n🔐 Validating IAM task role policy...")
    
    task_role_file = Path("deployment/ecs/iam-task-role.json")
    
    if not task_role_file.exists():
        print(f"{RED}✗ Task role policy not found: {task_role_file}{RESET}")
        return False
    
    print(f"{GREEN}✓ Task role policy file exists{RESET}")
    
    # Validate JSON syntax
    if not validate_json_file(task_role_file, ["Version", "Statement"]):
        return False
    
    print(f"{GREEN}✓ JSON syntax valid{RESET}")
    
    # Load and validate content
    with open(task_role_file, 'r') as f:
        policy = json.load(f)
    
    # Check policy structure
    if "Statement" not in policy or not isinstance(policy["Statement"], list):
        print(f"{RED}✗ Invalid policy structure{RESET}")
        return False
    
    print(f"{GREEN}✓ Policy structure valid{RESET}")
    
    # Check for required service permissions
    statements = policy["Statement"]
    
    # Extract actions from all statements
    all_actions = []
    for stmt in statements:
        actions = stmt.get("Action", [])
        if isinstance(actions, str):
            all_actions.append(actions)
        else:
            all_actions.extend(actions)
    
    required_services = {
        "kinesisvideo": ["kinesisvideo:DescribeStream", "kinesisvideo:GetDataEndpoint", "kinesisvideo:GetMedia"],
        "kinesis": ["kinesis:DescribeStream", "kinesis:PutRecord"],
        "s3": ["s3:PutObject"],
        "dynamodb": ["dynamodb:PutItem"],
        "cloudwatch": ["cloudwatch:PutMetricData"],
    }
    
    for service, required_actions in required_services.items():
        service_actions = [a for a in all_actions if a.startswith(f"{service}:")]
        
        if service_actions:
            print(f"{GREEN}✓ {service.upper()} permissions defined{RESET}")
            
            # Check for specific actions
            for action in required_actions:
                if action in all_actions or any(action.split(':')[1] in a for a in service_actions):
                    print(f"  {GREEN}✓ {action}{RESET}")
                else:
                    print(f"  {YELLOW}⚠ {action} not explicitly found{RESET}")
        else:
            print(f"{YELLOW}⚠ No {service.upper()} permissions found{RESET}")
    
    # Check for resource restrictions
    has_resource_restrictions = any(
        "Resource" in stmt and stmt["Resource"] != "*"
        for stmt in statements
    )
    
    if has_resource_restrictions:
        print(f"{GREEN}✓ Resource-level restrictions present (least-privilege){RESET}")
    else:
        print(f"{YELLOW}⚠ No resource-level restrictions found{RESET}")
    
    # Check for condition restrictions
    has_conditions = any("Condition" in stmt for stmt in statements)
    
    if has_conditions:
        print(f"{GREEN}✓ Conditional access controls present{RESET}")
    else:
        print(f"{YELLOW}⚠ No conditional access controls found{RESET}")
    
    return True


def validate_iam_execution_role() -> bool:
    """Validate IAM execution role policy."""
    print("\n🔑 Validating IAM execution role policy...")
    
    exec_role_file = Path("deployment/ecs/iam-execution-role.json")
    
    if not exec_role_file.exists():
        print(f"{RED}✗ Execution role policy not found: {exec_role_file}{RESET}")
        return False
    
    print(f"{GREEN}✓ Execution role policy file exists{RESET}")
    
    # Validate JSON syntax
    if not validate_json_file(exec_role_file, ["Version", "Statement"]):
        return False
    
    print(f"{GREEN}✓ JSON syntax valid{RESET}")
    
    # Load and validate content
    with open(exec_role_file, 'r') as f:
        policy = json.load(f)
    
    # Extract actions
    statements = policy["Statement"]
    all_actions = []
    for stmt in statements:
        actions = stmt.get("Action", [])
        if isinstance(actions, str):
            all_actions.append(actions)
        else:
            all_actions.extend(actions)
    
    # Check required actions
    required_permissions = [
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
    ]
    
    for action in required_permissions:
        if action in all_actions or any(action.split(':')[1] in a for a in all_actions):
            print(f"{GREEN}✓ {action}{RESET}")
        else:
            print(f"{RED}✗ {action} not found{RESET}")
            return False
    
    return True


def validate_readme() -> bool:
    """Validate README-ECS.md completeness."""
    print("\n📖 Validating README-ECS.md...")
    
    readme_file = Path("deployment/ecs/README-ECS.md")
    
    if not readme_file.exists():
        print(f"{RED}✗ README-ECS.md not found{RESET}")
        return False
    
    print(f"{GREEN}✓ README-ECS.md exists{RESET}")
    
    content = readme_file.read_text()
    
    # Check required sections
    required_sections = [
        "Prerequisites",
        "Architecture",
        "Step-by-Step",
        "ECR",
        "IAM",
        "Task Definition",
        "Service",
        "Container Insights",
        "VPC Endpoints",
        "KVS",
        "Troubleshooting",
    ]
    
    for section in required_sections:
        if section.lower() in content.lower():
            print(f"{GREEN}✓ Section '{section}' found{RESET}")
        else:
            print(f"{YELLOW}⚠ Section '{section}' not found{RESET}")
    
    # Check for important notes
    important_notes = [
        "NAT Gateway",
        "g4dn",
        "GPU",
        "CUDA",
        "VPC endpoint",
    ]
    
    for note in important_notes:
        if note in content:
            print(f"{GREEN}✓ Mentions '{note}'{RESET}")
        else:
            print(f"{YELLOW}⚠ '{note}' not mentioned{RESET}")
    
    # Check line count
    lines = content.count('\n')
    if lines > 500:
        print(f"{GREEN}✓ README is comprehensive ({lines} lines){RESET}")
    else:
        print(f"{YELLOW}⚠ README may be incomplete ({lines} lines){RESET}")
    
    return True


def validate_deployment_script() -> bool:
    """Validate deployment script."""
    print("\n🚀 Validating deployment script...")
    
    deploy_script = Path("deployment/ecs/deploy.sh")
    
    if not deploy_script.exists():
        print(f"{RED}✗ deploy.sh not found{RESET}")
        return False
    
    print(f"{GREEN}✓ deploy.sh exists{RESET}")
    
    # Check if executable
    if os.access(deploy_script, os.X_OK):
        print(f"{GREEN}✓ Script is executable{RESET}")
    else:
        print(f"{YELLOW}⚠ Script is not executable (run: chmod +x deploy.sh){RESET}")
    
    content = deploy_script.read_text()
    
    # Check for required functions
    required_functions = [
        "create_ecr_repo",
        "build_and_push_image",
        "create_iam_roles",
        "create_ecs_cluster",
        "register_task_definition",
        "create_security_group",
        "create_ecs_service",
    ]
    
    for func in required_functions:
        if func in content:
            print(f"{GREEN}✓ Function '{func}' defined{RESET}")
        else:
            print(f"{RED}✗ Function '{func}' not found{RESET}")
            return False
    
    # Check for error handling
    if "set -e" in content:
        print(f"{GREEN}✓ Error handling enabled (set -e){RESET}")
    else:
        print(f"{YELLOW}⚠ Error handling not enabled{RESET}")
    
    return True


def validate_env_example() -> bool:
    """Validate .env.example file."""
    print("\n⚙️  Validating .env.example...")
    
    env_file = Path("deployment/ecs/.env.example")
    
    if not env_file.exists():
        print(f"{RED}✗ .env.example not found{RESET}")
        return False
    
    print(f"{GREEN}✓ .env.example exists{RESET}")
    
    content = env_file.read_text()
    
    # Check required variables
    required_vars = [
        "AWS_REGION",
        "AWS_ACCOUNT_ID",
        "ECR_REPO_NAME",
        "ECS_CLUSTER_NAME",
        "VPC_ID",
        "PRIVATE_SUBNET_1",
        "PRIVATE_SUBNET_2",
        "KVS_STREAM_PREFIX",
        "KDS_STREAM_NAME",
        "S3_BUCKET_NAME",
        "S3_PREFIX",
    ]
    
    for var in required_vars:
        if var in content:
            print(f"{GREEN}✓ Variable '{var}' documented{RESET}")
        else:
            print(f"{RED}✗ Variable '{var}' not found{RESET}")
            return False
    
    return True


def main():
    """Run all validation checks."""
    print_header("Step 9: ECS (EC2 GPU) Deployment Validation")
    
    checks = [
        ("ECS Task Definition", validate_ecs_task_definition),
        ("ECS Service Definition", validate_ecs_service_definition),
        ("IAM Task Role Policy", validate_iam_task_role),
        ("IAM Execution Role Policy", validate_iam_execution_role),
        ("README-ECS.md", validate_readme),
        ("Deployment Script", validate_deployment_script),
        (".env.example", validate_env_example),
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
        print(f"{GREEN}Step 9 implementation is complete and valid!{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some checks failed ({passed_count}/{total_count}){RESET}")
        print(f"{RED}Please review the failures above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
