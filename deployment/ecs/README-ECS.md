# ECS (EC2 GPU) Deployment Guide

Complete guide for deploying the KVS Inference application on Amazon ECS with GPU-enabled EC2 instances.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [VPC Endpoints Configuration](#vpc-endpoints-configuration)
5. [Monitoring & Container Insights](#monitoring--container-insights)
6. [Troubleshooting](#troubleshooting)
7. [Cost Optimization](#cost-optimization)

---

## Prerequisites

### Required Tools
- AWS CLI v2 (configured with appropriate credentials)
- Docker (for building and pushing images)
- jq (for JSON processing)
- Access to AWS account with appropriate IAM permissions

### AWS Resources Required
- VPC with private subnets (minimum 2 AZs)
- NAT Gateway or NAT Instance (for initial setup)
- Security groups configured for egress traffic
- KVS streams (already created from previous steps)
- KDS stream (for event publishing)
- S3 bucket (for snapshot storage)
- DynamoDB table (optional, for state management)

### Environment Variables
Set the following variables before starting:

```bash
export AWS_REGION="ap-southeast-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export PROJECT_NAME="kvs-infer"
export ECR_REPO_NAME="kvs-infer"
export ECS_CLUSTER_NAME="kvs-infer-cluster"
export VPC_ID="vpc-xxxxx"
export PRIVATE_SUBNET_1="subnet-xxxxx"
export PRIVATE_SUBNET_2="subnet-xxxxx"
export KVS_STREAM_PREFIX="camera"
export KDS_STREAM_NAME="kvs-detection-events"
export S3_BUCKET_NAME="kvs-inference-snapshots"
export S3_PREFIX="snapshots"
export DYNAMODB_TABLE_NAME="kvs-inference-metadata"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          VPC (Private Subnets)                   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              ECS Cluster (EC2 GPU Instances)                │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │    ECS Task (kvs-infer-gpu)          │                  │ │
│  │  │  ┌────────────────────────────────┐  │                  │ │
│  │  │  │  Container (kvs-infer)         │  │                  │ │
│  │  │  │  - GPU: 1x NVIDIA T4           │  │                  │ │
│  │  │  │  - CPU: 4 vCPU                 │  │                  │ │
│  │  │  │  - Memory: 16 GB               │  │                  │ │
│  │  │  │  - Port: 8080 (health/metrics) │  │                  │ │
│  │  │  └────────────────────────────────┘  │                  │ │
│  │  │                                       │                  │ │
│  │  │  Volumes (Host Paths):                │                  │ │
│  │  │  - /opt/kvs-infer/config (ro)        │                  │ │
│  │  │  - /opt/kvs-infer/models (ro)        │                  │ │
│  │  │  - /opt/kvs-infer/cache (rw)         │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │                         │                                    │ │
│  └─────────────────────────┼────────────────────────────────────┘ │
│                            │                                      │
│                            ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              VPC Endpoints (PrivateLink)                     │ │
│  │  - com.amazonaws.${region}.ecr.api                          │ │
│  │  - com.amazonaws.${region}.ecr.dkr                          │ │
│  │  - com.amazonaws.${region}.s3 (Gateway)                     │ │
│  │  - com.amazonaws.${region}.logs                             │ │
│  │  - com.amazonaws.${region}.kinesis-streams                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            │ NAT Gateway (for KVS only)
                            ▼
                    ┌───────────────┐
                    │  AWS Services │
                    ├───────────────┤
                    │ KVS Streams   │ ← Requires Internet/NAT
                    │ KDS Stream    │ ← Via VPC Endpoint
                    │ S3 Bucket     │ ← Via VPC Endpoint
                    │ CloudWatch    │ ← Via VPC Endpoint
                    │ ECR Registry  │ ← Via VPC Endpoint
                    └───────────────┘
```

### Key Components

1. **ECS Cluster**: EC2-based cluster with GPU instances (g4dn.* family)
2. **ECS Task**: GPU-enabled container running inference workload
3. **IAM Roles**: 
   - Task Role (application permissions)
   - Execution Role (ECS service permissions)
4. **VPC Endpoints**: Reduce NAT usage and improve security
5. **CloudWatch**: Logs and Container Insights metrics

---

## Step-by-Step Deployment

### Step 1: Create ECR Repository

Create a private ECR repository to store Docker images:

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name ${ECR_REPO_NAME} \
  --region ${AWS_REGION} \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256 \
  --tags Key=Project,Value=kvs-infer Key=ManagedBy,Value=ecr

# Get repository URI
ECR_REPO_URI=$(aws ecr describe-repositories \
  --repository-names ${ECR_REPO_NAME} \
  --region ${AWS_REGION} \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "ECR Repository URI: ${ECR_REPO_URI}"
```

**Set lifecycle policy** to manage image retention:

```bash
cat > ecr-lifecycle-policy.json <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF

aws ecr put-lifecycle-policy \
  --repository-name ${ECR_REPO_NAME} \
  --region ${AWS_REGION} \
  --lifecycle-policy-text file://ecr-lifecycle-policy.json
```

### Step 2: Build and Push Docker Image

Build the Docker image and push to ECR:

```bash
# Navigate to project root
cd /path/to/multicam-infer

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REPO_URI}

# Build image for linux/amd64
docker build --platform linux/amd64 -t ${ECR_REPO_NAME}:latest .

# Tag image
docker tag ${ECR_REPO_NAME}:latest ${ECR_REPO_URI}:latest
docker tag ${ECR_REPO_NAME}:latest ${ECR_REPO_URI}:$(date +%Y%m%d-%H%M%S)

# Push image
docker push ${ECR_REPO_URI}:latest
docker push ${ECR_REPO_URI}:$(date +%Y%m%d-%H%M%S)

echo "Image pushed to ${ECR_REPO_URI}:latest"
```

**Or use the Makefile**:

```bash
IMG=${ECR_REPO_URI}:latest make docker-build
IMG=${ECR_REPO_URI}:latest make docker-push
```

### Step 3: Create IAM Roles

#### 3.1 Create IAM Task Role

The task role provides permissions for the application to access AWS services:

```bash
# Create trust policy
cat > task-role-trust-policy.json <<EOF
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

# Create IAM role
aws iam create-role \
  --role-name kvs-infer-task-role \
  --assume-role-policy-document file://task-role-trust-policy.json \
  --description "Task role for KVS Inference ECS tasks" \
  --tags Key=Project,Value=kvs-infer

# Substitute variables in policy template
sed -e "s/\${AWS_REGION}/${AWS_REGION}/g" \
    -e "s/\${AWS_ACCOUNT_ID}/${AWS_ACCOUNT_ID}/g" \
    -e "s/\${KVS_STREAM_PREFIX}/${KVS_STREAM_PREFIX}/g" \
    -e "s/\${KDS_STREAM_NAME}/${KDS_STREAM_NAME}/g" \
    -e "s/\${S3_BUCKET_NAME}/${S3_BUCKET_NAME}/g" \
    -e "s/\${S3_PREFIX}/${S3_PREFIX}/g" \
    -e "s/\${DYNAMODB_TABLE_NAME}/${DYNAMODB_TABLE_NAME}/g" \
    deployment/ecs/iam-task-role.json > /tmp/iam-task-role-resolved.json

# Attach inline policy
aws iam put-role-policy \
  --role-name kvs-infer-task-role \
  --policy-name kvs-infer-task-policy \
  --policy-document file:///tmp/iam-task-role-resolved.json

echo "Task role created: kvs-infer-task-role"
```

#### 3.2 Create IAM Execution Role

The execution role provides permissions for ECS to pull images and write logs:

```bash
# Create trust policy (same as above)
# Create IAM role
aws iam create-role \
  --role-name kvs-infer-execution-role \
  --assume-role-policy-document file://task-role-trust-policy.json \
  --description "Execution role for KVS Inference ECS tasks" \
  --tags Key=Project,Value=kvs-infer

# Substitute variables in execution policy
sed -e "s/\${AWS_REGION}/${AWS_REGION}/g" \
    -e "s/\${AWS_ACCOUNT_ID}/${AWS_ACCOUNT_ID}/g" \
    deployment/ecs/iam-execution-role.json > /tmp/iam-execution-role-resolved.json

# Attach inline policy
aws iam put-role-policy \
  --role-name kvs-infer-execution-role \
  --policy-name kvs-infer-execution-policy \
  --policy-document file:///tmp/iam-execution-role-resolved.json

echo "Execution role created: kvs-infer-execution-role"
```

### Step 4: Create ECS Cluster

Create an ECS cluster with GPU-enabled EC2 instances:

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name ${ECS_CLUSTER_NAME} \
  --region ${AWS_REGION} \
  --capacity-providers FARGATE FARGATE_SPOT \
  --settings name=containerInsights,value=enabled \
  --tags Key=Project,Value=kvs-infer Key=Environment,Value=production

echo "ECS cluster created: ${ECS_CLUSTER_NAME}"
```

#### 4.1 Create Launch Template for GPU Instances

```bash
cat > user-data.sh <<'EOF'
#!/bin/bash
# ECS GPU-optimized AMI user data

# Set ECS cluster name
echo ECS_CLUSTER=${ECS_CLUSTER_NAME} >> /etc/ecs/ecs.config
echo ECS_ENABLE_GPU_SUPPORT=true >> /etc/ecs/ecs.config
echo ECS_ENABLE_CONTAINER_METADATA=true >> /etc/ecs/ecs.config
echo ECS_ENABLE_TASK_IAM_ROLE=true >> /etc/ecs/ecs.config
echo ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST=true >> /etc/ecs/ecs.config

# Create directories for host volumes
mkdir -p /opt/kvs-infer/config
mkdir -p /opt/kvs-infer/models
mkdir -p /opt/kvs-infer/cache

# Set permissions
chmod 755 /opt/kvs-infer/config
chmod 755 /opt/kvs-infer/models
chmod 777 /opt/kvs-infer/cache

# Copy config from S3 (optional)
# aws s3 cp s3://${S3_BUCKET_NAME}/config/cameras.yaml /opt/kvs-infer/config/cameras.yaml

# Download models (optional - models should be in Docker image)
# aws s3 sync s3://${S3_BUCKET_NAME}/models/ /opt/kvs-infer/models/

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Start ECS agent
systemctl enable --now ecs
EOF

# Get latest ECS GPU-optimized AMI
ECS_GPU_AMI=$(aws ssm get-parameter \
  --name /aws/service/ecs/optimized-ami/amazon-linux-2/gpu/recommended/image_id \
  --region ${AWS_REGION} \
  --query 'Parameter.Value' \
  --output text)

echo "ECS GPU-optimized AMI: ${ECS_GPU_AMI}"

# Create launch template
aws ec2 create-launch-template \
  --launch-template-name kvs-infer-gpu-template \
  --version-description "Launch template for KVS Inference GPU instances" \
  --launch-template-data "{
    \"ImageId\": \"${ECS_GPU_AMI}\",
    \"InstanceType\": \"g4dn.xlarge\",
    \"IamInstanceProfile\": {
      \"Name\": \"ecsInstanceRole\"
    },
    \"SecurityGroupIds\": [\"${SECURITY_GROUP_ID}\"],
    \"UserData\": \"$(base64 -w0 user-data.sh)\",
    \"TagSpecifications\": [
      {
        \"ResourceType\": \"instance\",
        \"Tags\": [
          {\"Key\": \"Name\", \"Value\": \"kvs-infer-gpu-instance\"},
          {\"Key\": \"Project\", \"Value\": \"kvs-infer\"},
          {\"Key\": \"ManagedBy\", \"Value\": \"ecs\"}
        ]
      }
    ],
    \"MetadataOptions\": {
      \"HttpTokens\": \"required\",
      \"HttpPutResponseHopLimit\": 2
    }
  }"
```

#### 4.2 Create Auto Scaling Group

```bash
# Create Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name kvs-infer-gpu-asg \
  --launch-template LaunchTemplateName=kvs-infer-gpu-template,Version='$Latest' \
  --min-size 1 \
  --max-size 3 \
  --desired-capacity 1 \
  --vpc-zone-identifier "${PRIVATE_SUBNET_1},${PRIVATE_SUBNET_2}" \
  --health-check-type EC2 \
  --health-check-grace-period 300 \
  --tags \
    Key=Name,Value=kvs-infer-gpu-instance,PropagateAtLaunch=true \
    Key=Project,Value=kvs-infer,PropagateAtLaunch=true

# Create capacity provider
aws ecs create-capacity-provider \
  --name kvs-infer-gpu-capacity-provider \
  --auto-scaling-group-provider "autoScalingGroupArn=arn:aws:autoscaling:${AWS_REGION}:${AWS_ACCOUNT_ID}:autoScalingGroup:*:autoScalingGroupName/kvs-infer-gpu-asg,managedScaling={status=ENABLED,targetCapacity=100,minimumScalingStepSize=1,maximumScalingStepSize=1},managedTerminationProtection=DISABLED" \
  --tags Key=Project,Value=kvs-infer

# Associate capacity provider with cluster
aws ecs put-cluster-capacity-providers \
  --cluster ${ECS_CLUSTER_NAME} \
  --capacity-providers kvs-infer-gpu-capacity-provider \
  --default-capacity-provider-strategy \
    capacityProvider=kvs-infer-gpu-capacity-provider,weight=1,base=1
```

### Step 5: Register Task Definition

Prepare and register the ECS task definition:

```bash
# Substitute variables in task definition
sed -e "s/\${AWS_REGION}/${AWS_REGION}/g" \
    -e "s/\${AWS_ACCOUNT_ID}/${AWS_ACCOUNT_ID}/g" \
    deployment/ecs/ecs-task-def.json > /tmp/ecs-task-def-resolved.json

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file:///tmp/ecs-task-def-resolved.json \
  --region ${AWS_REGION}

echo "Task definition registered: kvs-infer-gpu"

# Verify task definition
aws ecs describe-task-definition \
  --task-definition kvs-infer-gpu \
  --region ${AWS_REGION} \
  --query 'taskDefinition.{Family:family,Revision:revision,Status:status}'
```

### Step 6: Create Security Group

Create a security group for the ECS tasks:

```bash
# Create security group
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --group-name kvs-infer-ecs-sg \
  --description "Security group for KVS Inference ECS tasks" \
  --vpc-id ${VPC_ID} \
  --region ${AWS_REGION} \
  --query 'GroupId' \
  --output text)

echo "Security group created: ${SECURITY_GROUP_ID}"

# Allow egress to HTTPS (443) for AWS services
aws ec2 authorize-security-group-egress \
  --group-id ${SECURITY_GROUP_ID} \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0 \
  --region ${AWS_REGION}

# Allow egress to HTTP (80) for package updates
aws ec2 authorize-security-group-egress \
  --group-id ${SECURITY_GROUP_ID} \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region ${AWS_REGION}

# Allow ingress for health checks (optional, if using ALB)
# aws ec2 authorize-security-group-ingress \
#   --group-id ${SECURITY_GROUP_ID} \
#   --protocol tcp \
#   --port 8080 \
#   --source-group ${ALB_SECURITY_GROUP_ID} \
#   --region ${AWS_REGION}

# Tag security group
aws ec2 create-tags \
  --resources ${SECURITY_GROUP_ID} \
  --tags Key=Name,Value=kvs-infer-ecs-sg Key=Project,Value=kvs-infer \
  --region ${AWS_REGION}
```

### Step 7: Create ECS Service

Create the ECS service to run tasks:

```bash
# Substitute variables in service definition
sed -e "s/\${ECS_CLUSTER_NAME}/${ECS_CLUSTER_NAME}/g" \
    -e "s/\${PRIVATE_SUBNET_1}/${PRIVATE_SUBNET_1}/g" \
    -e "s/\${PRIVATE_SUBNET_2}/${PRIVATE_SUBNET_2}/g" \
    -e "s/\${SECURITY_GROUP_ID}/${SECURITY_GROUP_ID}/g" \
    deployment/ecs/ecs-service.json > /tmp/ecs-service-resolved.json

# Create ECS service
aws ecs create-service \
  --cli-input-json file:///tmp/ecs-service-resolved.json \
  --region ${AWS_REGION}

echo "ECS service created: kvs-infer-service"

# Wait for service to become stable
aws ecs wait services-stable \
  --cluster ${ECS_CLUSTER_NAME} \
  --services kvs-infer-service \
  --region ${AWS_REGION}

echo "Service is stable and running"
```

### Step 8: Enable Container Insights

Container Insights is already enabled during cluster creation, but you can verify:

```bash
# Verify Container Insights is enabled
aws ecs describe-clusters \
  --clusters ${ECS_CLUSTER_NAME} \
  --region ${AWS_REGION} \
  --query 'clusters[0].settings[?name==`containerInsights`]'

# If not enabled, update cluster settings
aws ecs update-cluster-settings \
  --cluster ${ECS_CLUSTER_NAME} \
  --settings name=containerInsights,value=enabled \
  --region ${AWS_REGION}
```

---

## VPC Endpoints Configuration

VPC endpoints reduce NAT Gateway usage and improve security by keeping traffic within AWS network.

### Required VPC Endpoints

#### 1. ECR API Endpoint (Interface)
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id ${VPC_ID} \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.${AWS_REGION}.ecr.api \
  --subnet-ids ${PRIVATE_SUBNET_1} ${PRIVATE_SUBNET_2} \
  --security-group-ids ${SECURITY_GROUP_ID} \
  --private-dns-enabled \
  --region ${AWS_REGION} \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=ecr-api-endpoint},{Key=Project,Value=kvs-infer}]"
```

#### 2. ECR Docker Endpoint (Interface)
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id ${VPC_ID} \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.${AWS_REGION}.ecr.dkr \
  --subnet-ids ${PRIVATE_SUBNET_1} ${PRIVATE_SUBNET_2} \
  --security-group-ids ${SECURITY_GROUP_ID} \
  --private-dns-enabled \
  --region ${AWS_REGION} \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=ecr-dkr-endpoint},{Key=Project,Value=kvs-infer}]"
```

#### 3. S3 Gateway Endpoint
```bash
# Get route table IDs for private subnets
ROUTE_TABLE_IDS=$(aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values=${PRIVATE_SUBNET_1},${PRIVATE_SUBNET_2}" \
  --query 'RouteTables[*].RouteTableId' \
  --output text)

aws ec2 create-vpc-endpoint \
  --vpc-id ${VPC_ID} \
  --vpc-endpoint-type Gateway \
  --service-name com.amazonaws.${AWS_REGION}.s3 \
  --route-table-ids ${ROUTE_TABLE_IDS} \
  --region ${AWS_REGION} \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=s3-gateway-endpoint},{Key=Project,Value=kvs-infer}]"
```

#### 4. CloudWatch Logs Endpoint (Interface)
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id ${VPC_ID} \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.${AWS_REGION}.logs \
  --subnet-ids ${PRIVATE_SUBNET_1} ${PRIVATE_SUBNET_2} \
  --security-group-ids ${SECURITY_GROUP_ID} \
  --private-dns-enabled \
  --region ${AWS_REGION} \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=logs-endpoint},{Key=Project,Value=kvs-infer}]"
