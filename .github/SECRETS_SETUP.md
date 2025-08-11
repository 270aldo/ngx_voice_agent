# GitHub Secrets Configuration Guide

This document outlines all required secrets and environment variables for the NGX Voice Sales Agent CI/CD pipeline.

## 🔐 Required Secrets

### API Keys and Tokens

#### OpenAI Integration
```
OPENAI_API_KEY_TEST
```
- **Description**: OpenAI API key for testing environment
- **Usage**: Used in CI tests to validate AI functionality
- **Format**: `sk-...` (OpenAI API key format)
- **Required for**: CI pipeline, integration tests

#### Database and Infrastructure

```
SUPABASE_URL_TEST
SUPABASE_ANON_KEY_TEST
```
- **Description**: Supabase credentials for test environment
- **Usage**: Database connections during testing
- **Format**: 
  - URL: `https://your-project.supabase.co`
  - Key: Supabase anonymous key
- **Required for**: CI pipeline, integration tests

### AWS Deployment Credentials

#### Staging Environment
```
AWS_ACCESS_KEY_ID_STAGING
AWS_SECRET_ACCESS_KEY_STAGING
AWS_REGION
```
- **Description**: AWS credentials for staging deployments
- **Usage**: ECS deployments to staging environment
- **Permissions Required**:
  - `ecs:UpdateService`
  - `ecs:DescribeTaskDefinition`
  - `ecs:RegisterTaskDefinition`
  - `ecs:DescribeServices`
- **Required for**: CD pipeline staging deployment

#### Production Environment
```
AWS_ACCESS_KEY_ID_PRODUCTION
AWS_SECRET_ACCESS_KEY_PRODUCTION
```
- **Description**: AWS credentials for production deployments
- **Usage**: ECS deployments to production environment
- **Permissions Required**: Same as staging
- **Required for**: CD pipeline production deployment

### API Authentication Tokens

```
STAGING_API_TOKEN
PRODUCTION_API_TOKEN
```
- **Description**: Bearer tokens for API authentication during deployment verification
- **Usage**: Health checks and deployment verification
- **Format**: JWT or API key format
- **Required for**: Post-deployment verification

### Optional Notification Services

```
SLACK_WEBHOOK_URL
```
- **Description**: Slack webhook for failure notifications
- **Usage**: Send alerts when daily checks fail
- **Format**: `https://hooks.slack.com/services/...`
- **Required for**: Daily checks notification (optional)

## 🌍 Environment Variables

### GitHub Environments

The repository uses GitHub Environments for deployment protection:

#### Staging Environment
- **Name**: `staging`
- **URL**: `https://staging.ngx-voice-agent.com`
- **Protection Rules**: None (auto-deploy)
- **Secrets**: All staging-specific secrets

#### Production Environment
- **Name**: `production`
- **URL**: `https://api.ngx-voice-agent.com`
- **Protection Rules**: 
  - Required reviewers (recommended: 2)
  - Manual approval required
  - Branch restrictions: `main` only
- **Secrets**: All production-specific secrets

## 📋 Setup Instructions

### 1. Repository Secrets Setup

Navigate to your repository settings and add these secrets:

```bash
# Go to: Settings > Secrets and variables > Actions > New repository secret
```

### 2. Environment-Specific Secrets

For each environment (staging/production):

```bash
# Go to: Settings > Environments > [Environment Name] > Add secret
```

### 3. AWS IAM Setup

Create dedicated IAM users for each environment:

#### Staging IAM Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecs:UpdateService",
                "ecs:DescribeServices",
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition",
                "ecs:ListTaskDefinitions"
            ],
            "Resource": [
                "arn:aws:ecs:*:*:service/ngx-staging/*",
                "arn:aws:ecs:*:*:task-definition/ngx-voice-agent-staging:*"
            ]
        }
    ]
}
```

#### Production IAM Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecs:UpdateService",
                "ecs:DescribeServices",
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition",
                "ecs:ListTaskDefinitions"
            ],
            "Resource": [
                "arn:aws:ecs:*:*:service/ngx-production/*",
                "arn:aws:ecs:*:*:task-definition/ngx-voice-agent-production:*"
            ]
        }
    ]
}
```

### 4. Supabase Test Database Setup

Create a separate Supabase project for testing:

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Create new project: `ngx-voice-agent-test`
3. Copy the URL and anon key
4. Run database migrations on test instance
5. Add secrets to GitHub

### 5. API Token Generation

Generate API tokens for deployment verification:

```python
# Example token generation script
import jwt
import datetime

def generate_api_token(secret_key, environment):
    payload = {
        'environment': environment,
        'purpose': 'deployment-verification',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=365)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')

# Generate tokens for each environment
staging_token = generate_api_token('your-staging-secret', 'staging')
production_token = generate_api_token('your-production-secret', 'production')
```

## 🔍 Verification Script

Use this script to verify all secrets are properly configured:

```bash
#!/bin/bash
# verify-secrets.sh

echo "🔍 Verifying GitHub Secrets Configuration..."

# Required secrets list
secrets=(
    "OPENAI_API_KEY_TEST"
    "SUPABASE_URL_TEST"
    "SUPABASE_ANON_KEY_TEST"
    "AWS_ACCESS_KEY_ID_STAGING"
    "AWS_SECRET_ACCESS_KEY_STAGING"
    "AWS_REGION"
    "AWS_ACCESS_KEY_ID_PRODUCTION"
    "AWS_SECRET_ACCESS_KEY_PRODUCTION"
    "STAGING_API_TOKEN"
    "PRODUCTION_API_TOKEN"
)

# Check each secret
for secret in "${secrets[@]}"; do
    if gh secret list | grep -q "$secret"; then
        echo "✅ $secret: Configured"
    else
        echo "❌ $secret: Missing"
    fi
done

echo ""
echo "🌍 Checking Environments..."

# Check environments
environments=("staging" "production")
for env in "${environments[@]}"; do
    if gh api repos/:owner/:repo/environments | jq -r '.[].name' | grep -q "$env"; then
        echo "✅ Environment '$env': Configured"
    else
        echo "❌ Environment '$env': Missing"
    fi
done

echo ""
echo "💡 To add missing secrets:"
echo "   gh secret set SECRET_NAME --body 'secret-value'"
echo "   gh api repos/:owner/:repo/environments/$env --method PUT --field name=$env"
```

## 🚨 Security Best Practices

### Secret Rotation Schedule
- **API Keys**: Rotate quarterly
- **AWS Credentials**: Rotate every 6 months
- **Database Credentials**: Rotate annually

### Access Control
- Limit repository access to essential team members
- Use environment protection rules for production
- Enable audit logging for secret access

### Secret Management
- Never commit secrets to code
- Use GitHub's secret scanning alerts
- Regularly audit secret usage in workflows

### Monitoring
- Set up alerts for failed authentications
- Monitor unusual deployment patterns
- Review workflow logs regularly

## 📞 Support

If you encounter issues with secret configuration:

1. Check the workflow logs for specific error messages
2. Verify secret names match exactly (case-sensitive)
3. Ensure secrets are added to the correct environment
4. Test secrets independently before using in workflows

For urgent issues, contact the DevOps team or create an issue with the `infrastructure` label.

---

*Last updated: 2025-08-03*
*Version: 1.0*