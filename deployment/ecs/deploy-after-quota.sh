#!/bin/bash
# =============================================================================
# ECS GPU Deployment Script - After Quota Approval
# =============================================================================
# 
# Prerequisites:
# - vCPU quota approved for G instances
# - IAM roles created
# - VPC endpoints created
# - Docker image pushed to ECR
#
# Usage:
#   ./deploy-after-quota.sh

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
ASG_NAME="Infra-ECS-Cluster-vivid-fish-il1akc-12b36e69-ECSAutoScalingGroup-8IZZx43LhJ3N"
TASK_FAMILY="kvs-infer-gpu"
SERVICE_NAME="kvs-infer-gpu-service"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ECS GPU Deployment - After Quota     ${NC}"
echo -e "${GREEN}========================================${NC}\n"

# =============================================================================
# Step 1: Check vCPU Quota
# =============================================================================
echo -e "${BLUE}[Step 1/7]${NC} Checking vCPU quota..."

QUOTA_VALUE=$(aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-DB2E81BA \
  --region ${AWS_REGION} \
  --query 'Quota.Value' \
  --output text)

echo "Current G instance vCPU quota: ${QUOTA_VALUE}"

if (( $(echo "$QUOTA_VALUE <= 0" | bc -l) )); then
  echo -e "${RED}ERROR: vCPU quota is still 0. Please wait for approval.${NC}"
  echo "Check status:"
  echo "  aws service-quotas list-requested-service-quota-change-history \\"
  echo "    --service-code ec2 \\"
  echo "    --region ${AWS_REGION} \\"
  echo "    --query 'RequestedQuotas[?QuotaCode==\`L-DB2E81BA\`] | [0]'"
  exit 1
fi

echo -e "${GREEN}✓ vCPU quota approved: ${QUOTA_VALUE} vCPUs${NC}\n"

# =============================================================================
# Step 2: Register Task Definition
# =============================================================================
echo -e "${BLUE}[Step 2/7]${NC} Registering task definition..."

aws ecs register-task-definition \
  --cli-input-json file://deployment/ecs/task-definition-gpu-updated.json \
  --region ${AWS_REGION} > /dev/null

TASK_REVISION=$(aws ecs describe-task-definition \
  --task-definition ${TASK_FAMILY} \
  --region ${AWS_REGION} \
  --query 'taskDefinition.revision' \
  --output text)

echo -e "${GREEN}✓ Task definition registered: ${TASK_FAMILY}:${TASK_REVISION}${NC}\n"

# =============================================================================
# Step 3: Scale Up Auto Scaling Group
# =============================================================================
echo -e "${BLUE}[Step 3/7]${NC} Scaling up Auto Scaling Group..."

# Reset to 0 first
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name "${ASG_NAME}" \
  --desired-capacity 0 \
  --region ${AWS_REGION}

echo "Waiting 10 seconds..."
sleep 10

# Scale up to 1
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name "${ASG_NAME}" \
  --desired-capacity 1 \
  --region ${AWS_REGION}

echo -e "${GREEN}✓ Auto Scaling Group desired capacity set to 1${NC}\n"

# =============================================================================
# Step 4: Wait for EC2 Instance
# =============================================================================
echo -e "${BLUE}[Step 4/7]${NC} Waiting for EC2 instance to launch (2-3 minutes)..."

for i in {1..60}; do
  INSTANCE_COUNT=$(aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names "${ASG_NAME}" \
    --region ${AWS_REGION} \
    --query 'AutoScalingGroups[0].Instances | length(@)' \
    --output text)
  
  if [ "$INSTANCE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ EC2 instance launched${NC}"
    break
  fi
  
  echo -n "."
  sleep 5
done

if [ "$INSTANCE_COUNT" -eq 0 ]; then
  echo -e "\n${RED}ERROR: EC2 instance failed to launch${NC}"
  echo "Check scaling activities:"
  echo "  aws autoscaling describe-scaling-activities \\"
  echo "    --auto-scaling-group-name \"${ASG_NAME}\" \\"
  echo "    --max-records 3 --region ${AWS_REGION}"
  exit 1
fi

echo ""

# =============================================================================
# Step 5: Wait for Container Instance Registration
# =============================================================================
echo -e "${BLUE}[Step 5/7]${NC} Waiting for container instance registration..."

for i in {1..60}; do
  CONTAINER_INSTANCES=$(aws ecs list-container-instances \
    --cluster ${ECS_CLUSTER} \
    --region ${AWS_REGION} \
    --query 'length(containerInstanceArns)' \
    --output text)
  
  if [ "$CONTAINER_INSTANCES" -gt 0 ]; then
    echo -e "${GREEN}✓ Container instance registered with ECS${NC}"
    break
  fi
  
  echo -n "."
  sleep 5
done

if [ "$CONTAINER_INSTANCES" -eq 0 ]; then
  echo -e "\n${RED}ERROR: Container instance not registered with ECS${NC}"
  echo "Check EC2 user data logs: /var/log/ecs/ecs-init.log"
  exit 1
fi

echo ""

# =============================================================================
# Step 6: Create or Update ECS Service
# =============================================================================
echo -e "${BLUE}[Step 6/7]${NC} Creating/Updating ECS service..."

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'services[0].serviceName' \
  --output text 2>/dev/null || echo "None")