```

#### 5. Kinesis Data Streams Endpoint (Interface)
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id ${VPC_ID} \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.${AWS_REGION}.kinesis-streams \
  --subnet-ids ${PRIVATE_SUBNET_1} ${PRIVATE_SUBNET_2} \
  --security-group-ids ${SECURITY_GROUP_ID} \
  --private-dns-enabled \
  --region ${AWS_REGION} \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=kinesis-streams-endpoint},{Key=Project,Value=kvs-infer}]"
```

### Important Note: KVS Requires Internet Access

**Amazon Kinesis Video Streams does NOT support VPC endpoints** and requires Internet egress through:
- NAT Gateway (recommended for production)
- NAT Instance (cost-effective for development)
- Internet Gateway with public IPs (not recommended for private subnets)

Keep your NAT Gateway for KVS access, but VPC endpoints will handle all other AWS service traffic.

---

## Monitoring & Container Insights

### CloudWatch Container Insights

View metrics in CloudWatch Console:
1. Navigate to CloudWatch → Container Insights
2. Select **ECS Clusters** or **ECS Services**
3. Filter by cluster: `kvs-infer-cluster`

**Key Metrics to Monitor:**
- CPU Utilization
- Memory Utilization
- GPU Utilization (custom metrics)
- Network In/Out
- Task Count
- Running Task Count

