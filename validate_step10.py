#!/usr/bin/env python3
"""
Validation script for Step 10: GitHub Actions CI/CD workflows.

This script validates:
1. Workflow YAML syntax
2. Required secrets configuration
3. Job dependencies
4. Build configuration
5. Deployment configuration
6. Documentation completeness
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple


def validate_yaml_syntax(file_path: Path) -> Tuple[bool, str, dict]:
    """Validate YAML syntax and structure."""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return True, "Valid YAML syntax", data
    except yaml.YAMLError as e:
        return False, f"YAML syntax error: {e}", {}
    except Exception as e:
        return False, f"Error reading file: {e}", {}


def validate_deploy_workflow(workflow_path: Path) -> List[str]:
    """Validate the main deploy.yml workflow."""
    issues = []
    
    if not workflow_path.exists():
        issues.append(f"❌ Workflow file not found: {workflow_path}")
        return issues
    
    valid, msg, workflow = validate_yaml_syntax(workflow_path)
    if not valid:
        issues.append(f"❌ {msg}")
        return issues
    
    # Check workflow name
    if 'name' not in workflow:
        issues.append("❌ Workflow missing 'name' field")
    
    # Check triggers (handle YAML parsing 'on' as True)
    triggers = workflow.get('on') or workflow.get(True)
    if not triggers:
        issues.append("❌ Workflow missing 'on' triggers")
    else:
        if 'push' not in triggers:
            issues.append("⚠️  Missing 'push' trigger (recommended)")
        if 'workflow_dispatch' not in triggers:
            issues.append("⚠️  Missing 'workflow_dispatch' trigger (recommended for manual runs)")
        
        # Validate push trigger
        if 'push' in triggers and isinstance(triggers['push'], dict):
            if 'branches' in triggers['push']:
                if 'main' not in triggers['push']['branches']:
                    issues.append("⚠️  'main' branch not in push triggers")
            if 'tags' in triggers['push']:
                print("✅ Tag-based releases configured")
    
    # Check permissions (required for OIDC)
    if 'permissions' not in workflow:
        issues.append("❌ Missing 'permissions' (required for OIDC)")
    else:
        perms = workflow['permissions']
        if perms.get('id-token') != 'write':
            issues.append("❌ Missing 'id-token: write' permission (required for OIDC)")
        if perms.get('contents') != 'read':
            issues.append("⚠️  Missing 'contents: read' permission")
    
    # Check environment variables
    if 'env' not in workflow:
        issues.append("⚠️  No global environment variables defined")
    else:
        env_vars = workflow['env']
        required_env_vars = [
            'AWS_REGION', 'ECR_REPOSITORY', 'ECS_CLUSTER',
            'ECS_SERVICE', 'ECS_TASK_DEFINITION', 'CONTAINER_NAME'
        ]
        for var in required_env_vars:
            if var not in env_vars:
                issues.append(f"⚠️  Missing environment variable: {var}")
    
    # Check jobs
    if 'jobs' not in workflow:
        issues.append("❌ No jobs defined in workflow")
        return issues
    
    jobs = workflow['jobs']
    
    # Validate build job
    if 'build' not in jobs:
        issues.append("❌ Missing 'build' job")
    else:
        build_job = jobs['build']
        
        # Check outputs
        if 'outputs' not in build_job:
            issues.append("❌ Build job missing outputs")
        else:
            outputs = build_job['outputs']
            if 'image-uri' not in outputs:
                issues.append("❌ Build job missing 'image-uri' output")
        
        # Check steps
        if 'steps' not in build_job:
            issues.append("❌ Build job missing steps")
        else:
            steps = build_job['steps']
            step_names = [step.get('name', '') for step in steps]
            
            # Required steps
            required_steps = [
                'Checkout code',
                'Configure AWS credentials',
                'Login to Amazon ECR',
                'Build and push Docker image'
            ]
            for required_step in required_steps:
                if not any(required_step in name for name in step_names):
                    issues.append(f"❌ Build job missing step: {required_step}")
            
            # Check for caching
            if not any('cache' in name.lower() for name in step_names):
                issues.append("⚠️  No caching configured (recommended for faster builds)")
            
            # Check for Buildx
            if not any('buildx' in name.lower() for name in step_names):
                issues.append("⚠️  Docker Buildx not configured")
            
            # Validate OIDC configuration
            for step in steps:
                if step.get('name') == 'Configure AWS credentials (OIDC)':
                    if 'uses' in step:
                        if 'aws-actions/configure-aws-credentials' not in step['uses']:
                            issues.append("❌ Wrong action for AWS credentials")
                    if 'with' in step:
                        with_params = step['with']
                        if 'role-to-assume' not in with_params:
                            issues.append("❌ Missing 'role-to-assume' in AWS credentials step")
                        if 'aws-region' not in with_params:
                            issues.append("❌ Missing 'aws-region' in AWS credentials step")
            
            # Validate Docker build configuration
            for step in steps:
                if step.get('name') == 'Build and push Docker image':
                    if 'with' in step:
                        with_params = step['with']
                        
                        if 'platforms' not in with_params:
                            issues.append("⚠️  No platform specified in Docker build")
                        elif with_params['platforms'] != 'linux/amd64':
                            issues.append("⚠️  Platform should be 'linux/amd64' for ECS")
                        
                        if 'push' not in with_params or not with_params['push']:
                            issues.append("❌ Docker build not configured to push")
                        
                        if 'cache-from' not in with_params:
                            issues.append("⚠️  No cache-from configured")
                        
                        if 'cache-to' not in with_params:
                            issues.append("⚠️  No cache-to configured")
    
    # Validate deploy job
    if 'deploy' not in jobs:
        issues.append("❌ Missing 'deploy' job")
    else:
        deploy_job = jobs['deploy']
        
        # Check needs dependency
        if 'needs' not in deploy_job:
            issues.append("❌ Deploy job missing 'needs' dependency on build")
        elif deploy_job['needs'] != 'build' and 'build' not in deploy_job['needs']:
            issues.append("❌ Deploy job must depend on build job")
        
        # Check environment configuration
        if 'environment' in deploy_job:
            print("✅ Environment protection configured")
        else:
            issues.append("⚠️  No environment protection configured (recommended)")
        
        # Check steps
        if 'steps' not in deploy_job:
            issues.append("❌ Deploy job missing steps")
        else:
            steps = deploy_job['steps']
            step_names = [step.get('name', '') for step in steps]
            
            # Required steps
            required_steps = [
                'Download current task definition',
                'Update task definition',
                'Register new task definition',
                'Update ECS service',
                'Wait for service stability'
            ]
            for required_step in required_steps:
                if not any(required_step.lower() in name.lower() for name in step_names):
                    issues.append(f"❌ Deploy job missing step: {required_step}")
    
    # Validate rollback job
    if 'rollback' not in jobs:
        issues.append("⚠️  No rollback job configured (recommended)")
    else:
        rollback_job = jobs['rollback']
        
        # Check conditional execution
        if 'if' not in rollback_job:
            issues.append("⚠️  Rollback job should have conditional execution")
        elif 'failure()' not in rollback_job['if']:
            issues.append("⚠️  Rollback job should only run on failure")
        
        # Check needs
        if 'needs' not in rollback_job:
            issues.append("❌ Rollback job missing 'needs' dependencies")
    
    return issues


def validate_gpu_test_workflow(workflow_path: Path) -> List[str]:
    """Validate the GPU compatibility test workflow."""
    issues = []
    
    if not workflow_path.exists():
        issues.append(f"⚠️  GPU test workflow not found: {workflow_path} (optional but recommended)")
        return issues
    
    valid, msg, workflow = validate_yaml_syntax(workflow_path)
    if not valid:
        issues.append(f"❌ {msg}")
        return issues
    
    # Check for matrix strategy
    if 'jobs' in workflow:
        jobs = workflow['jobs']
        for job_name, job in jobs.items():
            if 'strategy' in job:
                if 'matrix' in job['strategy']:
                    print(f"✅ Matrix strategy configured in job: {job_name}")
                    matrix = job['strategy']['matrix']
                    
                    # Check for GPU-related matrix dimensions
                    if 'cuda_version' in matrix:
                        print(f"  ✅ CUDA version matrix: {matrix['cuda_version']}")
                    if 'driver_version' in matrix:
                        print(f"  ✅ Driver version matrix: {matrix['driver_version']}")
                    if 'pytorch_version' in matrix:
                        print(f"  ✅ PyTorch version matrix: {matrix['pytorch_version']}")
                    
                    # Check for exclusions
                    if 'exclude' in matrix:
                        print(f"  ✅ Matrix exclusions configured: {len(matrix['exclude'])} combinations")
    
    return issues


def validate_required_secrets() -> List[str]:
    """Validate that required secrets are documented."""
    issues = []
    
    readme_path = Path(".github/workflows/README-CICD.md")
    if not readme_path.exists():
        issues.append("❌ README-CICD.md not found")
        return issues
    
    with open(readme_path, 'r') as f:
        content = f.read()
    
    required_secrets = [
        'AWS_ROLE_ARN',
        'AWS_REGION',
        'ECR_REPOSITORY',
        'ECS_CLUSTER',
        'ECS_SERVICE',
        'ECS_TASK_DEFINITION'
    ]
    
    for secret in required_secrets:
        if secret not in content:
            issues.append(f"⚠️  Secret '{secret}' not documented in README")
    
    # Check for OIDC setup documentation
    if 'OIDC' not in content and 'OpenID Connect' not in content:
        issues.append("❌ OIDC setup not documented")
    
    # Check for GitHub Actions setup
    if 'GitHub Repository Setup' not in content:
        issues.append("❌ GitHub repository setup not documented")
    
    return issues


def validate_documentation() -> List[str]:
    """Validate documentation completeness."""
    issues = []
    
    readme_path = Path(".github/workflows/README-CICD.md")
    if not readme_path.exists():
        issues.append("❌ README-CICD.md not found")
        return issues
    
    with open(readme_path, 'r') as f:
        content = f.read()
    
    required_sections = [
        '## Overview',
        '## Prerequisites',
        '## AWS OIDC Setup',
        '## GitHub Repository Setup',
        '## Workflow Configuration',
        '## Usage',
        '## Troubleshooting',
        '## Best Practices'
    ]
    
    for section in required_sections:
        if section not in content:
            issues.append(f"❌ Missing documentation section: {section}")
    
    # Check for architecture diagram
    if '```' not in content or 'GitHub Actions' not in content:
        issues.append("⚠️  No architecture diagram found")
    
    # Check for examples
    if '```bash' not in content:
        issues.append("⚠️  No bash examples in documentation")
    
    # Check for troubleshooting
    common_issues = ['OIDC Authentication Failed', 'ECR Push Permission Denied', 'ECS Service Update Failed']
    for issue in common_issues:
        if issue not in content:
            issues.append(f"⚠️  Troubleshooting missing common issue: {issue}")
    
    return issues


def validate_workflow_structure() -> List[str]:
    """Validate overall workflow structure and best practices."""
    issues = []
    
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        issues.append("❌ .github/workflows directory not found")
        return issues
    
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    
    if not workflow_files:
        issues.append("❌ No workflow files found")
        return issues
    
    print(f"Found {len(workflow_files)} workflow file(s):")
    for wf in workflow_files:
        print(f"  - {wf.name}")
    
    # Check for recommended workflows
    recommended_workflows = ['deploy.yml', 'deploy.yaml']
    has_deploy = any(wf.name in recommended_workflows for wf in workflow_files)
    if not has_deploy:
        issues.append("❌ No deploy workflow found (deploy.yml or deploy.yaml)")
    
    return issues


def main():
    """Main validation function."""
    print("=" * 70)
    print("Step 10 Validation: GitHub Actions CI/CD Workflows")
    print("=" * 70)
    print()
    
    all_issues = []
    
    # 1. Validate workflow structure
    print("1. Validating workflow structure...")
    issues = validate_workflow_structure()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ Workflow structure valid")
    print()
    
    # 2. Validate deploy workflow
    print("2. Validating deploy.yml workflow...")
    deploy_path = Path(".github/workflows/deploy.yml")
    issues = validate_deploy_workflow(deploy_path)
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ Deploy workflow valid")
    print()
    
    # 3. Validate GPU test workflow
    print("3. Validating GPU compatibility test workflow...")
    gpu_test_path = Path(".github/workflows/gpu-compatibility-test.yml")
    issues = validate_gpu_test_workflow(gpu_test_path)
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ GPU test workflow valid")
    print()
    
    # 4. Validate required secrets
    print("4. Validating required secrets documentation...")
    issues = validate_required_secrets()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ All required secrets documented")
    print()
    
    # 5. Validate documentation
    print("5. Validating documentation completeness...")
    issues = validate_documentation()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ Documentation complete")
    print()
    
    # Summary
    print("=" * 70)
    print("Validation Summary")
    print("=" * 70)
    
    error_count = len([i for i in all_issues if i.startswith("❌")])
    warning_count = len([i for i in all_issues if i.startswith("⚠️")])
    
    if error_count == 0 and warning_count == 0:
        print("✅ All validations passed!")
        print()
        print("Step 10 is complete and ready for use.")
        print()
        print("Next steps:")
        print("1. Set up AWS OIDC provider (see README-CICD.md)")
        print("2. Configure GitHub repository secrets")
        print("3. Push to main branch to trigger deployment")
        return 0
    else:
        print(f"Found {error_count} error(s) and {warning_count} warning(s)")
        print()
        
        if error_count > 0:
            print("❌ Errors (must fix):")
            for issue in all_issues:
                if issue.startswith("❌"):
                    print(f"  {issue}")
            print()
        
        if warning_count > 0:
            print("⚠️  Warnings (recommended to fix):")
            for issue in all_issues:
                if issue.startswith("⚠️"):
                    print(f"  {issue}")
            print()
        
        if error_count > 0:
            print("Please fix the errors above before proceeding.")
            return 1
        else:
            print("Warnings are non-critical. You may proceed, but addressing them is recommended.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
