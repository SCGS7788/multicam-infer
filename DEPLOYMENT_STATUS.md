# ✅ Deployment Status - kvs-infer on AWS

## สถานะปัจจุบัน

### ✅ สำเร็จแล้ว:

1. **Docker Image Built** ✅
   - Image: `kvs-infer:latest`
   - Size: 14.8GB
   - Includes: Roboflow Gun Detector, PyTorch, CUDA support

2. **ECR Repository Created** ✅
   - Repository URI: `065693560492.dkr.ecr.ap-southeast-1.amazonaws.com/kvs-infer`
   - Region: ap-southeast-1
   - Image Scanning: Enabled

3. **Image Pushed to ECR** ✅
   - Digest: `sha256:a1b5a1ed649a15187ca8df46ccbbf403f93339f3f5bc732cfa526ea9aafbaca5`

4. **ECS Cluster Created** ✅
   - Cluster Name: `kvs-infer-cluster`
   - Region: ap-southeast-1
   - Container Insights: Enabled

---

## 🎯 ขั้นตอนถัดไป

### Option 1: Deploy บน Fargate (ไม่ต้องจัดการ Server)

**ข้อดี:** ไม่ต้องจัดการ EC2 instances
**ข้อเสีย:** ไม่รองรับ GPU

```bash
# 1. Register task definition (Fargate compatible)
aws ecs register-task-definition \
    --cli-input-json file://deployment/ecs/task-definition-fargate.json

# 2. Create service
aws ecs create-service \
    --cluster kvs-infer-cluster \
    --service-name kvs-infer-service \
    --task-definition kvs-infer-task \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={
        subnets=[subnet-xxxxx,subnet-yyyyy],
        securityGroups=[sg-xxxxx],
        assignPublicIp=ENABLED
    }"
```

### Option 2: Deploy บน EC2 with GPU (แนะนำสำหรับ production)

**ข้อดี:** รองรับ GPU, performance ดีกว่า
**ข้อเสีย:** ต้องจัดการ EC2 instances

#### Step 1: สร้าง EC2 Launch Template

```bash
# สร้าง launch template สำหรับ ECS-optimized GPU instances
aws ec2 create-launch-template \
    --launch-template-name kvs-infer-gpu-template \
    --launch-template-data '{
        "ImageId": "ami-0c2e0ea4b8b8b9b0c",
        "InstanceType": "g4dn.xlarge",
        "IamInstanceProfile": {
            "Name": "ecsInstanceRole"
        },
        "SecurityGroupIds": ["sg-xxxxx"],
        "UserData": "IyEvYmluL2Jhc2gKZWNobyBFQ1NfQ0xVU1RFUj1rdnMtaW5mZXItY2x1c3RlciA+PiAvZXRjL2Vjcy9lY3MuY29uZmlnCmVjaG8gRUNTX0VOQUJMRV9HUFVfU1VQUE9SVD10cnVlID4+IC9ldGMvZWNzL2Vjcy5jb25maWc="
    }'
```

#### Step 2: Create Auto Scaling Group

```bash
aws autoscaling create-auto-scaling-group \
    --auto-scaling-group-name kvs-infer-asg \
    --launch-template LaunchTemplateName=kvs-infer-gpu-template \
    --min-size 1 \
    --max-size 2 \
    --desired-capacity 1 \
    --vpc-zone-identifier "subnet-xxxxx,subnet-yyyyy"
```

#### Step 3: Register EC2 Capacity Provider

```bash
aws ecs create-capacity-provider \
    --name kvs-infer-gpu-provider \
    --auto-scaling-group-provider "autoScalingGroupArn=arn:aws:autoscaling:...,
        managedScaling={status=ENABLED,targetCapacity=100},
        managedTerminationProtection=DISABLED"

aws ecs put-cluster-capacity-providers \
    --cluster kvs-infer-cluster \
    --capacity-providers kvs-infer-gpu-provider \
    --default-capacity-provider-strategy capacityProvider=kvs-infer-gpu-provider,weight=1
```

#### Step 4: Register Task Definition

```bash
aws ecs register-task-definition \
    --cli-input-json file://deployment/ecs/task-definition.json
```

#### Step 5: Create Service

```bash
aws ecs create-service \
    --cluster kvs-infer-cluster \
    --service-name kvs-infer-service \
    --task-definition kvs-infer-task \
    --desired-count 1 \
    --capacity-provider-strategy capacityProvider=kvs-infer-gpu-provider,weight=1 \
    --network-configuration "awsvpcConfiguration={
        subnets=[subnet-xxxxx,subnet-yyyyy],
        securityGroups=[sg-xxxxx]
    }"
```

---

## 📋 ต้องเตรียมก่อน Deploy

### 1. **IAM Roles**

#### ecsTaskExecutionRole (สำหรับ pull image และ logs)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:CreateLogGroup"
      ],
      "Resource": "*"
    }
  ]
}
```

#### ecsTaskRole (สำหรับ access AWS services)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesisvideo:GetDataEndpoint",
        "kinesisvideo:GetHLSStreamingSessionURL",
        "kinesisvideo:DescribeStream",
        "kinesis:PutRecord",
        "kinesis:PutRecords",
        "s3:PutObject",
        "s3:GetObject",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "*"
    }
  ]
}
```