### Application Metrics

Access Prometheus metrics from the container:

```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster ${ECS_CLUSTER_NAME} \
  --service-name kvs-infer-service \
  --region ${AWS_REGION} \
  --query 'taskArns[0]' \
  --output text)

# Get task details
aws ecs describe-tasks \
  --cluster ${ECS_CLUSTER_NAME} \
  --tasks ${TASK_ARN} \
  --region ${AWS_REGION} \
  --query 'tasks[0].containers[0].{Name:name,Status:lastStatus,Health:healthStatus}'

# Execute command in container (requires enableExecuteCommand=true)
aws ecs execute-command \
  --cluster ${ECS_CLUSTER_NAME} \
  --task ${TASK_ARN} \
  --container kvs-infer \
  --command "/bin/bash" \
  --interactive

# From inside container, check metrics
curl http://localhost:8080/healthz
curl http://localhost:8080/metrics
```

### CloudWatch Logs

View logs in CloudWatch Console:
1. Navigate to CloudWatch → Log groups
2. Select `/ecs/kvs-infer`
3. Filter logs by time range or search terms

**Or use AWS CLI:**

```bash
# List log streams
aws logs describe-log-streams \
  --log-group-name /ecs/kvs-infer \
  --order-by LastEventTime \
  --descending \
  --max-items 5 \
  --region ${AWS_REGION}

# Tail logs
aws logs tail /ecs/kvs-infer --follow --region ${AWS_REGION}
```

