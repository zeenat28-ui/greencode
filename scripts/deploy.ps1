<#
.SYNOPSIS
  Deploy GreenCode Auditor to production (Vercel / Render / Docker).

.DESCRIPTION
  Alexa voice command "deploy to production" triggers this script.
  It supports Vercel, Render, and Docker-based deployment.

  Set the following environment variables before running:
    - VERCEL_TOKEN / VERCEL_ORG_ID / VERCEL_PROJECT_ID  (for Vercel)
    - RENDER_SERVICE_ID / RENDER_API_KEY                (for Render)
    - DOCKER_REGISTRY / DOCKER_USERNAME / DOCKER_PASSWORD (for Docker)
#>
param(
    [string]$Environment = "production",
    [string]$Platform = "vercel"  # vercel | render | docker
)

$ErrorActionPreference = "Stop"

Write-Host "=== GreenCode Deploy ===" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Platform: $Platform" -ForegroundColor Yellow

switch ($Platform) {
    "vercel" {
        if (-not $env:VERCEL_TOKEN) {
            Write-Warning "VERCEL_TOKEN not set. Skipping Vercel deploy."
            exit 0
        }
        Write-Host "Deploying to Vercel..." -ForegroundColor Green
        & npx vercel deploy --prod --token $env:VERCEL_TOKEN
    }
    "render" {
        if (-not $env:RENDER_API_KEY) {
            Write-Warning "RENDER_API_KEY not set. Skipping Render deploy."
            exit 0
        }
        Write-Host "Triggering Render deploy..." -ForegroundColor Green
        # Render deploy hook
        $url = "https://api.render.com/v1/services/$env:RENDER_SERVICE_ID/deploys"
        $headers = @{ Authorization = "Bearer $env:RENDER_API_KEY" }
        Invoke-RestMethod -Method Post -Uri $url -Headers $headers
    }
    "docker" {
        Write-Host "Building Docker image..." -ForegroundColor Green
        & docker build -t greencode:$Environment .
        if ($env:DOCKER_REGISTRY) {
            & docker push $env:DOCKER_REGISTRY/greencode:$Environment
        }
    }
    default {
        Write-Warning "Unknown platform: $Platform"
    }
}

Write-Host "Deploy complete." -ForegroundColor Cyan
