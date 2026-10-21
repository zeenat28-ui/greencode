# GitHub OAuth Setup - Production Deployment

## Problem Summary
Your production deployment at `https://greencode-teal.vercel.app` was using a minimal API handler that didn't expose the full FastAPI application with OAuth routes. Additionally, the GitHub OAuth credentials were missing from Vercel environment variables.

## What Was Fixed
✅ **Updated `api/index.py`** to properly use the full FastAPI app (`app.main`)
✅ **Pushed changes to GitHub** - Vercel is auto-deploying now
✅ **All OAuth routes now exposed**:
- `/api/auth/github/authorize`
- `/api/auth/github/oauth`
- `/api/auth/google/authorize`
- `/api/auth/google/oauth`
- `/api/auth/login`
- `/api/auth/register`
- `/api/auth/demo`

## What You Need To Do

### Step 1: Add Environment Variables to Vercel

Go to your Vercel project settings:
https://vercel.com/zeenatriaz468-4881s-projects/greencode/settings/environment-variables

Add these **TWO** environment variables:

| Variable Name | Value | Environment |
|---------------|-------|-------------|
| `GITHUB_CLIENT_ID` | `Ov23liuZ38iXiMFskDVq` | Production ✓ |
| `GITHUB_CLIENT_SECRET` | `8a7ece446ca4a564f3b4b59b5f308d5bed38f8b2` | Production ✓ |

**Important:** Make sure to check "Production" environment for both variables!

### Step 2: Wait for Vercel Deployment

1. Go to: https://vercel.com/zeenatriaz468-4881s-projects/greencode/deployments
2. Wait for the latest deployment to complete (2-3 minutes)
3. Or click "Redeploy" to force a fresh build with the new env vars

### Step 3: Verify GitHub OAuth App Settings

Go to: https://github.com/settings/developers

Find your OAuth App and verify these settings:

- **Homepage URL:** `https://greencode-teal.vercel.app`
- **Authorization callback URL:** `https://greencode-teal.vercel.app/login`

(Note: NO trailing slash on `/login`)

### Step 4: Test GitHub Login

Run the test script:
```powershell
.\test-github-oauth-production.ps1
```

Or manually test:
1. Visit https://greencode-teal.vercel.app
2. Click "Continue with GitHub"
3. Authorize the app on GitHub
4. You should be redirected to the dashboard
5. Try scanning a real repository!

## Verification Checklist

- [ ] Added `GITHUB_CLIENT_ID` to Vercel
- [ ] Added `GITHUB_CLIENT_SECRET` to Vercel
- [ ] Waited for Vercel deployment to complete
- [ ] Verified GitHub OAuth app callback URL
- [ ] Tested login flow
- [ ] Successfully scanned a repository

## Troubleshooting

### "GitHub OAuth not configured" error
- Check that you added BOTH environment variables to Vercel
- Make sure you selected "Production" environment
- Click "Redeploy" after adding the variables

### Redirect issues
- Verify the GitHub OAuth app callback URL is exactly: `https://greencode-teal.vercel.app/login`
- No trailing slash
- Must match exactly

### Still having issues?
Run the diagnostic:
```powershell
.\test-github-oauth-production.ps1
```

The script will tell you exactly what's wrong.

## Ready for Hackathon Demo!

Once GitHub OAuth works, you can:
1. ✅ Login with real GitHub account
2. ✅ Scan your actual repositories
3. ✅ Show real carbon intelligence data
4. ✅ Record impressive demo video
5. ✅ Submit to Amazon Developer Hackathon 2026

---

**Created:** 2026-01-19  
**Status:** Waiting for environment variables to be added to Vercel