### CloudWatch Alarms

Create alarms for critical metrics:

```bash
# CPU Utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name kvs-infer-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ClusterName,Value=${ECS_CLUSTER_NAME} Name=ServiceName,Value=kvs-infer-service \
  --region ${AWS_REGION}

# Memory Utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name kvs-infer-high-memory \
  --alarm-description "Alert when memory exceeds 90%" \
  --metric-name MemoryUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 90 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ClusterName,Value=${ECS_CLUSTER_NAME} Name=ServiceName,Value=kvs-infer-service \
  --region ${AWS_REGION}

# Task count alarm (service health)
aws cloudwatch put-metric-alarm \
  --alarm-name kvs-infer-no-running-tasks \
  --alarm-description "Alert when no tasks are running" \
  --metric-name RunningTaskCount \
  --namespace ECS/ContainerInsights \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ClusterName,Value=${ECS_CLUSTER_NAME} Name=ServiceName,Value=kvs-infer-service \
  --region ${AWS_REGION}
```

---

## Troubleshooting

### Task Fails to Start

**Check task logs:**
```bash
TASK_ARN=$(aws ecs list-tasks --cluster ${ECS_CLUSTER_NAME} --region ${AWS_REGION} --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster ${ECS_CLUSTER_NAME} --tasks ${TASK_ARN} --region ${AWS_REGION}
```

