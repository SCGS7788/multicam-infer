#!/bin/bash
# =============================================================================
# Auto-Monitor and Deploy when Quota is Approved
# =============================================================================
# This script will continuously check quota status and automatically deploy
# when the quota is approved

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

AWS_REGION="ap-southeast-1"
QUOTA_CODE="L-DB2E81BA"
CHECK_INTERVAL=60  # Check every 60 seconds
MAX_WAIT=3600      # Maximum wait time: 1 hour

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Auto GPU Deployment Monitor          ${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "⏰ Monitoring quota status..."
echo "   Will check every ${CHECK_INTERVAL} seconds"
echo "   Maximum wait time: $(($MAX_WAIT / 60)) minutes"
echo ""

START_TIME=$(date +%s)
ATTEMPT=0

while true; do
  ATTEMPT=$((ATTEMPT + 1))
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  # Check if max wait time exceeded
  if [ $ELAPSED -gt $MAX_WAIT ]; then
    echo -e "\n${RED}⏱️  Maximum wait time exceeded (1 hour)${NC}"
    echo "Quota may need manual intervention. Check AWS Support case."
    exit 1
  fi
  
  # Display current attempt
  MINUTES_ELAPSED=$((ELAPSED / 60))
  echo -e "${BLUE}[Attempt $ATTEMPT - ${MINUTES_ELAPSED}m elapsed]${NC} Checking quota status..."
  
  # Get current quota value
  QUOTA_VALUE=$(aws service-quotas get-service-quota \
    --service-code ec2 \
    --quota-code ${QUOTA_CODE} \
    --region ${AWS_REGION} \
    --query 'Quota.Value' \
    --output text 2>/dev/null || echo "0")
  
  # Check if quota is approved
  if (( $(echo "$QUOTA_VALUE > 0" | bc -l) )); then
    echo -e "\n${GREEN}🎉 Quota Approved! Current value: ${QUOTA_VALUE} vCPUs${NC}\n"
    
    # Run deployment script
    echo -e "${GREEN}Starting GPU deployment...${NC}\n"
    
    if [ -f "./deployment/ecs/deploy-after-quota.sh" ]; then
      ./deployment/ecs/deploy-after-quota.sh
      exit 0
    else
      echo -e "${RED}Error: deploy-after-quota.sh not found${NC}"
      exit 1
    fi
  else
    # Get request status
    STATUS=$(aws service-quotas list-requested-service-quota-change-history \
      --service-code ec2 \
      --region ${AWS_REGION} \
      --query 'RequestedQuotas[?QuotaCode==`'${QUOTA_CODE}'`] | [0].Status' \
      --output text 2>/dev/null || echo "UNKNOWN")
    
    echo "   Status: ${STATUS} | Current Value: ${QUOTA_VALUE} vCPUs"
    echo "   ⏳ Waiting ${CHECK_INTERVAL} seconds before next check..."
    sleep $CHECK_INTERVAL
  fi
done
