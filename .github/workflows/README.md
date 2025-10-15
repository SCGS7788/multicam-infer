# GitHub Actions CI/CD Setup Guide

## 🚀 Automated Build and Deployment

This workflow automatically builds Docker images on GitHub's Ubuntu runners (linux/amd64) and deploys to AWS ECS.

## ⚙️ Setup GitHub Secrets

You need to add these secrets to your GitHub repository:

### 1. Go to GitHub Repository Settings
```
https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions
```

### 2. Add Required Secrets

Click "New repository secret" and add:

#### AWS_ACCESS_KEY_ID
```
Your AWS Access Key ID
```

#### AWS_SECRET_ACCESS_KEY
```
Your AWS Secret Access Key
```

## 📝 How to Create AWS Credentials for GitHub Actions

### Option A: Create IAM User (Recommended for CI/CD)

```bash
# 1. Create IAM user for GitHub Actions
aws iam create-user --user-name github-actions-kvs-infer

# 2. Create access key
aws iam create-access-key --user-name github-actions-kvs-infer

# Save the output - you'll need AccessKeyId and SecretAccessKey

# 3. Attach required policies
aws iam attach-user-policy \
  --user-name github-actions-kvs-infer \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-user-policy \
  --user-name github-actions-kvs-infer \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
```

### Option B: Use Existing Credentials

If you already have AWS credentials configured locally:

```bash
# View your credentials (DO NOT share these)
cat ~/.aws/credentials
```

Look for:
- `aws_access_key_id` → Add as AWS_ACCESS_KEY_ID secret
- `aws_secret_access_key` → Add as AWS_SECRET_ACCESS_KEY secret

## 🎯 Workflow Triggers

The workflow runs automatically when:

1. **Push to main/master branch**
   ```bash
   git add .
   git commit -m "Update code"
   git push origin main
   ```

2. **Manual trigger** via GitHub Actions UI
   - Go to Actions tab
   - Select "Build and Deploy to ECS"
   - Click "Run workflow"

## 📦 What the Workflow Does

1. ✅ Checks out your code
2. ✅ Configures AWS credentials
3. ✅ Logs in to Amazon ECR
4. ✅ Builds Docker image for **linux/amd64** platform
5. ✅ Pushes image to ECR with:
   - Tag: git commit SHA
   - Tag: `latest`
6. ✅ Updates ECS task definition
7. ✅ Deploys to ECS service
8. ✅ Waits for service stability

## 🔍 Monitor Deployment

### Via GitHub
- Go to "Actions" tab in your repository
- Click on the running workflow
- View real-time logs

### Via AWS
```bash
# Check service status
aws ecs describe-services \
  --cluster vivid-fish-il1akc \
  --services kvs-infer-gpu \
  --region ap-southeast-1

# View task logs
aws logs tail /ecs/kvs-infer-gpu --follow
```

## ⚡ Quick Deploy Now

If you want to trigger the workflow immediately:

1. Commit this workflow file:
   ```bash
   cd /Users/pradyapadsee/Documents/aws/multicam-infer
   git add .github/workflows/deploy-ecs.yml
   git commit -m "Add CI/CD workflow for ECS deployment"
   git push origin main
   ```

2. The workflow will start automatically!

## 🛠️ Troubleshooting

### Build Fails
- Check if Docker build succeeds locally
- Review Dockerfile for errors
- Check GitHub Actions logs

### AWS Authentication Fails
- Verify AWS credentials in GitHub Secrets
- Ensure IAM user has required permissions
- Check AWS region is correct

### ECS Deployment Fails
- Verify ECS cluster name: `vivid-fish-il1akc`
- Verify ECS service name: `kvs-infer-gpu`
- Check task definition exists
- Ensure container instance has enough resources

## 📊 Expected Build Time

- Docker build: 8-12 minutes
- ECR push: 2-3 minutes
- ECS deployment: 2-5 minutes
- **Total: ~15-20 minutes**

## 🎉 Benefits

- ✅ No more platform compatibility issues (ARM64 vs AMD64)
- ✅ Automatic deployment on code changes
- ✅ Consistent build environment
- ✅ Version tracking with git SHA tags
- ✅ Rollback capability
- ✅ No local Docker build needed
