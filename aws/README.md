# AWS Deployment Guide

This guide walks you through deploying the Onchain Credit Scoring application to AWS using ECS Fargate.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI installed and configured
3. Docker installed locally (for testing)
4. GitHub repository with Actions enabled

## Architecture

- **ECR (Elastic Container Registry)**: Stores Docker images
- **ECS Fargate**: Runs containers without managing servers
- **Application Load Balancer**: Routes traffic to containers
- **Secrets Manager**: Stores sensitive configuration
- **CloudWatch Logs**: Application logging

## Step 1: Create AWS Resources

### 1.1 Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name credit-scoring-onchain \
  --region us-east-1 \
  --image-scanning-configuration scanOnPush=true
```

### 1.2 Create IAM Roles

#### Task Execution Role
```bash
# Create role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

#### Task Role (for application permissions)
```bash
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'
```

### 1.3 Create Secrets in AWS Secrets Manager

```bash
# Etherscan API Key
aws secretsmanager create-secret \
  --name credit-scoring/etherscan-api-key \
  --secret-string "your-etherscan-api-key-here" \
  --region us-east-1

# OpenRouter API Key (optional)
aws secretsmanager create-secret \
  --name credit-scoring/openrouter-api-key \
  --secret-string "your-openrouter-api-key-here" \
  --region us-east-1
```

### 1.4 Create CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/credit-scoring-onchain \
  --region us-east-1
```

### 1.5 Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name credit-scoring-cluster \
  --region us-east-1
```

### 1.6 Create VPC and Networking (if needed)

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# Create subnets (at least 2 in different AZs)
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create security group
aws ec2 create-security-group \
  --group-name credit-scoring-sg \
  --description "Security group for credit scoring app" \
  --vpc-id vpc-xxx

# Allow HTTP/HTTPS traffic
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0
```

### 1.7 Create Application Load Balancer (Optional but Recommended)

```bash
aws elbv2 create-load-balancer \
  --name credit-scoring-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx \
  --region us-east-1

# Create target group
aws elbv2 create-target-group \
  --name credit-scoring-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --health-check-path /api/health \
  --health-check-interval-seconds 30
```

## Step 2: Register Task Definition

1. Edit `aws/ecs-task-definition.json`:
   - Replace `YOUR_ACCOUNT_ID` with your AWS account ID
   - Update region if different from `us-east-1`
   - Adjust CPU/memory as needed
   - Update secret ARNs

2. Register the task definition:
```bash
aws ecs register-task-definition \
  --cli-input-json file://aws/ecs-task-definition.json \
  --region us-east-1
```

## Step 3: Create ECS Service

```bash
aws ecs create-service \
  --cluster credit-scoring-cluster \
  --service-name credit-scoring-service \
  --task-definition credit-scoring-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/credit-scoring-tg/xxx,containerName=credit-scoring-app,containerPort=8000" \
  --region us-east-1
```

## Step 4: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key
- `AWS_REGION` - AWS region (e.g., `us-east-1`)
- `PRODUCTION_URL` - Your application URL (optional, for status badges)

### Create IAM User for GitHub Actions

```bash
# Create user
aws iam create-user --user-name github-actions-deploy

# Create access key
aws iam create-access-key --user-name github-actions-deploy

# Attach policies
aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess

aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess

# For Secrets Manager access
aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

## Step 5: Update Workflow Configuration

Edit `.github/workflows/aws-deploy.yml` and update:

```yaml
env:
  AWS_REGION: us-east-1  # Your region
  ECR_REPOSITORY: credit-scoring-onchain
  ECS_SERVICE: credit-scoring-service
  ECS_CLUSTER: credit-scoring-cluster
  ECS_TASK_DEFINITION: credit-scoring-task
  CONTAINER_NAME: credit-scoring-app
```

## Step 6: Test Deployment

1. Push to your repository:
```bash
git add .
git commit -m "Configure AWS deployment"
git push origin main
```

2. Check GitHub Actions:
   - Go to Actions tab
   - Watch the workflow run
   - Verify build and deployment succeed

3. Verify deployment:
```bash
# Check ECS service
aws ecs describe-services \
  --cluster credit-scoring-cluster \
  --services credit-scoring-service \
  --region us-east-1

# Check running tasks
aws ecs list-tasks \
  --cluster credit-scoring-cluster \
  --service-name credit-scoring-service \
  --region us-east-1
```

## Step 7: Access Your Application

- If using ALB: Use the ALB DNS name
- If using public IP: Get the public IP from the task
- Update DNS/domain to point to your endpoint

## Monitoring

### View Logs
```bash
aws logs tail /ecs/credit-scoring-onchain --follow --region us-east-1
```

### CloudWatch Metrics
- Go to CloudWatch → Metrics → ECS
- Monitor CPU, memory, and request metrics

### Set Up Alarms
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name credit-scoring-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## Cost Optimization

1. **Right-size resources**: Adjust CPU/memory based on usage
2. **Use Spot instances**: For non-critical workloads
3. **Auto-scaling**: Scale down during low traffic
4. **Reserved capacity**: For predictable workloads

## Troubleshooting

### Deployment fails
- Check IAM permissions
- Verify ECR repository exists
- Check task definition is registered
- Review CloudWatch logs

### Service won't start
- Check security group rules
- Verify subnet configuration
- Check task definition secrets
- Review ECS service events

### High costs
- Review CloudWatch metrics
- Right-size task definitions
- Enable auto-scaling
- Use reserved capacity

## Security Best Practices

1. ✅ Use Secrets Manager for sensitive data
2. ✅ Enable ECR image scanning
3. ✅ Use least-privilege IAM policies
4. ✅ Enable VPC flow logs
5. ✅ Use HTTPS/ALB for public access
6. ✅ Regular security updates
7. ✅ Enable CloudTrail for audit logs

## Next Steps

- Set up auto-scaling based on CPU/memory
- Configure custom domain with Route 53
- Set up CloudFront for CDN
- Enable AWS WAF for DDoS protection
- Configure backup and disaster recovery