if [ "$SERVICE_EXISTS" == "None" ] || [ -z "$SERVICE_EXISTS" ]; then
  # Create new service
  echo "Creating new service..."
  
  aws ecs create-service \
    --cluster ${ECS_CLUSTER} \
    --service-name ${SERVICE_NAME} \
    --task-definition ${TASK_FAMILY}:${TASK_REVISION} \
    --desired-count 1 \
    --launch-type EC2 \
    --network-configuration "awsvpcConfiguration={
        subnets=[subnet-0795923e22aeac56a,subnet-0a3db42ff65bdfbb1],
        securityGroups=[sg-0f521bbf1f080a90c],
        assignPublicIp=DISABLED
    }" \
    --enable-execute-command \
    --region ${AWS_REGION} > /dev/null
  
  echo -e "${GREEN}✓ Service created: ${SERVICE_NAME}${NC}"
else
  # Update existing service
  echo "Updating existing service..."
  
  aws ecs update-service \
    --cluster ${ECS_CLUSTER} \
    --service ${SERVICE_NAME} \
    --task-definition ${TASK_FAMILY}:${TASK_REVISION} \
    --desired-count 1 \
    --force-new-deployment \
    --region ${AWS_REGION} > /dev/null
  
  echo -e "${GREEN}✓ Service updated: ${SERVICE_NAME}${NC}"
fi

echo ""

# =============================================================================
# Step 7: Wait for Service Stability
# =============================================================================
echo -e "${BLUE}[Step 7/7]${NC} Waiting for service to become stable (2-5 minutes)..."

aws ecs wait services-stable \
  --cluster ${ECS_CLUSTER} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} 2>/dev/null || echo "Timeout reached, but service may still be starting..."

echo ""

# =============================================================================
# Deployment Complete
# =============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete! 🎉             ${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Get service status
RUNNING_COUNT=$(aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'services[0].runningCount' \
  --output text)

DESIRED_COUNT=$(aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'services[0].desiredCount' \
  --output text)

echo -e "${GREEN}Service Status:${NC}"
echo "  Running tasks: ${RUNNING_COUNT}/${DESIRED_COUNT}"
echo ""

# Get task details
TASK_ARN=$(aws ecs list-tasks \
  --cluster ${ECS_CLUSTER} \
  --service-name ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'taskArns[0]' \
  --output text)

if [ "$TASK_ARN" != "None" ] && [ -n "$TASK_ARN" ]; then
  echo -e "${GREEN}Task ARN:${NC}"
  echo "  ${TASK_ARN}"
  echo ""
fi

# Useful commands
echo -e "${BLUE}Useful Commands:${NC}"
echo ""
echo "View service events:"
echo "  aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${SERVICE_NAME} --query 'services[0].events[:5]'"
echo ""
echo "View logs:"
echo "  aws logs tail /ecs/kvs-infer-gpu --follow --region ${AWS_REGION}"
echo ""
echo "View task details:"
echo "  aws ecs describe-tasks --cluster ${ECS_CLUSTER} --tasks ${TASK_ARN}"
echo ""
echo "Access container shell (if enabled):"
echo "  aws ecs execute-command --cluster ${ECS_CLUSTER} --task ${TASK_ARN} --container kvs-infer --command \"/bin/bash\" --interactive"
echo ""
echo "Health check:"
echo "  # Get task private IP first, then:"
echo "  curl http://<TASK_IP>:8080/health"
echo ""
