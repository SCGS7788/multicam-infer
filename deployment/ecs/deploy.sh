#!/bin/bash
# ECS Deployment Script for KVS Inference
# Automates the complete ECS deployment process

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again."
        exit 1
    fi
    
    log_success "All prerequisites are installed"
}

# Load environment variables
load_env() {
    log_info "Loading environment variables..."
    
    if [ -f "deployment/ecs/.env" ]; then
        source deployment/ecs/.env
        log_success "Environment variables loaded from deployment/ecs/.env"
    else
        log_warning "No .env file found. Using environment variables."
    fi
    
    # Required variables
    required_vars=(
        "AWS_REGION"
        "AWS_ACCOUNT_ID"
        "ECR_REPO_NAME"
        "ECS_CLUSTER_NAME"
        "VPC_ID"
        "PRIVATE_SUBNET_1"
        "PRIVATE_SUBNET_2"
        "KVS_STREAM_PREFIX"
        "KDS_STREAM_NAME"
        "S3_BUCKET_NAME"
        "S3_PREFIX"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "All required environment variables are set"
}

# Step 1: Create ECR repository
create_ecr_repo() {
    log_info "Step 1: Creating ECR repository..."
    
    if aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --region "${AWS_REGION}" &> /dev/null; then
        log_warning "ECR repository ${ECR_REPO_NAME} already exists"
    else
        aws ecr create-repository \
            --repository-name "${ECR_REPO_NAME}" \
            --region "${AWS_REGION}" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 \
            --tags Key=Project,Value=kvs-infer Key=ManagedBy,Value=terraform
        
        log_success "ECR repository ${ECR_REPO_NAME} created"
    fi
    
    # Get repository URI
    export ECR_REPO_URI=$(aws ecr describe-repositories \
        --repository-names "${ECR_REPO_NAME}" \
        --region "${AWS_REGION}" \
        --query 'repositories[0].repositoryUri' \
        --output text)
    
    log_info "ECR Repository URI: ${ECR_REPO_URI}"
}

# Step 2: Build and push Docker image
build_and_push_image() {
    log_info "Step 2: Building and pushing Docker image..."
    
    # Login to ECR
    log_info "Logging into ECR..."
    aws ecr get-login-password --region "${AWS_REGION}" | \
        docker login --username AWS --password-stdin "${ECR_REPO_URI}"
    
    # Build image
    log_info "Building Docker image..."
    docker build --platform linux/amd64 -t "${ECR_REPO_NAME}:latest" .
    
    # Tag image
    log_info "Tagging Docker image..."
    docker tag "${ECR_REPO_NAME}:latest" "${ECR_REPO_URI}:latest"
    
    # Generate timestamp tag
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    docker tag "${ECR_REPO_NAME}:latest" "${ECR_REPO_URI}:${TIMESTAMP}"
    
    # Push images
    log_info "Pushing Docker images..."
    docker push "${ECR_REPO_URI}:latest"
    docker push "${ECR_REPO_URI}:${TIMESTAMP}"
    
    log_success "Docker image pushed to ${ECR_REPO_URI}:latest and ${ECR_REPO_URI}:${TIMESTAMP}"
}

# Step 3: Create IAM roles
create_iam_roles() {
    log_info "Step 3: Creating IAM roles..."
    
    # Create trust policy
    cat > /tmp/task-role-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
    
    # Create Task Role
    if aws iam get-role --role-name kvs-infer-task-role &> /dev/null; then
        log_warning "IAM role kvs-infer-task-role already exists"
    else
        aws iam create-role \
            --role-name kvs-infer-task-role \
            --assume-role-policy-document file:///tmp/task-role-trust-policy.json \
            --description "Task role for KVS Inference ECS tasks" \
            --tags Key=Project,Value=kvs-infer
        
        log_success "IAM role kvs-infer-task-role created"
    fi
    
    # Attach task role policy
    log_info "Attaching task role policy..."
    sed -e "s/\${AWS_REGION}/${AWS_REGION}/g" \
        -e "s/\${AWS_ACCOUNT_ID}/${AWS_ACCOUNT_ID}/g" \
        -e "s/\${KVS_STREAM_PREFIX}/${KVS_STREAM_PREFIX}/g" \
        -e "s/\${KDS_STREAM_NAME}/${KDS_STREAM_NAME}/g" \
        -e "s/\${S3_BUCKET_NAME}/${S3_BUCKET_NAME}/g" \
        -e "s/\${S3_PREFIX}/${S3_PREFIX}/g" \
        -e "s/\${DYNAMODB_TABLE_NAME}/${DYNAMODB_TABLE_NAME:-kvs-inference-metadata}/g" \
        deployment/ecs/iam-task-role.json > /tmp/iam-task-role-resolved.json
    
    aws iam put-role-policy \
        --role-name kvs-infer-task-role \
        --policy-name kvs-infer-task-policy \
        --policy-document file:///tmp/iam-task-role-resolved.json
    
    log_success "Task role policy attached"
    
    # Create Execution Role
    if aws iam get-role --role-name kvs-infer-execution-role &> /dev/null; then
        log_warning "IAM role kvs-infer-execution-role already exists"
    else
        aws iam create-role \
            --role-name kvs-infer-execution-role \
            --assume-role-policy-document file:///tmp/task-role-trust-policy.json \
            --description "Execution role for KVS Inference ECS tasks" \
            --tags Key=Project,Value=kvs-infer
        
        log_success "IAM role kvs-infer-execution-role created"
    fi
    
    # Attach execution role policy
    log_info "Attaching execution role policy..."
    sed -e "s/\${AWS_REGION}/${AWS_REGION}/g" \
        -e "s/\${AWS_ACCOUNT_ID}/${AWS_ACCOUNT_ID}/g" \
        deployment/ecs/iam-execution-role.json > /tmp/iam-execution-role-resolved.json
    
    aws iam put-role-policy \
        --role-name kvs-infer-execution-role \
        --policy-name kvs-infer-execution-policy \
        --policy-document file:///tmp/iam-execution-role-resolved.json
    
    log_success "Execution role policy attached"
}

# Step 4: Create ECS cluster
create_ecs_cluster() {
    log_info "Step 4: Creating ECS cluster..."
    
    if aws ecs describe-clusters --clusters "${ECS_CLUSTER_NAME}" --region "${AWS_REGION}" \
        --query 'clusters[0].clusterName' --output text 2>/dev/null | grep -q "${ECS_CLUSTER_NAME}"; then
        log_warning "ECS cluster ${ECS_CLUSTER_NAME} already exists"
    else
        aws ecs create-cluster \
            --cluster-name "${ECS_CLUSTER_NAME}" \
            --region "${AWS_REGION}" \
            --settings name=containerInsights,value=enabled \
            --tags Key=Project,Value=kvs-infer Key=Environment,Value=production
        
        log_success "ECS cluster ${ECS_CLUSTER_NAME} created"
    fi
}

# Step 5: Register task definition
register_task_definition() {
    log_info "Step 5: Registering task definition..."
    
    # Substitute variables
    sed -e "s/\${AWS_REGION}/${AWS_REGION}/g" \
        -e "s/\${AWS_ACCOUNT_ID}/${AWS_ACCOUNT_ID}/g" \
        deployment/ecs/ecs-task-def.json > /tmp/ecs-task-def-resolved.json
    
    # Register task definition
    aws ecs register-task-definition \
        --cli-input-json file:///tmp/ecs-task-def-resolved.json \
        --region "${AWS_REGION}" > /dev/null
    
    log_success "Task definition kvs-infer-gpu registered"
    
    # Get latest revision
    TASK_DEF_REVISION=$(aws ecs describe-task-definition \
        --task-definition kvs-infer-gpu \
        --region "${AWS_REGION}" \
        --query 'taskDefinition.revision' \
        --output text)
    
    log_info "Latest task definition revision: ${TASK_DEF_REVISION}"
}

# Step 6: Create security group
create_security_group() {
    log_info "Step 6: Creating security group..."
    
    # Check if security group exists
    EXISTING_SG=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=kvs-infer-ecs-sg" "Name=vpc-id,Values=${VPC_ID}" \
        --region "${AWS_REGION}" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "${EXISTING_SG}" ] && [ "${EXISTING_SG}" != "None" ]; then
        export SECURITY_GROUP_ID="${EXISTING_SG}"
        log_warning "Security group kvs-infer-ecs-sg already exists: ${SECURITY_GROUP_ID}"
    else
        export SECURITY_GROUP_ID=$(aws ec2 create-security-group \
            --group-name kvs-infer-ecs-sg \
            --description "Security group for KVS Inference ECS tasks" \
            --vpc-id "${VPC_ID}" \
            --region "${AWS_REGION}" \
            --query 'GroupId' \
            --output text)
        
        # Allow egress to HTTPS
        aws ec2 authorize-security-group-egress \
            --group-id "${SECURITY_GROUP_ID}" \
            --protocol tcp \
            --port 443 \
            --cidr 0.0.0.0/0 \
            --region "${AWS_REGION}" || true
        
        # Allow egress to HTTP
        aws ec2 authorize-security-group-egress \
            --group-id "${SECURITY_GROUP_ID}" \
            --protocol tcp \
            --port 80 \
            --cidr 0.0.0.0/0 \
            --region "${AWS_REGION}" || true
        
        # Tag security group
        aws ec2 create-tags \
            --resources "${SECURITY_GROUP_ID}" \
            --tags Key=Name,Value=kvs-infer-ecs-sg Key=Project,Value=kvs-infer \
            --region "${AWS_REGION}"
        
        log_success "Security group created: ${SECURITY_GROUP_ID}"
    fi
}

# Step 7: Create ECS service
create_ecs_service() {
    log_info "Step 7: Creating ECS service..."
    
    # Check if service exists
    if aws ecs describe-services \
        --cluster "${ECS_CLUSTER_NAME}" \
        --services kvs-infer-service \
        --region "${AWS_REGION}" \
        --query 'services[0].serviceName' \
        --output text 2>/dev/null | grep -q "kvs-infer-service"; then
        
        log_warning "ECS service kvs-infer-service already exists"
        log_info "Updating service with new task definition..."
        
        aws ecs update-service \
            --cluster "${ECS_CLUSTER_NAME}" \
            --service kvs-infer-service \
            --task-definition kvs-infer-gpu \
            --force-new-deployment \
            --region "${AWS_REGION}" > /dev/null
        
        log_success "Service updated"
    else
        # Substitute variables
        sed -e "s/\${ECS_CLUSTER_NAME}/${ECS_CLUSTER_NAME}/g" \
            -e "s/\${PRIVATE_SUBNET_1}/${PRIVATE_SUBNET_1}/g" \
            -e "s/\${PRIVATE_SUBNET_2}/${PRIVATE_SUBNET_2}/g" \
            -e "s/\${SECURITY_GROUP_ID}/${SECURITY_GROUP_ID}/g" \
            deployment/ecs/ecs-service.json > /tmp/ecs-service-resolved.json
        
        # Create service
        aws ecs create-service \
            --cli-input-json file:///tmp/ecs-service-resolved.json \
            --region "${AWS_REGION}" > /dev/null
        
        log_success "ECS service kvs-infer-service created"
    fi
    
    # Wait for service to become stable
    log_info "Waiting for service to become stable (this may take a few minutes)..."
    aws ecs wait services-stable \
        --cluster "${ECS_CLUSTER_NAME}" \
        --services kvs-infer-service \
        --region "${AWS_REGION}" 2>/dev/null || log_warning "Service not stable yet. Check ECS console for details."
    
    log_success "Service is running"
}

# Main deployment function
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  KVS Inference ECS Deployment Script  ${NC}"
    echo -e "${GREEN}========================================${NC}\n"
    
    check_prerequisites
    load_env
    
    echo ""
    log_info "Deployment parameters:"
    echo "  Region: ${AWS_REGION}"
    echo "  Account ID: ${AWS_ACCOUNT_ID}"
    echo "  ECR Repo: ${ECR_REPO_NAME}"
    echo "  ECS Cluster: ${ECS_CLUSTER_NAME}"
    echo "  VPC ID: ${VPC_ID}"
    echo ""
    
    read -p "Continue with deployment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    
    create_ecr_repo
    build_and_push_image
    create_iam_roles
    create_ecs_cluster
    register_task_definition
    create_security_group
    create_ecs_service
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Deployment Complete! 🎉              ${NC}"
    echo -e "${GREEN}========================================${NC}\n"
    
    log_success "ECS service is running"
    log_info "View service status:"
    echo "  aws ecs describe-services --cluster ${ECS_CLUSTER_NAME} --services kvs-infer-service"
    echo ""
    log_info "View logs:"
    echo "  aws logs tail /ecs/kvs-infer --follow"
    echo ""
    log_info "View tasks:"
    echo "  aws ecs list-tasks --cluster ${ECS_CLUSTER_NAME} --service-name kvs-infer-service"
}

# Run main function
main "$@"
