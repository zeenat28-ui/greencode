# test-github-oauth-production.ps1
# Run this AFTER adding environment variables to Vercel and redeploying

Write-Host "`n═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   GITHUB OAUTH PRODUCTION TEST" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "[1/4] Testing if Vercel deployment is online..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "https://greencode-teal.vercel.app/api/health" -Method GET -TimeoutSec 10
    Write-Host "✓ Backend is online - Version: $($health.version)" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend health check failed" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/4] Testing GitHub OAuth configuration..." -ForegroundColor Yellow
try {
    $oauth = Invoke-RestMethod -Uri "https://greencode-teal.vercel.app/api/auth/github/authorize" -Method GET -TimeoutSec 10
    
    if ($oauth.configured -eq $true) {
        Write-Host "✓ GitHub OAuth is CONFIGURED!" -ForegroundColor Green
        Write-Host "  Client ID: $($oauth.client_id)" -ForegroundColor Green
        Write-Host "  Auth URL: $($oauth.auth_url.Substring(0, [Math]::Min(80, $oauth.auth_url.Length)))..." -ForegroundColor Green
    } else {
        Write-Host "✗ GitHub OAuth is NOT configured" -ForegroundColor Red
        Write-Host "  Message: $($oauth.message)" -ForegroundColor Red
        Write-Host "`n  Did you add the environment variables to Vercel?" -ForegroundColor Yellow
        Write-Host "  - GITHUB_CLIENT_ID" -ForegroundColor Yellow
        Write-Host "  - GITHUB_CLIENT_SECRET" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "✗ GitHub OAuth endpoint failed" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/4] Testing Demo login (backup)..." -ForegroundColor Yellow
try {
    $demo = Invoke-RestMethod -Uri "https://greencode-teal.vercel.app/api/auth/demo" -Method POST -TimeoutSec 10
    if ($demo.success -eq $true) {
        Write-Host "✓ Demo login works" -ForegroundColor Green
    } else {
        Write-Host "○ Demo login response: $($demo | ConvertTo-Json)" -ForegroundColor Gray
    }
} catch {
    Write-Host "○ Demo login test skipped" -ForegroundColor Gray
}

Write-Host "`n[4/4] Opening GitHub OAuth flow in browser..." -ForegroundColor Yellow
if ($oauth.auth_url) {
    Write-Host "✓ Opening browser for OAuth test..." -ForegroundColor Green
    Start-Process $oauth.auth_url
    Write-Host "`nPlease complete the GitHub authorization in your browser." -ForegroundColor Cyan
    Write-Host "After authorizing, you should be redirected to your dashboard." -ForegroundColor Cyan
} else {
    Write-Host "○ No auth URL available" -ForegroundColor Gray
}

Write-Host "`n═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   TEST COMPLETE!" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Complete GitHub authorization in the browser" -ForegroundColor White
Write-Host "2. You should land on the dashboard" -ForegroundColor White
Write-Host "3. Try scanning a repository!" -ForegroundColor White
Write-Host ""
