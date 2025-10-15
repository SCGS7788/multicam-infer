# 🚀 ECS GPU Deployment Guide

## 📊 สถานะปัจจุบัน

### ✅ สิ่งที่เตรียมไว้แล้ว:

1. **IAM Roles** ✅
   - `ecsTaskExecutionRole` - สำหรับ pull Docker images และส่ง logs
   - `ecsTaskRole` - สำหรับเข้าถึง AWS services (KVS, KDS, S3, DynamoDB)

2. **VPC Endpoints** ✅
   - `ecr.api` - สำหรับ ECR API calls
   - `ecr.dkr` - สำหรับ pull Docker images
   - `logs` - สำหรับ CloudWatch Logs
   - `kinesis-streams` - สำหรับ Kinesis Data Streams
   - `s3` (Gateway) - สำหรับ S3 access
   - `dynamodb` (Gateway) - สำหรับ DynamoDB access

3. **AWS Resources** ✅
   - ECS Cluster: `vivid-fish-il1akc`
   - ECR Repository: `kvs-infer` (image pushed)
   - S3 Bucket: `kvs-inference-snapshots-065693560492`
   - Kinesis Data Stream: `kvs-detection-events`
   - DynamoDB Table: `kvs-inference-metadata`
   - Kinesis Video Streams: `stream-C01` to `stream-C22`

4. **Task Definition** ✅
   - File: `task-definition-gpu-updated.json`
   - Instance Type: g4dn.xlarge (4 vCPUs, 16GB RAM, 1x NVIDIA T4 GPU)
   - GPU Support: Enabled with device mappings
   - Memory: 16GB (reservation: 12GB)
   - Health Check: `/health` endpoint

5. **Configuration Files** ✅
   - `cameras-ecs.yaml` - Camera configuration for 3 streams
   - `.env` - Environment variables

6. **Deployment Scripts** ✅
   - `deploy-after-quota.sh` - Complete deployment automation
   - `check-quota-status.sh` - Check quota approval status

### ⏳ รอการอนุมัติ:

1. **vCPU Quota Request** ⏳
   - Service: Amazon EC2
   - Quota: Running On-Demand G and VT instances
   - Current Value: 0 vCPUs
   - Requested Value: 8 vCPUs
   - Status: **CASE_OPENED** (รอการอนุมัติ)
   - Case ID: 176050925100155
   - เวลาที่ส่งคำขอ: 2025-10-15 13:20:04

---

## 🎯 ขั้นตอนการ Deploy

### Step 1: ตรวจสอบสถานะ Quota

```bash
cd /Users/pradyapadsee/Documents/aws/multicam-infer
./deployment/ecs/check-quota-status.sh
```

รอจนกว่า **CurrentValue > 0** (โดยปกติใช้เวลา 15-60 นาที)

### Step 2: Deploy บน ECS

เมื่อ quota ได้รับอนุมัติแล้ว:

```bash
./deployment/ecs/deploy-after-quota.sh
```

Script นี้จะ:
1. ✅ ตรวจสอบ vCPU quota
2. ✅ Register task definition
3. ✅ Scale up Auto Scaling Group (0 → 1 instance)
4. ✅ รอ EC2 instance เริ่มทำงาน (2-3 นาที)
5. ✅ รอ container instance ลงทะเบียนกับ ECS
6. ✅ สร้าง/อัปเดต ECS service
7. ✅ รอ service มีเสถียรภาพ

### Step 3: ตรวจสอบสถานะ Deployment

```bash
# ดู service status
aws ecs describe-services \
  --cluster vivid-fish-il1akc \
  --services kvs-infer-gpu-service \
  --region ap-southeast-1 \
  --query 'services[0].{runningCount: runningCount, desiredCount: desiredCount, status: status}'

# ดู tasks
aws ecs list-tasks \
  --cluster vivid-fish-il1akc \
  --service-name kvs-infer-gpu-service \
  --region ap-southeast-1

# ดู logs
aws logs tail /ecs/kvs-infer-gpu --follow --region ap-southeast-1
```

---

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   VPC (Private Subnets)                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │       ECS Cluster: vivid-fish-il1akc                       │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────┐                 │ │
│  │  │  ECS Service: kvs-infer-gpu-service  │                 │ │
│  │  │                                       │                 │ │
│  │  │  Task: kvs-infer-gpu                 │                 │ │
│  │  │  - Container: kvs-infer              │                 │ │
│  │  │  - GPU: 1x NVIDIA T4                 │                 │ │
│  │  │  - CPU: 4 vCPUs                      │                 │ │
│  │  │  - Memory: 16 GB                     │                 │ │
│  │  │  - Port: 8080 (health/metrics)       │                 │ │
│  │  └──────────────────────────────────────┘                 │ │
│  │                                                            │ │
│  │  EC2 Instance: g4dn.xlarge                                │ │
│  │  - AMI: ECS-Optimized GPU                                 │ │
│  │  - Subnets: Private (AZ a, b)                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              VPC Endpoints (PrivateLink)                   │ │
│  │  ✓ ecr.api, ecr.dkr                                        │ │
│  │  ✓ logs                                                    │ │
│  │  ✓ kinesis-streams                                         │ │
│  │  ✓ s3 (Gateway)                                            │ │
│  │  ✓ dynamodb (Gateway)                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────────┐
                    │  AWS Services    │
                    ├──────────────────┤
                    │ KVS (22 streams) │
                    │ KDS Events       │
                    │ S3 Snapshots     │
                    │ DynamoDB Metadata│
                    └──────────────────┘
