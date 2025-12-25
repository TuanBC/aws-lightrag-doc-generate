# CI/CD Pipeline Documentation

This repository uses GitHub Actions for continuous integration and deployment.

## Workflows

### 1. `ci-cd.yml` - Main CI/CD Pipeline
**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

**Jobs:**
- **Lint**: Runs Ruff linter and formatter checks
- **Test**: Runs pytest with coverage reporting
- **Build Docker**: Builds and optionally pushes Docker images
- **Security Scan**: Runs Trivy vulnerability scanner
- **Deploy Staging**: Deploys to staging environment (develop branch)
- **Deploy Production**: Deploys to production environment (main branch)

### 2. `docker-build.yml` - Docker Image Build
**Triggers:**
- Push to `main` branch
- Version tags (v*.*.*)
- Manual workflow dispatch

**Features:**
- Builds multi-architecture images (amd64, arm64)
- Pushes to GitHub Container Registry (ghcr.io)
- Automatic version tagging

### 3. `codeql.yml` - Code Security Analysis
**Triggers:**
- Push to `main` or `develop` branches
- Pull requests
- Weekly schedule (Sundays)

**Features:**
- Static code analysis for security vulnerabilities
- Python code scanning

## Required Secrets

Configure these secrets in GitHub repository settings:

### Required for Testing
- `ETHERSCAN_API_KEY` - Etherscan API key (can use dummy value for tests)

### Optional for Docker Registry
- `DOCKER_USERNAME` - Docker Hub username (if using Docker Hub)
- `DOCKER_PASSWORD` - Docker Hub password/token

### Optional for Deployment
- `STAGING_URL` - Staging environment URL
- `PRODUCTION_URL` - Production environment URL
- Additional deployment secrets based on your platform:
  - AWS: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ACCOUNT_ID`
  - Kubernetes: `KUBECONFIG`
  - Fly.io: `FLY_API_TOKEN`
  - Railway: `RAILWAY_TOKEN`

### 4. `deploy-frontend.yml` - Frontend S3 Deployment
**Triggers:**
- Push to `main` branch (changes in `frontend/` directory)
- Manual workflow dispatch

**Features:**
- Builds Next.js static export
- Automatically fetches Lambda Function URL as API base
- Deploys to S3 with proper cache headers
- HTML files: no-cache for instant updates
- Assets: 1-year cache with immutable flag

**Required Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID` (your 12-digit AWS account ID)

## Environment Variables

The workflows use these environment variables:
- `PYTHON_VERSION`: "3.12"
- `DOCKER_IMAGE_NAME`: "credit-scoring-onchain"
- `REGISTRY`: "ghcr.io" (GitHub Container Registry)

## Coverage Reporting

Test coverage is automatically uploaded to Codecov (if configured). To enable:
1. Sign up at [codecov.io](https://codecov.io)
2. Add your repository
3. Add `CODECOV_TOKEN` secret (optional, public repos work without it)

## Deployment Configuration

### Staging Deployment
- Triggered on push to `develop` branch
- Runs after successful Docker build
- Configure deployment commands in `deploy-staging` job

### Production Deployment
- Triggered on push to `main` branch
- Runs after successful Docker build and security scan
- Requires manual approval (if environment protection is enabled)
- Configure deployment commands in `deploy-production` job

## Customizing Deployment

Edit the deployment jobs in `ci-cd.yml`:

### Example: Deploy to Fly.io
```yaml
- name: Deploy to Fly.io
  run: |
    curl -L https://fly.io/install.sh | sh
    export FLYCTL_INSTALL="/home/runner/.fly"
    export PATH="$FLYCTL_INSTALL/bin:$PATH"
    flyctl deploy --remote-only
  env:
    FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

### Example: Deploy to Kubernetes
```yaml
- name: Deploy to Kubernetes
  run: |
    echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig.yaml
    export KUBECONFIG=kubeconfig.yaml
    kubectl apply -f k8s/
    kubectl rollout status deployment/credit-scoring-app
```

### Example: Deploy to AWS ECS
```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-1

- name: Deploy to ECS
  run: |
    aws ecs update-service \
      --cluster my-cluster \
      --service credit-scoring-service \
      --force-new-deployment
```

## Workflow Status Badges

Add these badges to your README.md:

```markdown
![CI/CD](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/CI/CD%20Pipeline/badge.svg)
![Docker Build](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Docker%20Build%20and%20Push/badge.svg)
![CodeQL](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/CodeQL%20Analysis/badge.svg)
```

## Troubleshooting

### Tests Failing
- Ensure `ETHERSCAN_API_KEY` secret is set (can be a dummy value for tests)
- Check that all dependencies are in `requirements.txt`
- Verify pytest configuration in `pytest.ini`

### Docker Build Failing
- Check Dockerfile syntax
- Ensure all required files are in the repository
- Verify `.dockerignore` is configured correctly

### Deployment Failing
- Verify deployment secrets are set
- Check deployment commands are correct for your platform
- Review environment protection settings in GitHub

## Best Practices

1. **Never commit secrets** - Always use GitHub Secrets
2. **Test locally first** - Run `pytest` and `ruff check` before pushing
3. **Review PRs** - All PRs must pass CI before merging
4. **Use semantic versioning** - Tag releases with `v1.0.0` format
5. **Monitor security scans** - Review CodeQL and Trivy results regularly

