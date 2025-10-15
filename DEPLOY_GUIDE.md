# 🚀 Quick Deployment Guide - kvs-infer to AWS ECS

## สถานะการพัฒนา

✅ **ระบบพร้อม Deploy:**
- Roboflow Gun Detector ติดตั้งและทดสอบเรียบร้อย
- Docker image กำลัง build
- AWS credentials configured
- Task definition พร้อมใช้งาน

---

## ขั้นตอนการ Deploy (Simplified)

### **ก่อน Deploy - ต้องเตรียม:**

1. **VPC และ Subnets**
   ```bash
   # ดู VPC ที่มี
   aws ec2 describe-vpcs --region ap-southeast-1
   
   # ดู Subnets
   aws ec2 describe-subnets --region ap-southeast-1 \
       --filters "Name=vpc-id,Values=vpc-xxxxx"
   ```

2. **Security Group**
   ```bash
   # สร้าง Security Group
   aws ec2 create-security-group \
       --group-name kvs-infer-sg \
       --description "Security group for kvs-infer ECS tasks" \
       --vpc-id vpc-xxxxx \
       --region ap-southeast-1
   ```

3. **IAM Roles** (ถ้ายังไม่มี)
   - `ecsTaskExecutionRole` - สำหรับ pull image จาก ECR และ logs
   - `ecsTaskRole` - สำหรับ access AWS services (KVS, KDS, S3)

---

### **วิธีที่ 1: Quick Deploy (แนะนำ)**

```bash
# 1. Build Docker image (กำลังทำงานอยู่)
docker build -t kvs-infer:latest .

# 2. Run quick deploy script
./quick-deploy.sh
```

**Script จะทำ:**
- ✅ สร้าง ECR repository
- ✅ Login เข้า ECR
- ✅ Tag และ push Docker image
- ✅ สร้าง ECS cluster

---

### **วิธีที่ 2: Manual Step-by-Step**

#### **Step 1: Build และ Push Image**

```bash
# Set variables
export AWS_ACCOUNT_ID=065693560492
export AWS_REGION=ap-southeast-1
export ECR_REPO_NAME=kvs-infer

# Create ECR repository
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS \
    --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag and push
docker tag kvs-infer:latest \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest

docker push \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
```

#### **Step 2: Create ECS Cluster**

```bash
# สร้าง cluster
aws ecs create-cluster \
    --cluster-name kvs-infer-cluster \
    --region $AWS_REGION \
    --settings name=containerInsights,value=enabled

# หรือสำหรับ GPU (ต้องมี EC2 instances)
aws ecs create-cluster \
    --cluster-name kvs-infer-cluster \
    --capacity-providers "FARGATE" "FARGATE_SPOT" \
    --region $AWS_REGION
```

#### **Step 3: Register Task Definition**

```bash
# Register task definition
aws ecs register-task-definition \
    --cli-input-json file://deployment/ecs/task-definition.json \
    --region $AWS_REGION
```

#### **Step 4: Create Service**

```bash
# สร้าง service (ต้องแก้ VPC, subnet, security-group)
aws ecs create-service \
    --cluster kvs-infer-cluster \
    --service-name kvs-infer-service \
    --task-definition kvs-infer-task \
    --desired-count 1 \
    --launch-type EC2 \
    --network-configuration "awsvpcConfiguration={
        subnets=[subnet-xxxxx,subnet-yyyyy],
        securityGroups=[sg-xxxxx],
        assignPublicIp=DISABLED
    }" \
    --region $AWS_REGION
```

---

### **วิธีที่ 3: Deploy ด้วย AWS Console**

1. **ECR (Elastic Container Registry)**
   - เปิด ECR Console
   - กด "Create repository" → ชื่อ: `kvs-infer`
   - Push image ด้วยคำสั่งที่ console แสดง

2. **ECS Cluster**
   - เปิด ECS Console
   - กด "Create Cluster"
   - เลือก "EC2 Linux + Networking"
   - ชื่อ: `kvs-infer-cluster`
   - Instance type: `g4dn.xlarge` (GPU)

3. **Task Definition**
   - กด "Create new Task Definition"
   - เลือก "EC2"
   - Copy content จาก `deployment/ecs/task-definition.json`
   - แก้ค่าตาม environment

4. **Service**
   - ใน Cluster → กด "Create Service"
   - เลือก Task Definition ที่สร้างไว้
   - Desired tasks: 1
   - Configure network settings

---

## 📋 Checklist ก่อน Deploy

- [ ] Docker image build เสร็จ
- [ ] AWS credentials configured
- [ ] ECR repository สร้างแล้ว
- [ ] Image push ไปที่ ECR แล้ว
- [ ] ECS cluster สร้างแล้ว
- [ ] VPC และ subnets พร้อมใช้งาน
- [ ] Security groups configured
- [ ] IAM roles สร้างแล้ว
- [ ] Task definition registered
- [ ] Config file (cameras.yaml) พร้อม

---

## 🔍 ตรวจสอบสถานะ

```bash
# ดู Docker build status
tail -f docker-build.log

# ดู ECR repositories
aws ecr describe-repositories --region ap-southeast-1

# ดู ECS clusters
aws ecs list-clusters --region ap-southeast-1

# ดู ECS tasks
aws ecs list-tasks --cluster kvs-infer-cluster --region ap-southeast-1

# ดู logs
aws logs tail /ecs/kvs-infer --follow --region ap-southeast-1
```

---

## 🎯 ถัดไป

หลังจาก Docker build เสร็จ:

1. รัน `./quick-deploy.sh` เพื่อ push image
2. แก้ไข `task-definition.json` ให้ตรงกับ VPC/subnet
3. Register task definition
4. Create ECS service
5. Monitor logs และ test system

---

## 💰 ประมาณการค่าใช้จ่าย

**Option 1: Fargate (ไม่ต้องจัดการ server)**
- 2 vCPU, 4 GB RAM: ~$0.10/hour
- เดือนละ ~$75 (ถ้ารันตลอด)

**Option 2: EC2 with GPU**
- g4dn.xlarge: ~$0.526/hour
- เดือนละ ~$380 (ถ้ารันตลอด)

**แนะนำ:** ใช้ Fargate ก่อน ถ้า performance ไม่พอค่อยย้ายไป GPU

---

## 🆘 Troubleshooting

**Docker build ช้า:**
```bash
# เช็ค progress
tail -f docker-build.log

# Cancel และ restart
pkill -f "docker build"
docker build -t kvs-infer:latest .
```

**ECR push ล้มเหลว:**
```bash
# Login ใหม่
aws ecr get-login-password --region ap-southeast-1 | \
    docker login --username AWS \
    --password-stdin 065693560492.dkr.ecr.ap-southeast-1.amazonaws.com
```

**ECS task ไม่ start:**
- ตรวจสอบ IAM roles
- ตรวจสอบ security groups (ต้องมี outbound rules)
- ดู logs ใน CloudWatch

---

## 📞 Next Steps

บอกฉันเมื่อ Docker build เสร็จ แล้วฉันจะช่วย:
1. Push image ไป ECR
2. Setup ECS infrastructure
3. Deploy service
4. Monitor และ verify system
