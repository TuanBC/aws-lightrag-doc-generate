# Terraform Infrastructure as Code

This directory contains Terraform configuration for provisioning AWS resources.

## Prerequisites

1. Terraform installed (>= 1.0)
2. AWS CLI configured
3. Appropriate AWS permissions

## Usage

### Initialize Terraform

```bash
cd aws/terraform
terraform init
```

### Plan Changes

```bash
terraform plan \
  -var="etherscan_api_key=your-key-here" \
  -var="openrouter_api_key=your-key-here"
```

### Apply Configuration

```bash
terraform apply \
  -var="etherscan_api_key=your-key-here" \
  -var="openrouter_api_key=your-key-here"
```

### Destroy Resources

```bash
terraform destroy
```

## Variables

Create a `terraform.tfvars` file:

```hcl
aws_region         = "us-east-1"
etherscan_api_key  = "your-key"
openrouter_api_key = "your-key"
```

Then run:
```bash
terraform apply
```

## Outputs

After applying, Terraform will output:
- ECR repository URL
- ECS cluster name
- Task definition ARN

Use these values to update your GitHub Actions workflow.

