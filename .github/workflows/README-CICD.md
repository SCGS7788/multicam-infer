# GitHub Actions CI/CD for ECS GPU Deployment

Complete guide for setting up automated build and deployment pipelines for GPU-accelerated ECS workloads using GitHub Actions with AWS OIDC authentication.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [AWS OIDC Setup](#aws-oidc-setup)
- [GitHub Repository Setup](#github-repository-setup)
- [Workflow Configuration](#workflow-configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Actions                           │
│                                                                   │
│  ┌─────────────┐      ┌──────────────┐      ┌────────────────┐ │
│  │   Build     │─────▶│    Deploy    │─────▶│   Rollback     │ │
│  │             │      │              │      │  (on failure)  │ │
│  └─────────────┘      └──────────────┘      └────────────────┘ │
│         │                    │                                   │
└─────────┼────────────────────┼───────────────────────────────────┘
          │                    │
          ▼                    ▼
    ┌─────────┐         ┌──────────┐
    │   ECR   │         │   ECS    │
    │ (Image) │         │ (Deploy) │
    └─────────┘         └──────────┘
          │                    │
          │                    ▼
          │            ┌───────────────┐
          │            │  EC2 Instance │
          │            │  (g4dn GPU)   │
          │            └───────────────┘
          │                    │
          └────────────────────┘
              Pull & Run
```

### Workflows

1. **`deploy.yml`** - Main CI/CD pipeline
   - Build Docker image with GPU support
   - Push to Amazon ECR
   - Deploy to ECS with rolling update
   - Automatic rollback on failure

2. **`gpu-compatibility-test.yml`** - GPU validation
   - Test CUDA/driver compatibility matrix
   - Validate GPU detection in ECS
   - Generate compatibility reports

## Prerequisites

### AWS Account Setup

1. **AWS Account** with permissions for:
   - IAM (create roles, policies)
   - ECR (repository management)
   - ECS (cluster, service, task management)
   - EC2 (for ECS instances)

2. **Existing ECS Infrastructure** (from Step 9):
   - ECS cluster with GPU instances
   - ECS service running
   - ECR repository created
   - Task definition registered

3. **AWS CLI** installed and configured:
   ```bash
   aws --version  # Should be 2.x
   ```

### GitHub Repository Setup

1. **GitHub repository** with admin access
2. **GitHub Actions enabled** in repository settings

## AWS OIDC Setup

### Why OIDC?

OIDC (OpenID Connect) allows GitHub Actions to authenticate with AWS without storing long-lived credentials as secrets. This is more secure and follows AWS best practices.

**Benefits:**
- ✅ No long-lived access keys
- ✅ Automatic key rotation
- ✅ Fine-grained permissions per workflow
- ✅ Audit trail in CloudTrail

### Step 1: Create OIDC Identity Provider

Create the GitHub OIDC provider in AWS IAM:

```bash
# Set variables
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
GITHUB_ORG="your-github-username-or-org"
GITHUB_REPO="multicam-infer"

# Create OIDC provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

**Note:** The thumbprint `6938fd4d98bab03faadb97b34396831e3780aea1` is GitHub's current certificate thumbprint. Verify the latest thumbprint from [GitHub's documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services).

### Step 2: Create IAM Role for GitHub Actions

Create a role that GitHub Actions will assume:

```bash
# Create trust policy
cat > github-actions-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name GitHubActionsECSDeployRole \
  --assume-role-policy-document file://github-actions-trust-policy.json \
  --description "Role for GitHub Actions to deploy to ECS"
```

### Step 3: Attach Policies to the Role

Create and attach a policy with necessary permissions:

```bash
cat > github-actions-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECSAccess",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:DeregisterTaskDefinition",
        "ecs:DescribeServices",
        "ecs:UpdateService",
        "ecs:DescribeTasks",
        "ecs:RunTask",
        "ecs:StopTask",
        "ecs:ListTasks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMPassRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::${AWS_ACCOUNT_ID}:role/kvs-infer-task-role",
        "arn:aws:iam::${AWS_ACCOUNT_ID}:role/kvs-infer-execution-role"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:*:${AWS_ACCOUNT_ID}:log-group:/ecs/*"
    }
  ]
}
EOF

# Create the policy
aws iam create-policy \
  --policy-name GitHubActionsECSDeployPolicy \
  --policy-document file://github-actions-policy.json

# Attach the policy to the role
aws iam attach-role-policy \
  --role-name GitHubActionsECSDeployRole \
  --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/GitHubActionsECSDeployPolicy"
```

### Step 4: Get the Role ARN

Save this for GitHub secrets:

```bash
aws iam get-role \
  --role-name GitHubActionsECSDeployRole \
  --query 'Role.Arn' \
  --output text
```

Output example:
```
arn:aws:iam::123456789012:role/GitHubActionsECSDeployRole
```

## GitHub Repository Setup

### Step 1: Configure Repository Secrets

Go to your GitHub repository:
1. Navigate to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the following secrets:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_ROLE_ARN` | IAM role ARN from OIDC setup | `arn:aws:iam::123456789012:role/GitHubActionsECSDeployRole` |
| `AWS_REGION` | AWS region for deployment | `us-east-1` |
| `ECR_REPOSITORY` | ECR repository name | `kvs-infer` |
| `ECS_CLUSTER` | ECS cluster name | `kvs-infer-cluster` |
| `ECS_SERVICE` | ECS service name | `kvs-infer-service` |
| `ECS_TASK_DEFINITION` | Task definition family name | `kvs-infer-task` |

### Step 2: Configure Repository Variables (Optional)

For non-sensitive configuration:

1. Navigate to **Settings** → **Secrets and variables** → **Actions** → **Variables** tab
2. Add environment-specific variables

### Step 3: Enable GitHub Actions Permissions

1. Go to **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, select:
   - ✅ **Read and write permissions**
   - ✅ **Allow GitHub Actions to create and approve pull requests**

## Workflow Configuration

### Main Deployment Workflow

File: `.github/workflows/deploy.yml`

**Triggers:**
- Push to `main` branch
- Push tags (e.g., `v1.0.0`)
- Manual workflow dispatch

**Jobs:**

1. **Build Job**
   - Checkout code
   - Set up Python with pip caching
   - Configure Docker Buildx with layer caching
   - Authenticate with AWS via OIDC
   - Login to Amazon ECR
   - Build multi-platform Docker image (linux/amd64)
   - Push to ECR with multiple tags (SHA, semver, latest)
   - Scan image for vulnerabilities with Trivy
   - Output image URI for deployment

2. **Deploy Job**
   - Download current ECS task definition
   - Update task definition with new image URI
   - Register new task definition revision
   - Update ECS service with new task definition
   - Wait for service stability (deployment complete)
   - Display deployment status summary

3. **Rollback Job** (runs on failure)
   - Find previous stable task definition
   - Rollback to previous task definition
   - Force new deployment

### GPU Compatibility Test Workflow

File: `.github/workflows/gpu-compatibility-test.yml`

**Triggers:**
- Manual workflow dispatch (with instance type selection)
- Weekly schedule (Sundays at 2 AM UTC)

**Features:**
- Test matrix for CUDA versions, driver versions, PyTorch versions
- GPU detection validation on actual ECS tasks
- Compatibility report generation
- Performance benchmarks

## Usage

### Deploy to Production

#### Option 1: Automatic Deployment (Push to Main)

```bash
# Commit and push to main branch
git add .
git commit -m "feat: add new feature"
git push origin main
```

The workflow will automatically:
1. Build Docker image
2. Push to ECR
3. Deploy to ECS
4. Wait for stability

#### Option 2: Tagged Release

```bash
# Create a release tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

This creates a release with proper semantic versioning tags in ECR.

#### Option 3: Manual Deployment

1. Go to **Actions** → **Build and Deploy to ECS**
2. Click **Run workflow**
3. Select environment (production/staging)
4. Click **Run workflow**

### Monitor Deployment

#### View Workflow Progress

1. Go to **Actions** tab in GitHub
2. Click on the running workflow
3. Monitor each job's progress in real-time

#### View Deployment Summary

After deployment completes, GitHub Actions creates a summary:

```
### 🐳 Docker Image Built
**Image URI:** `123456789012.dkr.ecr.us-east-1.amazonaws.com/kvs-infer:sha-abc1234`
**Image Tag:** `sha-abc1234`
**Commit SHA:** `abc1234567890...`

### 📋 Task Definition Registered
**ARN:** `arn:aws:ecs:us-east-1:123456789012:task-definition/kvs-infer-task:42`

### ✅ Deployment Complete
**Cluster:** `kvs-infer-cluster`
**Service:** `kvs-infer-service`
**Task Definition:** `arn:aws:ecs:...:task-definition/kvs-infer-task:42`
**Image:** `123456789012.dkr.ecr.us-east-1.amazonaws.com/kvs-infer:sha-abc1234`

🎉 Service is stable and running!
```

#### Check ECS Service Status

```bash
# Via AWS CLI
aws ecs describe-services \
  --cluster kvs-infer-cluster \
  --services kvs-infer-service \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'

# Via AWS Console
# Navigate to: ECS → Clusters → kvs-infer-cluster → Services → kvs-infer-service
```

### Rollback a Deployment

#### Automatic Rollback

If the deployment fails (health checks, stability timeout), the workflow automatically:
1. Detects the failure
2. Finds the previous stable task definition
3. Rolls back to that version
4. Forces a new deployment

#### Manual Rollback

If you need to rollback manually:

```bash
# List recent task definitions
aws ecs list-task-definitions \
  --family-prefix kvs-infer-task \
  --sort DESC \
  --max-items 5

# Rollback to specific revision
aws ecs update-service \
  --cluster kvs-infer-cluster \
  --service kvs-infer-service \
  --task-definition kvs-infer-task:41 \  # Previous revision
  --force-new-deployment
```

Or use the GitHub Actions workflow:
1. Go to **Actions** → **Build and Deploy to ECS**
2. Click **Re-run jobs** on a previous successful deployment

### Test GPU Compatibility

Run the GPU compatibility test workflow:

```bash
# Via GitHub UI
# Go to Actions → GPU Driver Compatibility Test → Run workflow
# Select instance type (e.g., g4dn.xlarge)

# Or trigger via API
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/YOUR_ORG/multicam-infer/actions/workflows/gpu-compatibility-test.yml/dispatches \
  -d '{"ref":"main","inputs":{"instance_type":"g4dn.xlarge"}}'
```

## Troubleshooting

### Common Issues

#### Issue 1: OIDC Authentication Failed

**Error:**
```
Error: Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

**Solutions:**
1. Verify the OIDC provider is created:
   ```bash
   aws iam list-open-id-connect-providers
   ```

2. Check the role trust policy:
   ```bash
   aws iam get-role --role-name GitHubActionsECSDeployRole --query 'Role.AssumeRolePolicyDocument'
   ```

3. Ensure the repository matches the trust policy condition:
   ```json
   "StringLike": {
     "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
   }
   ```

#### Issue 2: ECR Push Permission Denied

**Error:**
```
denied: User: arn:aws:sts::123456789012:assumed-role/GitHubActionsECSDeployRole/... is not authorized to perform: ecr:PutImage
```

**Solutions:**
1. Verify the role has ECR permissions:
   ```bash
   aws iam list-attached-role-policies --role-name GitHubActionsECSDeployRole
   ```

2. Check ECR repository policy:
   ```bash
   aws ecr get-repository-policy --repository-name kvs-infer
   ```

3. Ensure the role can access ECR:
   ```bash
   # Test ECR login
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin \
     123456789012.dkr.ecr.us-east-1.amazonaws.com
   ```

#### Issue 3: ECS Service Update Failed

**Error:**
```
Error: Service update failed to stabilize
```

**Solutions:**
1. Check ECS service events:
   ```bash
   aws ecs describe-services \
     --cluster kvs-infer-cluster \
     --services kvs-infer-service \
     --query 'services[0].events[:5]'
   ```

2. Common causes:
   - Health check failures (check container logs)
   - Insufficient resources (CPU/Memory/GPU)
   - Network connectivity issues (security groups, subnets)
   - IAM permission issues (task role, execution role)

3. Check container logs:
   ```bash
   # Get task ARN
   TASK_ARN=$(aws ecs list-tasks \
     --cluster kvs-infer-cluster \
     --service-name kvs-infer-service \
     --query 'taskArns[0]' \
     --output text)
   
   # View logs
   aws logs tail /ecs/kvs-infer --follow
   ```

#### Issue 4: GPU Not Available in Container

**Error:**
```
RuntimeError: CUDA not available
```

**Solutions:**
1. Verify task definition has GPU resource:
   ```bash
   aws ecs describe-task-definition \
     --task-definition kvs-infer-task \
     --query 'taskDefinition.containerDefinitions[0].resourceRequirements'
   ```
   
   Should show:
   ```json
   [{"type": "GPU", "value": "1"}]
   ```

2. Check EC2 instance has GPU:
   ```bash
   # SSH to ECS instance
   nvidia-smi
   
   # Should show Tesla T4 GPU
   ```

3. Verify ECS agent version supports GPU (>= 1.56.0):
   ```bash
   # On ECS instance
   cat /etc/ecs/ecs.config | grep ECS_AGENT_VERSION
   ```

#### Issue 5: Build Cache Not Working

**Symptom:** Slow builds, rebuilding layers every time

**Solutions:**
1. Verify cache paths in workflow:
   ```yaml
   - uses: actions/cache@v4
     with:
       path: /tmp/.buildx-cache
       key: ${{ runner.os }}-buildx-${{ github.sha }}
       restore-keys: |
         ${{ runner.os }}-buildx-
   ```

2. Check Docker Buildx cache:
   ```yaml
   - uses: docker/build-push-action@v5
     with:
       cache-from: type=local,src=/tmp/.buildx-cache
       cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max
   ```

3. Ensure cache is moved properly:
   ```yaml
   - name: Move cache
     run: |
       rm -rf /tmp/.buildx-cache
       mv /tmp/.buildx-cache-new /tmp/.buildx-cache
   ```

### Debug Mode

Enable debug logging in GitHub Actions:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add secrets:
   - `ACTIONS_RUNNER_DEBUG` = `true`
   - `ACTIONS_STEP_DEBUG` = `true`

3. Re-run the workflow to see detailed logs

### Check Workflow Logs

View detailed logs for each step:

```bash
# Via GitHub CLI
gh run view --log

# Or download logs
gh run download
```

## Best Practices

### Security

1. **Never commit secrets to the repository**
   - Use GitHub Secrets for sensitive data
   - Use OIDC instead of long-lived credentials

2. **Limit IAM permissions**
   - Follow least-privilege principle
   - Use resource-level restrictions
   - Add condition keys where possible

3. **Scan images for vulnerabilities**
   - Trivy scanning enabled in workflow
   - Review scan results before deployment
   - Set up vulnerability alerts

4. **Use immutable tags for production**
   - Avoid using `:latest` in production
   - Use SHA-based tags for traceability
   - Use semantic versioning for releases

### Performance

1. **Cache dependencies**
   - Enable pip caching for Python dependencies
   - Use Docker layer caching
   - Cache node_modules if using Node.js

2. **Optimize Docker images**
   - Use multi-stage builds
   - Minimize layer count
   - Remove unnecessary files

3. **Parallel job execution**
   - Build and test in parallel when possible
   - Use matrix strategy for multiple configurations

### Reliability

1. **Health checks**
   - Configure container health checks
   - Set appropriate timeouts
   - Test health check endpoints locally

2. **Deployment strategies**
   - Use rolling updates (default)
   - Enable circuit breaker for automatic rollback
   - Configure deployment configuration:
     ```json
     {
       "deploymentConfiguration": {
         "minimumHealthyPercent": 100,
         "maximumPercent": 200
       }
     }
     ```

3. **Monitoring**
   - Enable Container Insights
   - Set up CloudWatch alarms
   - Monitor deployment metrics

4. **Testing**
   - Run tests before deployment
   - Use staging environment for validation
   - Implement smoke tests after deployment

### Cost Optimization

1. **Use spot instances for development**
   - Reduce costs by ~70%
   - Acceptable for non-critical workloads
   - Configure in ECS capacity provider

2. **Optimize build caching**
   - Reduces build time and cost
   - Cache Docker layers
   - Cache pip dependencies

3. **Clean up old images**
   - Set ECR lifecycle policies
   - Keep last N images or images from last N days
   - Example:
     ```json
     {
       "rules": [{
         "rulePriority": 1,
         "description": "Keep last 10 images",
         "selection": {
           "tagStatus": "any",
           "countType": "imageCountMoreThan",
           "countNumber": 10
         },
         "action": {"type": "expire"}
       }]
     }
     ```

## Next Steps

After setting up CI/CD:

1. **Set up staging environment**
   - Create separate ECS cluster/service for staging
   - Deploy to staging before production
   - Run integration tests in staging

2. **Configure notifications**
   - Slack notifications for deployment status
   - Email alerts for failures
   - PagerDuty integration for critical alerts

3. **Implement blue/green deployment**
   - Use AWS CodeDeploy with ECS
   - Zero-downtime deployments
   - Easy rollback

4. **Add more tests**
   - Unit tests in CI
   - Integration tests in staging
   - Load tests before production

5. **Set up monitoring dashboards**
   - CloudWatch dashboards for ECS metrics
   - Custom metrics from application
   - Grafana for visualization

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS OIDC with GitHub Actions](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [Amazon ECS Developer Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [AWS Actions for GitHub](https://github.com/aws-actions)

## Support

For issues or questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review workflow logs in GitHub Actions
- Check CloudWatch Logs for application logs
- Review ECS service events for deployment issues