**Common issues:**
- Image pull failed → Check ECR permissions and execution role
- Health check failed → Verify port 8080 is accessible and /healthz endpoint works
- GPU not available → Verify g4dn instance type and GPU resourceRequirements
- Volume mount failed → Check host paths exist on EC2 instance

### No GPU Detected

**Verify GPU support:**
```bash
# SSH to EC2 instance
# Check NVIDIA driver
nvidia-smi

# Check ECS agent config
cat /etc/ecs/ecs.config | grep GPU

# Check task definition
aws ecs describe-task-definition --task-definition kvs-infer-gpu --query 'taskDefinition.containerDefinitions[0].resourceRequirements'
```

### High NAT Gateway Costs

**Verify VPC endpoints:**
```bash
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=${VPC_ID}" --region ${AWS_REGION}
```

**Monitor data transfer:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/NATGateway \
  --metric-name BytesOutToDestination \
  --dimensions Name=NatGatewayId,Value=${NAT_GATEWAY_ID} \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region ${AWS_REGION}
```

### Service Won't Scale

**Check capacity provider:**
```bash
aws ecs describe-capacity-providers \
  --capacity-providers kvs-infer-gpu-capacity-provider \
  --region ${AWS_REGION}

# Check Auto Scaling Group
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names kvs-infer-gpu-asg \
  --region ${AWS_REGION}
