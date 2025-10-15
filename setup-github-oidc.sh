#!/bin/bash
#
# setup-github-oidc.sh
# 
# Script to set up AWS OIDC provider and IAM role for GitHub Actions.
# This script must be run once per AWS account before using the CI/CD workflow.
#
# Usage:
#   ./setup-github-oidc.sh <github-org> <github-repo>
#
# Example:
#   ./setup-github-oidc.sh myorg multicam-infer
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check arguments
if [ $# -ne 2 ]; then
    print_error "Usage: $0 <github-org> <github-repo>"
    print_info "Example: $0 myorg multicam-infer"
    exit 1
fi

GITHUB_ORG="$1"
GITHUB_REPO="$2"

print_info "Setting up GitHub OIDC for: ${GITHUB_ORG}/${GITHUB_REPO}"
echo ""

# Get AWS account ID
print_info "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_success "AWS Account ID: ${AWS_ACCOUNT_ID}"
echo ""

# Check if OIDC provider already exists
print_info "Checking if OIDC provider exists..."
if aws iam list-open-id-connect-providers | grep -q "token.actions.githubusercontent.com"; then
    print_warning "OIDC provider already exists. Skipping creation."
    OIDC_PROVIDER_ARN=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text)
    print_info "Existing OIDC Provider ARN: ${OIDC_PROVIDER_ARN}"
else
    print_info "Creating OIDC provider..."
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
    
    OIDC_PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
    print_success "OIDC provider created: ${OIDC_PROVIDER_ARN}"
fi
echo ""

# Create trust policy
print_info "Creating trust policy..."
cat > /tmp/github-actions-trust-policy.json << EOF
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
print_success "Trust policy created"
echo ""

# Create IAM role
ROLE_NAME="GitHubActionsECSDeployRole"
print_info "Creating IAM role: ${ROLE_NAME}..."

if aws iam get-role --role-name ${ROLE_NAME} 2>/dev/null; then
    print_warning "Role already exists. Updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-document file:///tmp/github-actions-trust-policy.json
    print_success "Trust policy updated"
else
    aws iam create-role \
        --role-name ${ROLE_NAME} \
        --assume-role-policy-document file:///tmp/github-actions-trust-policy.json \
        --description "Role for GitHub Actions to deploy to ECS"
    print_success "Role created: ${ROLE_NAME}"
fi
echo ""

# Create IAM policy
print_info "Creating IAM policy..."
cat > /tmp/github-actions-policy.json << EOF
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

POLICY_NAME="GitHubActionsECSDeployPolicy"
if aws iam get-policy --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}" 2>/dev/null; then
    print_warning "Policy already exists. Skipping creation."
    POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"
else
    print_info "Creating policy..."
    POLICY_ARN=$(aws iam create-policy \
        --policy-name ${POLICY_NAME} \
        --policy-document file:///tmp/github-actions-policy.json \
        --query 'Policy.Arn' \
        --output text)
    print_success "Policy created: ${POLICY_ARN}"
fi
echo ""

# Attach policy to role
print_info "Attaching policy to role..."
if aws iam list-attached-role-policies --role-name ${ROLE_NAME} | grep -q ${POLICY_NAME}; then
    print_warning "Policy already attached to role"
else
    aws iam attach-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-arn ${POLICY_ARN}
    print_success "Policy attached to role"
fi
echo ""

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name ${ROLE_NAME} --query 'Role.Arn' --output text)

# Clean up temp files
rm -f /tmp/github-actions-trust-policy.json /tmp/github-actions-policy.json

# Print summary
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "🎉 GitHub OIDC Setup Complete!"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
print_success "OIDC Provider: ${OIDC_PROVIDER_ARN}"
print_success "IAM Role: ${ROLE_NAME}"
print_success "IAM Policy: ${POLICY_NAME}"
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "📋 Next Steps: Configure GitHub Repository Secrets"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "Go to: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo "Add the following secrets:"
echo ""
print_info "AWS_ROLE_ARN"
echo "  Value: ${ROLE_ARN}"
echo ""
print_info "AWS_REGION"
echo "  Value: us-east-1  (or your preferred region)"
echo ""
print_info "ECR_REPOSITORY"
echo "  Value: kvs-infer  (your ECR repository name)"
echo ""
print_info "ECS_CLUSTER"
echo "  Value: kvs-infer-cluster  (your ECS cluster name)"
echo ""
print_info "ECS_SERVICE"
echo "  Value: kvs-infer-service  (your ECS service name)"
echo ""
print_info "ECS_TASK_DEFINITION"
echo "  Value: kvs-infer-task  (your task definition family name)"
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "✅ After configuring secrets, you can deploy by:"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "  1. Push to main branch:"
echo "     git push origin main"
echo ""
echo "  2. Create a tag:"
echo "     git tag -a v1.0.0 -m 'Release v1.0.0'"
echo "     git push origin v1.0.0"
echo ""
echo "  3. Manual workflow dispatch:"
echo "     Go to Actions → Build and Deploy to ECS → Run workflow"
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
