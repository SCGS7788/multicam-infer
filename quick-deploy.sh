#!/bin/bash
# =============================================================================
# Quick Deploy Script for kvs-infer to AWS ECS
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
AWS_ACCOUNT_ID=065693560492
AWS_REGION=ap-southeast-1
ECR_REPO_NAME=kvs-infer
IMAGE_TAG=latest

log_info "Starting deployment to AWS ECS..."

# Step 1: Create ECR repository
log_info "Step 1: Creating ECR repository..."
if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION &>/dev/null; then
    log_success "ECR repository $ECR_REPO_NAME already exists"
else
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256
    log_success "Created ECR repository: $ECR_REPO_NAME"
fi

# Step 2: Login to ECR
log_info "Step 2: Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
log_success "Logged into ECR"

# Step 3: Tag and push image
log_info "Step 3: Tagging and pushing Docker image..."
ECR_IMAGE_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG

docker tag kvs-infer:$IMAGE_TAG $ECR_IMAGE_URI
docker push $ECR_IMAGE_URI
log_success "Pushed image to ECR: $ECR_IMAGE_URI"

# Step 4: Create ECS cluster (if not exists)
log_info "Step 4: Creating ECS cluster..."
CLUSTER_NAME=kvs-infer-cluster

if aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    log_success "ECS cluster $CLUSTER_NAME already exists"
else
    aws ecs create-cluster \
        --cluster-name $CLUSTER_NAME \
        --region $AWS_REGION \
        --settings name=containerInsights,value=enabled
    log_success "Created ECS cluster: $CLUSTER_NAME"
fi

log_success "===================================="
log_success "Deployment preparation completed!"
log_success "===================================="
echo ""
log_info "Next steps:"
echo "1. Configure VPC and subnets in task definition"
echo "2. Create ECS task definition with GPU support"
echo "3. Launch ECS service"
echo ""
log_info "ECR Image URI: $ECR_IMAGE_URI"