```

---

## Cost Optimization

### Instance Type Selection

| Instance Type | vCPU | Memory | GPU | Price/hr* | Use Case |
|--------------|------|--------|-----|-----------|----------|
| g4dn.xlarge  | 4    | 16 GB  | 1   | ~$0.526   | Development/Single camera |
| g4dn.2xlarge | 8    | 32 GB  | 1   | ~$0.752   | Multiple cameras (2-4) |
| g4dn.4xlarge | 16   | 64 GB  | 1   | ~$1.204   | High throughput (5-8 cameras) |

*Prices vary by region. Use Spot instances for additional savings.

### Spot Instances

Save up to 70% with Spot instances:

```bash
# Update capacity provider to use Spot
aws ecs create-capacity-provider \
  --name kvs-infer-gpu-spot-capacity-provider \
  --auto-scaling-group-provider "autoScalingGroupArn=arn:aws:autoscaling:${AWS_REGION}:${AWS_ACCOUNT_ID}:autoScalingGroup:*:autoScalingGroupName/kvs-infer-gpu-spot-asg,managedScaling={status=ENABLED,targetCapacity=100}"

# Create Spot Auto Scaling Group (modify launch template to use Spot)
```

### VPC Endpoint Savings

Estimated monthly savings with VPC endpoints (vs NAT Gateway):

| Service | Monthly Data (GB) | NAT Cost | VPC Endpoint Cost | Savings |
|---------|-------------------|----------|-------------------|---------|
| ECR     | 50               | $2.25    | $7.20             | -$4.95* |
| S3      | 500              | $22.50   | $0 (Gateway)      | $22.50  |
| Logs    | 100              | $4.50    | $7.20             | -$2.70* |
| Kinesis | 200              | $9.00    | $7.20             | $1.80   |
| **Total** | 850 GB         | **$38.25** | **$21.60**      | **$16.65** |

*VPC endpoints have a fixed cost ($0.01/hr = $7.20/mo) but eliminate data transfer costs

**Note:** VPC endpoints are cost-effective when data transfer > 720 GB/month per endpoint.

### Monitoring Costs

- **Container Insights**: ~$0.30 per task per month
- **CloudWatch Logs**: $0.50 per GB ingested, $0.03 per GB stored
- **CloudWatch Metrics**: Custom metrics $0.30 per metric per month

---

## Summary

You've successfully deployed the KVS Inference application on ECS with GPU support! 🎉

**What you've set up:**
- ✅ ECR repository with image scanning
- ✅ Docker image built and pushed
- ✅ IAM roles with least-privilege access
- ✅ ECS cluster with GPU instances (g4dn.*)
- ✅ ECS service with 1 task running
- ✅ VPC endpoints for cost optimization
- ✅ Container Insights for monitoring
- ✅ CloudWatch alarms for critical metrics

**Next steps:**
1. Monitor task health in ECS console
2. View logs in CloudWatch
3. Set up CloudWatch dashboards
4. Configure auto-scaling based on load
5. Implement CI/CD pipeline for automated deployments

**Useful commands:**
```bash
# Service status
aws ecs describe-services --cluster ${ECS_CLUSTER_NAME} --services kvs-infer-service

# Task details
aws ecs list-tasks --cluster ${ECS_CLUSTER_NAME} --service-name kvs-infer-service

# View logs
aws logs tail /ecs/kvs-infer --follow

# Update service (new task definition)
aws ecs update-service --cluster ${ECS_CLUSTER_NAME} --service kvs-infer-service --force-new-deployment
```

For issues or questions, refer to the [Troubleshooting](#troubleshooting) section.
