# CI/CD Setup Guide

This guide will help you set up the CI/CD pipeline for the Onchain Credit Scoring application.

## Quick Start

1. **Push the workflow files to your repository**
   ```bash
   git add .github/
   git commit -m "Add CI/CD pipeline"
   git push
   ```

2. **Configure GitHub Secrets**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add the required secrets (see below)

3. **Verify the pipeline runs**
   - Go to Actions tab in GitHub
   - The pipeline should automatically run on your next push

## Required Secrets

### Minimum Required
- `ETHERSCAN_API_KEY` - Your Etherscan API key (required for tests)

### Optional (for Docker)
- `DOCKER_USERNAME` - Docker Hub username (if using Docker Hub)
- `DOCKER_PASSWORD` - Docker Hub access token

### Optional (for Deployment)
Add secrets based on your deployment platform:
- **AWS**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- **Kubernetes**: `KUBECONFIG` (base64 encoded)
- **Fly.io**: `FLY_API_TOKEN`
- **Railway**: `RAILWAY_TOKEN`
- **Heroku**: `HEROKU_API_KEY`

## Workflow Files

### `ci-cd.yml` - Main Pipeline
- Runs on every push and PR
- Includes: linting, testing, Docker builds, security scans
- Deploys to staging (develop) and production (main)

### `docker-build.yml` - Docker Images
- Builds and pushes Docker images to GitHub Container Registry
- Supports multi-architecture builds
- Automatic version tagging

### `codeql.yml` - Security Analysis
- Weekly security scans
- CodeQL analysis for Python

## Customizing for Your Deployment

### Step 1: Choose Your Platform

Edit `.github/workflows/ci-cd.yml` and update the deployment jobs:

#### Option A: Fly.io
```yaml
- name: Deploy to Fly.io
  uses: superfly/flyctl-actions/setup-flyctl@master
- name: Deploy
  run: flyctl deploy --remote-only
  env:
    FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

#### Option B: Railway
```yaml
- name: Deploy to Railway
  uses: bervProject/railway-deploy@main
  with:
    railway_token: ${{ secrets.RAILWAY_TOKEN }}
    service: credit-scoring-app
```

#### Option C: AWS ECS
```yaml
- name: Configure AWS
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-1
- name: Deploy
  run: |
    aws ecs update-service \
      --cluster my-cluster \
      --service credit-scoring \
      --force-new-deployment
```

### Step 2: Configure Environment Protection

1. Go to Settings → Environments
2. Create `staging` and `production` environments
3. Enable "Required reviewers" for production
4. Add deployment secrets to each environment

### Step 3: Set Up Branch Protection

1. Go to Settings → Branches
2. Add rule for `main` branch:
   - Require status checks to pass
   - Require branches to be up to date
   - Select: "CI/CD Pipeline / test"

## Testing the Pipeline

### Test Locally
```bash
# Run linting
ruff check .

# Run tests
pytest

# Build Docker image
docker build -t credit-scoring-onchain .
```

### Test in GitHub
1. Create a test branch
2. Make a small change
3. Push and create a PR
4. Verify all checks pass

## Monitoring

### View Workflow Runs
- Go to Actions tab
- Click on a workflow run to see details
- Check logs for any failures

### Set Up Notifications
1. Go to Settings → Notifications
2. Enable "Actions" notifications
3. Choose when to receive alerts

## Troubleshooting

### "Workflow not running"
- Check that workflow files are in `.github/workflows/`
- Verify YAML syntax is correct
- Ensure triggers match your branch names

### "Tests failing"
- Check that `ETHERSCAN_API_KEY` secret is set
- Verify all dependencies are in `requirements.txt`
- Run tests locally to debug

### "Docker build failing"
- Check Dockerfile syntax
- Verify all files are committed
- Check `.dockerignore` configuration

### "Deployment failing"
- Verify deployment secrets are set
- Check deployment commands are correct
- Review environment protection settings

## Next Steps

1. ✅ Push workflow files to repository
2. ✅ Configure GitHub Secrets
3. ✅ Test the pipeline with a PR
4. ✅ Customize deployment for your platform
5. ✅ Set up branch protection rules
6. ✅ Enable environment protection for production

## Support

For issues or questions:
- Check workflow logs in Actions tab
- Review [GitHub Actions documentation](https://docs.github.com/en/actions)
- Open an issue in the repository

