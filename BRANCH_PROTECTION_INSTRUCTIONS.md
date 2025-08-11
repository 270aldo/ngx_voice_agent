# Branch Protection Setup Instructions

## Manual Setup Required

Due to API limitations, branch protection rules need to be configured manually through the GitHub web interface.

## Steps to Configure Branch Protection

1. **Navigate to Repository Settings**
   - Go to https://github.com/270aldo/ngx_voice_agent
   - Click on "Settings" tab
   - Click on "Branches" in the left sidebar

2. **Add Branch Protection Rule**
   - Click "Add rule" button
   - Branch name pattern: `main`

3. **Configure Protection Settings**

   ### ✅ Required Status Checks
   - [x] Require status checks to pass before merging
   - [x] Require branches to be up to date before merging
   - **Required status checks:**
     - `security-scan`
     - `code-quality` 
     - `test`
     - `docker-build`

   ### ✅ Pull Request Reviews
   - [x] Require pull request reviews before merging
   - **Required approving reviews:** 1
   - [x] Dismiss stale pull request reviews when new commits are pushed
   - [x] Require review from code owners

   ### ✅ Additional Restrictions
   - [x] Require linear history
   - [x] Include administrators (enforce for admins)
   - [x] Allow force pushes: **NO**
   - [x] Allow deletions: **NO**

4. **Save Protection Rule**
   - Click "Create" to save the branch protection rule

## Verification

After setup, verify that:
- ✅ Direct commits to `main` are blocked
- ✅ Pull requests require review
- ✅ Status checks must pass before merge
- ✅ Code owner reviews are required

## Alternative: GitHub CLI Command

If you have the GitHub CLI configured with appropriate permissions, you can run:

```bash
# This command should be run by repository admin
gh api repos/270aldo/ngx_voice_agent/branches/main/protection \
  --method PUT \
  --raw-field required_status_checks='{"strict":true,"contexts":["security-scan","code-quality","test","docker-build"]}' \
  --raw-field enforce_admins=true \
  --raw-field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":true}' \
  --raw-field restrictions=null \
  --raw-field required_linear_history=true \
  --raw-field allow_force_pushes=false \
  --raw-field allow_deletions=false
```

## Status

- [x] Repository created and configured
- [x] GitFlow branching strategy implemented
- [x] CI/CD workflows configured
- [ ] **Manual branch protection setup required** 
- [x] Release v0.9.0-beta tagged
- [x] Documentation completed

**Next Action Required:** Repository administrator must configure branch protection rules manually through GitHub web interface.