#### ecsInstanceRole (สำหรับ EC2 instances)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:CreateCluster",
        "ecs:RegisterContainerInstance",
        "ecs:DeregisterContainerInstance",
        "ecs:DiscoverPollEndpoint",
        "ecs:Submit*",
        "ecs:Poll",
        "ecs:StartTelemetrySession",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. **VPC และ Subnets**

```bash
# ดู VPCs
aws ec2 describe-vpcs --region ap-southeast-1 --output table

# ดู Subnets
aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=vpc-xxxxx" \
    --region ap-southeast-1 \
    --output table

# ต้องมีอย่างน้อย 2 subnets ใน different AZs
```

### 3. **Security Groups**

```bash
# สร้าง security group
aws ec2 create-security-group \
    --group-name kvs-infer-sg \
    --description "Security group for kvs-infer ECS tasks" \
    --vpc-id vpc-xxxxx

# เพิ่ม inbound rules (สำหรับ health check)
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxx \
    --protocol tcp \
    --port 8080 \
    --cidr 10.0.0.0/8

# เพิ่ม outbound rules (all traffic)
aws ec2 authorize-security-group-egress \
    --group-id sg-xxxxx \
    --protocol all \
    --cidr 0.0.0.0/0
```

---

## 🔍 ตรวจสอบและ Monitor

### ดูสถานะ Deployment

```bash
# ดู ECS services
aws ecs describe-services \
    --cluster kvs-infer-cluster \
    --services kvs-infer-service

# ดู tasks ที่กำลังรัน
aws ecs list-tasks \
    --cluster kvs-infer-cluster

# ดู task details
aws ecs describe-tasks \
    --cluster kvs-infer-cluster \
    --tasks <task-id>
```

### ดู Logs

```bash
# Real-time logs
aws logs tail /ecs/kvs-infer --follow

# Filter logs
aws logs filter-log-events \
    --log-group-name /ecs/kvs-infer \
    --filter-pattern "ERROR"
```

### Health Check

```bash
# Get task private IP
TASK_IP=$(aws ecs describe-tasks \
    --cluster kvs-infer-cluster \
    --tasks <task-id> \
    --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
    --output text)

# Test health endpoint (from within VPC)
curl http://$TASK_IP:8080/healthz
```

---

## 💰 Cost Estimation

### Fargate
- **vCPU:** 2
- **Memory:** 4 GB
- **Cost:** ~$0.10/hour = ~$75/month

### EC2 GPU (g4dn.xlarge)
- **Instance:** $0.526/hour
- **Storage:** $0.10/GB/month (50 GB EBS)
- **Total:** ~$390/month

### Additional Costs
- **ECR Storage:** $0.10/GB/month (~$1.50 for 15GB image)
- **Data Transfer:** Variable
- **CloudWatch Logs:** $0.50/GB ingested + $0.03/GB stored
- **Kinesis:** $0.015/shard/hour + $0.014/million PUT units

---

## ⚠️ Important Notes

1. **GPU Support:** 
   - Fargate ไม่รองรับ GPU
   - ต้องใช้ EC2 instances ถ้าต้องการ GPU

2. **Networking:**
   - Tasks ใน private subnet ต้องมี NAT Gateway สำหรับ access internet
   - หรือใช้ VPC Endpoints สำหรับ AWS services

3. **Config File:**
   - ต้อง mount config/cameras.yaml เข้า container
   - Option 1: ใช้ EFS
   - Option 2: ใช้ host path (EC2 only)
   - Option 3: Bake into image

4. **Secrets:**
   - ใช้ AWS Secrets Manager หรือ SSM Parameter Store
   - ไม่ควรใส่ API keys ใน task definition

---

## 🚀 Quick Start Commands

```bash
# ตั้งค่า environment variables
export AWS_REGION=ap-southeast-1
export CLUSTER_NAME=kvs-infer-cluster
export VPC_ID=vpc-xxxxx
export SUBNET_1=subnet-xxxxx
export SUBNET_2=subnet-yyyyy
export SG_ID=sg-xxxxx

# Register task definition
aws ecs register-task-definition \
    --cli-input-json file://deployment/ecs/task-definition.json

# Create service (Fargate)
aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name kvs-infer-service \
    --task-definition kvs-infer-task \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={
        subnets=[$SUBNET_1,$SUBNET_2],
        securityGroups=[$SG_ID],
        assignPublicIp=ENABLED
    }"

# Watch deployment
watch -n 5 'aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services kvs-infer-service \
    --query "services[0].events[0:5]" \
    --output table'
```

---

## 📞 Next Steps

1. เลือก deployment option (Fargate หรือ EC2 GPU)
2. เตรียม VPC, Subnets, Security Groups
3. สร้าง IAM Roles
4. Register task definition
5. Create ECS service
6. Monitor และ test system

บอกฉันเมื่อพร้อม deploy หรือต้องการความช่วยเหลือในขั้นตอนใดๆ! 🎯