```

---

## 🔧 Configuration Details

### Task Definition Highlights

- **Family**: `kvs-infer-gpu`
- **Launch Type**: EC2
- **CPU**: 4096 (4 vCPUs)
- **Memory**: 16384 MB (16 GB)
- **GPU**: 1x NVIDIA T4 (via resourceRequirements)
- **Placement Constraint**: `attribute:ecs.instance-type =~ g4dn.*`

### Environment Variables

```bash
AWS_REGION=ap-southeast-1
ROBOFLOW_API_KEY=oBQpsjr25DqFZziUSMVN
LOG_LEVEL=INFO
CUDA_VISIBLE_DEVICES=0
KVS_STREAM_PREFIX=stream
KDS_STREAM_NAME=kvs-detection-events
S3_BUCKET_NAME=kvs-inference-snapshots-065693560492
DYNAMODB_TABLE_NAME=kvs-inference-metadata
```

### Camera Configuration

ไฟล์: `deployment/ecs/cameras-ecs.yaml`

- **Streams**: stream-C01, stream-C02, stream-C03
- **Detector**: Roboflow Gun Detection (cctv-gun-detection/2)
- **FPS Target**: 2 frames/second
- **Confidence Threshold**: 0.5
- **Mode**: HLS (no retention required)

---

## 🚨 Troubleshooting

### 1. Quota ยังไม่อนุมัติ

```bash
# ตรวจสอบสถานะ
./deployment/ecs/check-quota-status.sh

# ถ้ารอนานเกิน 1 ชั่วโมง ติดต่อ AWS Support
```

### 2. EC2 Instance ไม่เริ่มทำงาน

```bash
# ดู scaling activities
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name "Infra-ECS-Cluster-vivid-fish-il1akc-12b36e69-ECSAutoScalingGroup-8IZZx43LhJ3N" \
  --max-records 5 \
  --region ap-southeast-1
```

### 3. Container Instance ไม่ลงทะเบียน

```bash
# ตรวจสอบ EC2 instance
aws ec2 describe-instances \
  --filters "Name=tag:aws:autoscaling:groupName,Values=Infra-ECS-Cluster-vivid-fish-il1akc-12b36e69-ECSAutoScalingGroup-8IZZx43LhJ3N" \
  --region ap-southeast-1

# SSH เข้า instance (ถ้ามี keypair)
# ดู logs: /var/log/ecs/ecs-init.log
```

### 4. Task ไม่เริ่มทำงาน

```bash
# ดู task events
aws ecs describe-tasks \
  --cluster vivid-fish-il1akc \
  --tasks <TASK_ARN> \
  --region ap-southeast-1

# ดู logs
aws logs tail /ecs/kvs-infer-gpu --follow --region ap-southeast-1
```

### 5. Application Errors

```bash
# ดู container logs
aws logs get-log-events \
  --log-group-name /ecs/kvs-infer-gpu \
  --log-stream-name <STREAM_NAME> \
  --region ap-southeast-1

# Health check
# Get task private IP
aws ecs describe-tasks \
  --cluster vivid-fish-il1akc \
  --tasks <TASK_ARN> \
  --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
  --output text

# Test health endpoint (from within VPC)
curl http://<PRIVATE_IP>:8080/health
```

---

## 📈 Monitoring

### CloudWatch Logs

- Log Group: `/ecs/kvs-infer-gpu`
- Format: JSON
- Retention: 7 days

### Prometheus Metrics

Endpoint: `http://<TASK_IP>:8080/metrics`

Metrics:
- `infer_frames_total` - Total frames processed
- `infer_events_total` - Total detection events
- `infer_latency_ms` - Inference latency
- `publisher_failures_total` - Publisher failures
- `worker_alive` - Worker health status

### Container Insights

Enabled on cluster: `vivid-fish-il1akc`

View in CloudWatch → Container Insights

---

## 💰 Cost Estimation

### g4dn.xlarge (On-Demand)

- **Instance Cost**: ~$0.526/hour (~$12.62/day)
- **GPU**: 1x NVIDIA T4 (16GB)
- **vCPUs**: 4
- **Memory**: 16 GB
- **Network**: Up to 25 Gbps

### Additional Costs

- **S3**: ~$0.023/GB/month (snapshots)
- **Kinesis Data Streams**: ~$0.015/shard/hour
- **DynamoDB**: Pay per request (on-demand)
- **CloudWatch Logs**: ~$0.50/GB ingested
- **VPC Endpoints**: ~$0.01/hour per endpoint

**Estimated Total**: ~$15-20/day

---

## 🎉 Next Steps

หลังจาก deploy สำเร็จ:

1. ✅ ตรวจสอบ logs และ metrics
2. ✅ ทดสอบ detection กับ KVS streams
3. ✅ ตรวจสอบ events ใน Kinesis Data Stream
4. ✅ ตรวจสอบ snapshots ใน S3
5. ✅ เพิ่ม cameras ใน `cameras-ecs.yaml`
6. ✅ Scale up เป็น multiple tasks (ถ้าต้องการ)
7. ✅ ตั้งค่า CloudWatch Alarms
8. ✅ ตั้งค่า Auto Scaling policies

---

## 📚 References

- [ECS GPU Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-gpu.html)
- [Service Quotas](https://console.aws.amazon.com/servicequotas/home)
- [VPC Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)
- [Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)
