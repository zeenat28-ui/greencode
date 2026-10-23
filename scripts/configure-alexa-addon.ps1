<#
.SYNOPSIS
  Configure Alexa+'s addon.json with the public GreenCode MCP server URL.

.DESCRIPTION
  Updates the MCP endpoint and serves privacy, terms, and media URLs from the
  same public HTTPS origin. With -ConfigureAskSkill, it also configures the
  separate ASK Custom Skill webhook at /api/alexa/skill.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,
    [string]$AddonPath = (Join-Path $PSScriptRoot "..\alexa\addon.json"),
    [string]$SkillPath = (Join-Path $PSScriptRoot "..\alexa\skill.json"),
    [switch]$ConfigureAskSkill
)

$ErrorActionPreference = "Stop"

$baseUri = $null
if (-not [Uri]::TryCreate($BaseUrl.TrimEnd("/"), [UriKind]::Absolute, [ref]$baseUri)) {
    throw "BaseUrl must be an absolute HTTPS URL, for example https://mcp.example.com."
}
if ($baseUri.Scheme -ne "https" -or $baseUri.AbsolutePath -ne "/" -or $baseUri.Query -or $baseUri.Fragment) {
    throw "BaseUrl must be an HTTPS origin without a path, query, or fragment."
}
if ($baseUri.Host -match "YOUR_PUBLIC_HTTPS_HOST|REPLACE") {
    throw "BaseUrl must be a real public HTTPS hostname, not a placeholder."
}
if (-not (Test-Path -LiteralPath $AddonPath -PathType Leaf)) {
    throw "Alexa+ add-on manifest was not found: $AddonPath"
}

$origin = $baseUri.GetLeftPart([UriPartial]::Authority)
$manifest = Get-Content -LiteralPath $AddonPath -Raw | ConvertFrom-Json
$integration = @($manifest.integrations | Where-Object { $_.type -eq "MCP" }) | Select-Object -First 1
if (-not $integration) {
    throw "The manifest does not contain an MCP integration."
}

$integration.config.endpoints.default.type = "HTTPS"
$integration.config.endpoints.default.uri = "$origin/mcp"
$manifest.storeListing.privacyAndCompliance.privacyPolicyUrl = "$origin/privacy"
$manifest.storeListing.privacyAndCompliance.termsOfUseUrl = "$origin/terms"

foreach ($theme in @("light", "dark")) {
    $prefix = ""
    if ($theme -eq "dark") {
        $prefix = "dark-"
    }
    foreach ($icon in $manifest.storeListing.mediaAssets.icons.$theme) {
        $icon.uri = "$origin/assets/icon-$prefix$($icon.size).png"
    }
}
foreach ($image in $manifest.storeListing.mediaAssets.carouselImages) {
    $image.uri = "$origin/assets/carousel-$($image.size).png"
}

$json = ConvertTo-Json -InputObject $manifest -Depth 50
$encoding = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Resolve-Path -LiteralPath $AddonPath).Path, "$json`n", $encoding)
Write-Host "Alexa+ manifest configured for $origin/mcp" -ForegroundColor Green

if ($ConfigureAskSkill) {
    if (-not (Test-Path -LiteralPath $SkillPath -PathType Leaf)) {
        throw "Alexa Custom Skill manifest was not found: $SkillPath"
    }
    $skill = Get-Content -LiteralPath $SkillPath -Raw | ConvertFrom-Json
    $skill.manifest.apis.custom.endpoint.uri = "$origin/api/alexa/skill"
    $skillJson = ConvertTo-Json -InputObject $skill -Depth 50
    [System.IO.File]::WriteAllText((Resolve-Path -LiteralPath $SkillPath).Path, "$skillJson`n", $encoding)
    Write-Host "Alexa Custom Skill webhook configured for $origin/api/alexa/skill" -ForegroundColor Green
}
