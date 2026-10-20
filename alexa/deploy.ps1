#!/usr/bin/env pwsh
# ============================================================================
# GreenCode Alexa Skill - Deployment Script
# ============================================================================
# Deploys the Alexa Custom Skill interaction model and configures the
# GreenCode MCP/ASK webhook endpoint for production use.
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - ASK CLI installed (npm install -g ask-cli)
#   - GREENCODE_ALEXA_SKILL_ID set (your Alexa Skill ID)
#   - GREENCODE_MCP_TOKEN set (for MCP server auth)
#   - Your GreenCode API deployed and reachable (Vercel, EC2, etc.)
# ============================================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  GreenCode Alexa Skill - Deployment" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# ------------------------------------------------------------------ config --
$SKILL_ID = $env:GREENCODE_ALEXA_SKILL_ID
$MCP_TOKEN = $env:GREENCODE_MCP_TOKEN
$API_BASE_URL = $env:GREENCODE_API_BASE_URL  # e.g. https://greencode-teal.vercel.app
$INTERACTION_MODEL = Join-Path $PSScriptRoot "interaction_model_en_US.json"

if (-not $SKILL_ID) {
    Write-Warning "GREENCODE_ALEXA_SKILL_ID not set. Skill ID validation will be skipped."
}
if (-not $API_BASE_URL) {
    Write-Warning "GREENCODE_API_BASE_URL not set. Using default https://greencode-teal.vercel.app"
    $API_BASE_URL = "https://greencode-teal.vercel.app"
}

# ------------------------------------------------------------------ step 1 --
Write-Host "`n[1/4] Validating interaction model..." -ForegroundColor Yellow
if (-not (Test-Path $INTERACTION_MODEL)) {
    Write-Error "Interaction model not found: $INTERACTION_MODEL"
    exit 1
}

$model = Get-Content $INTERACTION_MODEL -Raw | ConvertFrom-Json
$intentCount = $model.interactionModel.languageModel.intents.Count
Write-Host "  Interaction model loaded: $intentCount intents" -ForegroundColor Green

# ------------------------------------------------------------------ step 2 --
Write-Host "`n[2/4] Checking GreenCode API health..." -ForegroundColor Yellow
try {
    $healthResp = Invoke-RestMethod -Uri "$API_BASE_URL/api/health" -Method Get -TimeoutSec 10
    Write-Host "  API health: $($healthResp.status)" -ForegroundColor Green
} catch {
    Write-Warning "  Could not reach GreenCode API at $API_BASE_URL. Continue anyway."
}

# ------------------------------------------------------------------ step 3 --
Write-Host "`n[3/4] Alexa Skill endpoints to configure:" -ForegroundColor Yellow
Write-Host "  ASK Custom Skill Webhook: $API_BASE_URL/api/alexa/skill" -ForegroundColor Green
Write-Host "  MCP Streamable HTTP:      $API_BASE_URL/mcp" -ForegroundColor Green
Write-Host "  Skill ID: $SKILL_ID" -ForegroundColor Green

# ------------------------------------------------------------------ step 4 --
Write-Host "`n[4/4] Next steps (manual):" -ForegroundColor Yellow
Write-Host "  1. In the Alexa Developer Console, create/edit your skill:" -ForegroundColor Green
Write-Host "     https://developer.amazon.com/alexa/console/ask"
Write-Host "  2. Set Invocation Name to: green code auditor"
Write-Host "  3. Import the interaction model from: $INTERACTION_MODEL"
Write-Host "  4. Set the endpoint to HTTPS: $API_BASE_URL/api/alexa/skill"
Write-Host "  5. Set GREENCODE_ALEXA_SKILL_ID=$SKILL_ID on your server"
Write-Host "  6. Set GREENCODE_MCP_TOKEN=$MCP_TOKEN on your server (if using MCP auth)"
Write-Host "  7. Build and test the skill in the Alexa Developer Console"
Write-Host ""
Write-Host "  Example voice commands after deployment:" -ForegroundColor Green
Write-Host "    'Alexa, ask Green Code Auditor to audit my repository'"
Write-Host "    'Alexa, ask Green Code Auditor what is my green score'"
Write-Host "    'Alexa, ask Green Code Auditor compare Ireland and Virginia'"
Write-Host "    'Alexa, ask Green Code Auditor measure energy'"
Write-Host "    'Alexa, ask Green Code Auditor refactor my code'"
Write-Host "========================================================================" -ForegroundColor Cyan
