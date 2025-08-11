# Branch Protection Rules Setup

## Overview
Branch protection rules help maintain code quality and prevent accidental changes to important branches.

## Setup Instructions

### For `main` branch:

1. Go to Settings → Branches in your GitHub repository
2. Click "Add rule"
3. Branch name pattern: `main`
4. Configure these settings:

   **Protect matching branches**
   - ✅ Require a pull request before merging
     - ✅ Require approvals: 2
     - ✅ Dismiss stale pull request approvals when new commits are pushed
     - ✅ Require review from CODEOWNERS
   
   - ✅ Require status checks to pass before merging
     - ✅ Require branches to be up to date before merging
     - Status checks:
       - `Backend Tests`
       - `Security Scan`
       - `Lint Code`
   
   - ✅ Require conversation resolution before merging
   - ✅ Require signed commits
   - ✅ Require linear history
   - ✅ Include administrators
   - ✅ Restrict who can push to matching branches
     - Add specific users/teams who can push

### For `develop` branch:

1. Click "Add rule"
2. Branch name pattern: `develop`
3. Configure these settings:

   **Protect matching branches**
   - ✅ Require a pull request before merging
     - ✅ Require approvals: 1
     - ✅ Dismiss stale pull request approvals when new commits are pushed
   
   - ✅ Require status checks to pass before merging
     - Status checks:
       - `Backend Tests`
       - `Lint Code`
   
   - ✅ Require conversation resolution before merging
   - ✅ Require linear history

## Additional Security Settings

### Enable these repository security features:

1. **Dependency Graph** - Settings → Security & analysis
   - ✅ Dependency graph
   - ✅ Dependabot alerts
   - ✅ Dependabot security updates

2. **Code Scanning** - Settings → Security & analysis
   - ✅ Code scanning alerts
   - Set up CodeQL analysis

3. **Secret Scanning** - Settings → Security & analysis
   - ✅ Secret scanning
   - ✅ Push protection

## Automated Enforcement

The branch protection rules work with our CI/CD pipeline to:
- Prevent direct pushes to protected branches
- Ensure all code is reviewed
- Run automated tests before merging
- Maintain a clean, linear Git history
- Protect against security vulnerabilities

## Emergency Override

In case of emergency hotfixes:
1. Create a `hotfix/*` branch from `main`
2. Apply the fix
3. Create PR to `main` with expedited review
4. After merge to `main`, cherry-pick to `develop`