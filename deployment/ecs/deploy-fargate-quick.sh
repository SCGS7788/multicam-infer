#!/bin/bash
# =============================================================================
# Quick Deploy on Fargate (No GPU - For Testing)
# =============================================================================
# Deploy immediately without waiting for GPU quota approval

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
AWS_REGION="ap-southeast-1"
AWS_ACCOUNT_ID="065693560492"
ECS_CLUSTER="vivid-fish-il1akc"
TASK_FAMILY="kvs-infer-fargate-test"
SERVICE_NAME="kvs-infer-fargate-test"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Quick Deploy on Fargate (No GPU)     ${NC}"
echo -e "${YELLOW}  For testing while waiting for quota  ${NC}"
echo -e "${YELLOW}========================================${NC}\n"

echo -e "${YELLOW}⚠️  Warning: This deployment runs WITHOUT GPU${NC}"
echo -e "${YELLOW}   - Inference will be slower (CPU only)${NC}"
echo -e "${YELLOW}   - Use this for testing purposes only${NC}"
echo ""

read -p "Continue with Fargate deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# =============================================================================
# Step 1: Create Fargate Task Definition
# =============================================================================
echo -e "${BLUE}[Step 1/4]${NC} Creating Fargate task definition..."

cat > /tmp/kvs-infer-fargate-test.json <<EOF
{
  "family": "${TASK_FAMILY}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "executionRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "kvs-infer",
      "image": "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/kvs-infer:latest",
      "essential": true,
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "${AWS_REGION}"
        },
        {
          "name": "ROBOFLOW_API_KEY",
          "value": "oBQpsjr25DqFZziUSMVN"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        },
        {
          "name": "PYTHONUNBUFFERED",
          "value": "1"
        },
        {
          "name": "DEVICE",
          "value": "cpu"
        },
        {
          "name": "CONFIG_PATH",
          "value": "/app/config/cameras.yaml"
        },
        {
          "name": "KVS_STREAM_PREFIX",
          "value": "stream"
        },
        {
          "name": "KDS_STREAM_NAME",
          "value": "kvs-detection-events"
        },
        {
          "name": "S3_BUCKET_NAME",
          "value": "kvs-inference-snapshots-065693560492"
        },
        {
          "name": "S3_PREFIX",
          "value": "snapshots"
        },
        {
          "name": "DYNAMODB_TABLE_NAME",
          "value": "kvs-inference-metadata"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/kvs-infer-fargate-test",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8080/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 120
      }
    }
  ]
}
EOF

aws ecs register-task-definition \
  --cli-input-json file:///tmp/kvs-infer-fargate-test.json \
  --region ${AWS_REGION} > /dev/null

echo -e "${GREEN}✓ Task definition registered${NC}\n"

# =============================================================================
# Step 2: Create or Update Service
# =============================================================================
echo -e "${BLUE}[Step 2/4]${NC} Creating Fargate service..."

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'services[0].serviceName' \
  --output text 2>/dev/null || echo "None")

if [ "$SERVICE_EXISTS" == "None" ] || [ -z "$SERVICE_EXISTS" ]; then
  # Create new service
  aws ecs create-service \
    --cluster ${ECS_CLUSTER} \
    --service-name ${SERVICE_NAME} \
    --task-definition ${TASK_FAMILY} \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={
        subnets=[subnet-0795923e22aeac56a,subnet-0a3db42ff65bdfbb1],
        securityGroups=[sg-0f521bbf1f080a90c],
        assignPublicIp=DISABLED
    }" \
    --enable-execute-command \
    --region ${AWS_REGION} > /dev/null
  
  echo -e "${GREEN}✓ Service created${NC}"
else
  # Update existing service
  aws ecs update-service \
    --cluster ${ECS_CLUSTER} \
    --service ${SERVICE_NAME} \
    --task-definition ${TASK_FAMILY} \
    --desired-count 1 \
    --force-new-deployment \
    --region ${AWS_REGION} > /dev/null
  
  echo -e "${GREEN}✓ Service updated${NC}"
fi

echo ""

# =============================================================================
# Step 3: Wait for Service
# =============================================================================
echo -e "${BLUE}[Step 3/4]${NC} Waiting for service to start (2-3 minutes)..."

for i in {1..60}; do
  RUNNING_COUNT=$(aws ecs describe-services \
    --cluster ${ECS_CLUSTER} \
    --services ${SERVICE_NAME} \
    --region ${AWS_REGION} \
    --query 'services[0].runningCount' \
    --output text)
  
  if [ "$RUNNING_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Service is running${NC}"
    break
  fi
  
  echo -n "."
  sleep 3
done

echo ""

# =============================================================================
# Step 4: Get Status
# =============================================================================
echo -e "${BLUE}[Step 4/4]${NC} Getting service status..."

TASK_ARN=$(aws ecs list-tasks \
  --cluster ${ECS_CLUSTER} \
  --service-name ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'taskArns[0]' \
  --output text)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Fargate Deployment Complete! 🎉      ${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${GREEN}Service Status:${NC}"
aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'services[0].{Running: runningCount, Desired: desiredCount, Status: status}' \
  --output table

echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo ""
echo "View logs:"
echo "  aws logs tail /ecs/kvs-infer-fargate-test --follow --region ${AWS_REGION}"
echo ""
echo "View task details:"
echo "  aws ecs describe-tasks --cluster ${ECS_CLUSTER} --tasks ${TASK_ARN}"
echo ""
echo "Stop this test service (when done):"
echo "  aws ecs update-service --cluster ${ECS_CLUSTER} --service ${SERVICE_NAME} --desired-count 0"
echo ""
echo -e "${YELLOW}Note: This is running on CPU only (no GPU)${NC}"
echo -e "${YELLOW}      Switch to GPU deployment once quota is approved${NC}"
echo ""
