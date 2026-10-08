<#
.SYNOPSIS
  Expose the local GreenCode MCP server at a public HTTPS URL - the
  "accessible via a remote URL" requirement in the Alexa+ MCP quickstart,
  which names cloudflared as the tunneling service for local development.

.DESCRIPTION
  1. Starts `cloudflared tunnel --url http://127.0.0.1:<port>` and waits for
     the printed https:// URL.
  2. Adds the tunnel domain to GREENCODE_MCP_ALLOWED_HOSTS - without it the
     MCP transport's DNS-rebinding guard answers 421 to every request whose
     Host is not loopback, which would block the public URL entirely.
  3. Starts `python -m app.mcp_server` in the foreground (Ctrl+C stops it,
     then the tunnel is torn down).

  Set GREENCODE_MCP_TOKEN before running this so the /mcp endpoint answers
  unauthenticated requests with the 401 + PRM handshake the Alexa+ checklist
  requires. Paste the printed https:// URL into addon.json's
  integrations[0].config.endpoints.default.uri. The tunnel is HTTPS; the
  server itself stays loopback-only - cloudflared terminates the public side.

.NOTES
  Requires: python (repo venv), cloudflared on PATH
  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
#>
param(
    [string]$Port = $(if ($env:GREENCODE_MCP_PORT) { $env:GREENCODE_MCP_PORT } else { "8765" })
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    # Common download location when cloudflared isn't on PATH.
    $localCloudflared = Join-Path $env:LOCALAPPDATA "cloudflared.exe"
    if (Test-Path $localCloudflared) {
        $env:Path = "$env:LOCALAPPDATA;$env:Path"
    } else {
        Write-Error "cloudflared not found on PATH. Install it from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        exit 1
    }
}

if (-not $env:GREENCODE_MCP_TOKEN) {
    Write-Warning "GREENCODE_MCP_TOKEN is not set - /mcp will run open. Set it to enforce the Alexa+ 401 checklist."
}

# 1. Tunnel first: its random domain is needed for the Host allowlist.
$tunnelLog = Join-Path $env:TEMP "greencode-tunnel-$Port.log"
$tunnelErr = Join-Path $env:TEMP "greencode-tunnel-$Port.err.log"
Remove-Item $tunnelLog, $tunnelErr -ErrorAction SilentlyContinue

Write-Host "Starting cloudflared tunnel to http://127.0.0.1:$Port ..."
$tunnel = Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://127.0.0.1:$Port" `
    -RedirectStandardOutput $tunnelLog -RedirectStandardError $tunnelErr -PassThru

$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep -Milliseconds 500
    # cloudflared prints the quick-tunnel URL to stderr (its log stream), not
    # stdout - check both files or the wait loop times out on a healthy tunnel.
    foreach ($log in $tunnelLog, $tunnelErr) {
        if (Test-Path $log) {
            $found = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -AllMatches -ErrorAction SilentlyContinue
            if ($found) { $url = $found[0].Matches[0].Value; break }
        }
    }
}
if (-not $url) {
    Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
    Write-Error "Tunnel did not print a URL. See $tunnelErr"
    exit 1
}

# 2. Allow the tunnel's Host through the MCP transport's rebinding guard.
$tunnelHost = ([uri]$url).Host
if ($env:GREENCODE_MCP_ALLOWED_HOSTS) {
    $env:GREENCODE_MCP_ALLOWED_HOSTS = "$($env:GREENCODE_MCP_ALLOWED_HOSTS),$tunnelHost"
} else {
    $env:GREENCODE_MCP_ALLOWED_HOSTS = $tunnelHost
}

# 2.5 Quick tunnels get a fresh domain each run - point addon.json at it so
#     every URL (endpoint, privacy, terms, icons) stays live without editing.
$addonPath = Join-Path $PSScriptRoot "..\alexa\addon.json"
if (Test-Path $addonPath) {
    $before = Get-Content $addonPath -Raw
    $after = $before -replace "https://[a-z0-9-]+\.trycloudflare\.com", $url
    if ($after -ne $before) {
        Set-Content -Path $addonPath -Value $after -NoNewline
        Write-Host "addon.json URLs updated -> $url" -ForegroundColor Green
    }
}

Write-Host "Tunnel up: $url" -ForegroundColor Green
Write-Host "Allowed host: $tunnelHost" -ForegroundColor Green
Write-Host "Open $url/privacy in a browser to confirm it is reachable." -ForegroundColor Cyan

# 3. Server in the foreground; Ctrl+C tears the tunnel down with it.
Write-Host "Starting MCP server on http://127.0.0.1:$Port/mcp (Ctrl+C stops both)." -ForegroundColor Cyan
try {
    python -m app.mcp_server
} finally {
    if ($tunnel -and -not $tunnel.HasExited) {
        Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Tunnel stopped."
    }
}
