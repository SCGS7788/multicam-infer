#!/bin/bash
# =============================================================================
# Check vCPU Quota Status
# =============================================================================
# Monitors the status of vCPU quota request for G instances

set -e

AWS_REGION="ap-southeast-1"
QUOTA_CODE="L-DB2E81BA"

echo "=== Checking vCPU Quota Status for G instances ==="
echo ""

# Check current quota
echo "📊 Current Quota:"
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code ${QUOTA_CODE} \
  --region ${AWS_REGION} \
  --query '{QuotaName: Quota.QuotaName, CurrentValue: Quota.Value, Adjustable: Quota.Adjustable}' \
  --output table

echo ""

# Check quota request history
echo "📋 Recent Quota Change Requests:"
aws service-quotas list-requested-service-quota-change-history \
  --service-code ec2 \
  --region ${AWS_REGION} \
  --query 'RequestedQuotas[?QuotaCode==`'${QUOTA_CODE}'`] | [0:3]' \
  --output table

echo ""

# Get current quota value
CURRENT_VALUE=$(aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code ${QUOTA_CODE} \
  --region ${AWS_REGION} \
  --query 'Quota.Value' \
  --output text)

if (( $(echo "$CURRENT_VALUE > 0" | bc -l) )); then
  echo "✅ Quota is approved! Current value: ${CURRENT_VALUE} vCPUs"
  echo ""
  echo "You can now run the deployment script:"
  echo "  ./deployment/ecs/deploy-after-quota.sh"
else
  echo "⏳ Quota is still pending approval (current value: ${CURRENT_VALUE})"
  echo ""
  echo "Typical approval time: 15-60 minutes"
  echo "Re-run this script to check status:"
  echo "  ./deployment/ecs/check-quota-status.sh"
fi

echo ""
