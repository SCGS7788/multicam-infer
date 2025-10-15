╔══════════════════════════════════════════════════════════════════════╗
║                  CI/CD Setup Complete! ✅                            ║
╚══════════════════════════════════════════════════════════════════════╝

✅ สิ่งที่เสร็จแล้ว
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ✅ สร้าง GitHub Actions workflow
   - ไฟล์: .github/workflows/deploy-ecs.yml
   - ฟังก์ชัน: Build Docker image (linux/amd64) และ deploy ไปยัง ECS

2. ✅ สร้าง IAM User สำหรับ CI/CD
   - User: github-actions-kvs-infer
   - Permissions:
     • AmazonEC2ContainerRegistryPowerUser
     • AmazonECS_FullAccess
     • IAMReadOnlyAccess

3. ✅ Initialize Git repository
   - Branch: main
   - Code pushed to GitHub

4. ✅ สร้าง documentation
   - .github/workflows/README.md


⏭️  ขั้นตอนต่อไป (สำคัญ!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 STEP 1: เพิ่ม GitHub Secrets
──────────────────────────────────────────────────────────────────

⚠️  IMPORTANT: ต้องเพิ่ม AWS credentials ใน GitHub Secrets!

1. ไปที่: https://github.com/SCGS7788/multicam-infer/settings/secrets/actions
2. คลิก "New repository secret"
3. เพิ่ม 2 secrets ดังนี้:

   Secret #1:
   ┌─────────────────────────────────────┐
   │ Name:  AWS_ACCESS_KEY_ID            │
   │ Value: (ดูจาก AWS IAM Console)      │
   └─────────────────────────────────────┘

   Secret #2:
   ┌─────────────────────────────────────────────────────┐
   │ Name:  AWS_SECRET_ACCESS_KEY                        │
   │ Value: (ดูจาก AWS IAM Console)                      │
   └─────────────────────────────────────────────────────┘

📝 วิธีหา AWS Credentials:
   - IAM User: github-actions-kvs-infer
   - หาก credentials หาย: สร้าง access key ใหม่ใน IAM Console


📌 STEP 2: Trigger Workflow
──────────────────────────────────────────────────────────────────

หลังจากเพิ่ม Secrets แล้ว:

1. ไปที่: https://github.com/SCGS7788/multicam-infer/actions
2. เลือก workflow "Build and Deploy to ECS"
3. คลิก "Run workflow"
4. เลือก branch: main
5. คลิก "Run workflow" สีเขียว

หรือ push code ใหม่:
```bash
git commit --allow-empty -m "Trigger CI/CD"
git push origin main
```


📌 STEP 3: Monitor Deployment
──────────────────────────────────────────────────────────────────

1. ไปที่ GitHub Actions tab
2. คลิกเข้าไปดู workflow ที่กำลังทำงาน
3. ดู real-time logs

Build จะใช้เวลาประมาณ 15-20 นาที:
- Docker build: 8-12 นาที
- ECR push: 2-3 นาที
- ECS deploy: 2-5 นาที


📌 STEP 4: Verify Deployment
──────────────────────────────────────────────────────────────────

หลัง workflow สำเร็จ:

```bash
aws ecs describe-services \
  --cluster vivid-fish-il1akc \
  --services kvs-infer-gpu \
  --region ap-southeast-1 \
  --query 'services[0].{Status: status, Running: runningCount}'
```


🎯 ทำไมต้องใช้ CI/CD?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ ปัญหาเดิม:
   - Docker image ถูก build บน Mac (ARM64/Apple Silicon)
   - AWS ECS ต้องการ linux/amd64
   - ไม่สามารถ pull image ได้: "no matching manifest for linux/amd64"

✅ แก้ไขด้วย CI/CD:
   - GitHub Actions ใช้ Ubuntu runner (linux/amd64)
   - Build image บน server โดยตรง
   - รองรับ platform ที่ต้องการ 100%
   - ไม่ต้อง build locally อีกต่อไป!


🎉 ข้อดีเพิ่มเติม
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Auto-deploy ทุกครั้งที่ push code
✅ Version tracking ด้วย git SHA
✅ Easy rollback หากมีปัญหา
✅ Consistent build environment
✅ ไม่ต้องใช้ Docker Desktop บน Mac
✅ ฟรี 2000 minutes/month (public repo)


💡 Tips
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. เก็บ AWS credentials ไว้ในที่ปลอดภัย
2. ไม่ commit credentials เข้า git
3. ใช้ GitHub Secrets เท่านั้น
4. Monitor CloudWatch Logs: /ecs/kvs-infer-gpu


🚀 Next: เพิ่ม GitHub Secrets!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ทำตาม STEP 1 ข้างบน เพื่อเริ่ม deployment!

╔══════════════════════════════════════════════════════════════════════╗
║              เพิ่ม GitHub Secrets แล้ว Run Workflow!               ║
╚══════════════════════════════════════════════════════════════════════╝
