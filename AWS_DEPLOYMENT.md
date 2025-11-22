# AWS Deployment Quick Start

This guide provides a quick setup for deploying to AWS ECS with automatic CI/CD.

## 🚀 Quick Setup (5 minutes)

### Step 1: Create AWS Resources

Run these commands in your AWS CLI:

```bash
# 1. Create ECR repository
aws ecr create-repository \
  --repository-name credit-scoring-onchain \
  --region us-east-1

# 2. Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Your AWS Account ID: $AWS_ACCOUNT_ID"

# 3. Create IAM user for GitHub Actions
aws iam create-user --user-name github-actions-deploy

# 4. Create access key (save the output!)
aws iam create-access-key --user-name github-actions-deploy

# 5. Attach policies
aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess

aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
```

### Step 2: Create ECS Resources

```bash
# 1. Create cluster
aws ecs create-cluster --cluster-name credit-scoring-cluster --region us-east-1

# 2. Create CloudWatch log group
aws logs create-log-group \
  --log-group-name /ecs/credit-scoring-onchain \
  --region us-east-1

# 3. Create secrets (replace with your actual keys)
aws secretsmanager create-secret \
  --name credit-scoring/etherscan-api-key \
  --secret-string "YOUR_ETHERSCAN_KEY" \
  --region us-east-1

aws secretsmanager create-secret \
  --name credit-scoring/openrouter-api-key \
  --secret-string "YOUR_OPENROUTER_KEY" \
  --region us-east-1
```

### Step 3: Register Task Definition

1. Edit `aws/ecs-task-definition.json`:
   - Replace `YOUR_ACCOUNT_ID` with your AWS account ID
   - Update region if different

2. Register it:
```bash
aws ecs register-task-definition \
  --cli-input-json file://aws/ecs-task-definition.json \
  --region us-east-1
```

### Step 4: Create ECS Service

**Option A: With Public IP (Simplest)**
```bash
# Get default VPC and subnets
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text | tr '\t' ',')

# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name credit-scoring-sg \
  --description "Credit scoring app security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow HTTP traffic
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0

# Create service
aws ecs create-service \
  --cluster credit-scoring-cluster \
  --service-name credit-scoring-service \
  --task-definition credit-scoring-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
  --region us-east-1
```

**Option B: With Application Load Balancer (Recommended for Production)**

See `aws/README.md` for ALB setup instructions.

### Step 5: Configure GitHub Secrets

Go to: **Repository → Settings → Secrets and variables → Actions**

Add these secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | From Step 1.4 | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | From Step 1.4 | AWS secret key |
| `AWS_REGION` | `us-east-1` | AWS region |
| `PRODUCTION_URL` | Your app URL | Optional, for status badges |

### Step 6: Update Workflow Configuration

Edit `.github/workflows/aws-deploy.yml` and verify these values match your setup:

```yaml
env:
  AWS_REGION: us-east-1  # Your region
  ECR_REPOSITORY: credit-scoring-onchain
  ECS_SERVICE: credit-scoring-service
  ECS_CLUSTER: credit-scoring-cluster
  ECS_TASK_DEFINITION: credit-scoring-task
  CONTAINER_NAME: credit-scoring-app
```

### Step 7: Deploy!

```bash
git add .
git commit -m "Configure AWS deployment"
git push origin main
```

The workflow will:
1. ✅ Build Docker image
2. ✅ Push to ECR
3. ✅ Deploy to ECS
4. ✅ Update service with new image

## 📊 Monitor Deployment

### View Workflow
- Go to **Actions** tab in GitHub
- Watch the "AWS Deployment" workflow run

### Check ECS Service
```bash
aws ecs describe-services \
  --cluster credit-scoring-cluster \
  --services credit-scoring-service \
  --region us-east-1
```

### View Logs
```bash
aws logs tail /ecs/credit-scoring-onchain --follow --region us-east-1
```

### Get Application URL
```bash
# Get task public IP
TASK_ARN=$(aws ecs list-tasks \
  --cluster credit-scoring-cluster \
  --service-name credit-scoring-service \
  --query 'taskArns[0]' --output text)

ENI_ID=$(aws ecs describe-tasks \
  --cluster credit-scoring-cluster \
  --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text)

PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $ENI_ID \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text)

echo "Application URL: http://$PUBLIC_IP:8000"
```

## 🔧 Troubleshooting

### Workflow fails at "Login to Amazon ECR"
- ✅ Check AWS credentials are correct
- ✅ Verify IAM user has ECR permissions
- ✅ Check region matches

### Deployment fails
- ✅ Verify task definition is registered
- ✅ Check ECS cluster exists
- ✅ Verify service name matches
- ✅ Review CloudWatch logs

### Service won't start
- ✅ Check security group allows port 8000
- ✅ Verify secrets exist in Secrets Manager
- ✅ Check task definition ARNs are correct
- ✅ Review ECS service events

## 📚 Next Steps

- **Auto-scaling**: Configure based on CPU/memory
- **Load Balancer**: Set up ALB for high availability
- **Custom Domain**: Use Route 53 + ACM
- **Monitoring**: Set up CloudWatch alarms
- **Cost Optimization**: Right-size resources

## 📖 Full Documentation

For detailed setup instructions, see:
- `aws/README.md` - Complete AWS setup guide
- `aws/terraform/README.md` - Infrastructure as Code option

## 💰 Estimated Costs

- **ECS Fargate**: ~$15-30/month (512 CPU, 1GB RAM, 24/7)
- **ECR**: ~$0.10/GB/month (storage)
- **CloudWatch Logs**: ~$0.50/GB ingested
- **Data Transfer**: ~$0.09/GB out

**Total**: ~$20-40/month for basic setup

## ✅ Checklist

- [ ] ECR repository created
- [ ] IAM user and access keys created
- [ ] ECS cluster created
- [ ] Task definition registered
- [ ] ECS service created
- [ ] Secrets stored in Secrets Manager
- [ ] GitHub secrets configured
- [ ] Workflow configuration updated
- [ ] First deployment successful
- [ ] Application accessible

---

**Ready to deploy!** Push to your repository and watch the magic happen! 🚀

