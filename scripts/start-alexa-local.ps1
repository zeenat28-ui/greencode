param(
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$profilePath = Join-Path $env:LOCALAPPDATA "GreenCode\alexa-tunnel.json"
$startedProcesses = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$logDirectory = Join-Path $env:LOCALAPPDATA "GreenCode\logs"

function Get-NgrokPath {
    $command = Get-Command ngrok -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\ngrok.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\ngrok\ngrok.exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

function Test-LocalPort([int]$Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Wait-ForHttp([string]$Url, [int]$ExpectedStatus, [int]$Attempts = 40) {
    for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing
            if ([int]$response.StatusCode -eq $ExpectedStatus) { return }
        } catch {
            if ($_.Exception.Response -and
                [int]$_.Exception.Response.StatusCode -eq $ExpectedStatus) {
                return
            }
        }
        Start-Sleep -Milliseconds 750
    }
    throw "Timed out waiting for $Url to return HTTP $ExpectedStatus."
}

function Start-ManagedProcess(
    [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$WorkingDirectory,
    [string]$Name
) {
    $stdout = Join-Path $logDirectory "$Name.out.log"
    $stderr = Join-Path $logDirectory "$Name.err.log"
    $process = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru
    $startedProcesses.Add($process)
    return $process
}

if (-not (Test-Path -LiteralPath $profilePath)) {
    Write-Host "ngrok is not configured. Running one-time ngrok setup..."
    & (Join-Path $PSScriptRoot "setup-alexa-tunnel.ps1")
    if (-not (Test-Path -LiteralPath $profilePath)) {
        throw "Alexa tunnel setup did not complete."
    }
}

$profile = Get-Content -LiteralPath $profilePath -Raw | ConvertFrom-Json
if ($profile.provider -ne "ngrok") {
    throw "The saved tunnel profile is not an ngrok profile. Rerun scripts\setup-alexa-tunnel.ps1."
}
$ngrok = Get-NgrokPath
if (-not $ngrok) {
    throw "ngrok is required. Install it with 'winget install --id Ngrok.Ngrok -e', then rerun this script."
}
$configCheckLog = Join-Path $env:TEMP ("greencode-ngrok-check-" + [guid]::NewGuid().ToString("N"))
$configCheck = Start-Process -FilePath $ngrok -ArgumentList @("config", "check") `
    -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$configCheckLog.out" `
    -RedirectStandardError "$configCheckLog.err"
Remove-Item -LiteralPath "$configCheckLog.out", "$configCheckLog.err" -Force -ErrorAction SilentlyContinue
if ($configCheck.ExitCode -ne 0) {
    throw "ngrok is not authenticated. Run scripts\setup-alexa-tunnel.ps1 and add your free-account token locally."
}
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ".env"))) {
    throw "Create the repository .env from .env.example and configure GREENCODE_ALEXA_SKILL_ID before starting Alexa."
}
$skillIdSetting = Select-String -Path (Join-Path $repoRoot ".env") `
    -Pattern '^\s*GREENCODE_ALEXA_SKILL_ID\s*=\s*\S+' -Quiet
if (-not $skillIdSetting) {
    throw "GREENCODE_ALEXA_SKILL_ID is missing or empty in .env. Set it to the Skill ID shown in the Alexa Developer Console."
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

$backendStarted = $false
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) { throw "Python was not found. Install the project environment first." }
    $python = $pythonCommand.Source
}
if (-not (Test-LocalPort 8000)) {
    Start-ManagedProcess $python @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") $repoRoot "backend" | Out-Null
    $backendStarted = $true
}
Wait-ForHttp "http://127.0.0.1:8000/api/health" 200 120

if (-not (Test-LocalPort 8766)) {
    $previousMcpPort = $env:GREENCODE_MCP_PORT
    $env:GREENCODE_MCP_PORT = "8766"
    try {
        Start-ManagedProcess $python @("-m", "app.mcp_server") $repoRoot "mcp-server" | Out-Null
    } finally {
        if ($null -eq $previousMcpPort) {
            Remove-Item Env:\GREENCODE_MCP_PORT -ErrorAction SilentlyContinue
        } else {
            $env:GREENCODE_MCP_PORT = $previousMcpPort
        }
    }
    $mcpReady = $false
    for ($attempt = 0; $attempt -lt 40 -and -not $mcpReady; $attempt++) {
        $mcpReady = Test-LocalPort 8766
        if (-not $mcpReady) { Start-Sleep -Milliseconds 500 }
    }
    if (-not $mcpReady) {
        throw "The MCP server did not start on port 8766. Inspect $logDirectory\mcp-server.err.log."
    }
}

$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCommand) { throw "Node.js was not found. Install Node.js before starting the Alexa bridge." }
$bridgeProbe = @{ version = "1.0"; request = @{ type = "LaunchRequest" } } | ConvertTo-Json -Compress

if (-not (Test-LocalPort 8765)) {
    Start-ManagedProcess $nodeCommand.Source @((Join-Path $repoRoot "scripts\alexa_webhook_bridge.js")) $repoRoot "alexa-bridge" | Out-Null
} else {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/alexa/skill" `
            -Method Post -ContentType "application/json" -Body $bridgeProbe `
            -TimeoutSec 5 -UseBasicParsing | Out-Null
        throw "The service already listening on port 8765 accepted an unsigned Alexa request."
    } catch {
        if (-not $_.Exception.Response -or
            [int]$_.Exception.Response.StatusCode -notin @(400, 403, 503)) {
            throw "Port 8765 is occupied by a service that could not be verified as the guarded Alexa bridge."
        }
    }
}

$publicEndpoint = "https://$($profile.hostname)/api/alexa/skill"
$tunnelArguments = @("http", "http://127.0.0.1:8765")
if ($profile.hostname) {
    $tunnelArguments += @("--url", "https://$($profile.hostname)")
}
Write-Host "Starting the authenticated ngrok tunnel to the Alexa-only bridge..." -ForegroundColor Cyan
$tunnelProcess = Start-ManagedProcess $ngrok $tunnelArguments $repoRoot "alexa-tunnel"

$tunnelEndpoint = $null
for ($attempt = 0; $attempt -lt 60 -and -not $tunnelEndpoint; $attempt++) {
    if ($tunnelProcess.HasExited) {
        throw "ngrok exited. Inspect $logDirectory\alexa-tunnel.err.log"
    }
    try {
        $agent = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3
        $tunnel = @($agent.tunnels) | Where-Object {
            $_.proto -eq "https" -and $_.config.addr -match "127\.0\.0\.1:8765"
        } | Select-Object -First 1
        if ($tunnel) { $tunnelEndpoint = [string]$tunnel.public_url }
    } catch {
        $tunnelEndpoint = $null
    }
    if (-not $tunnelEndpoint) { Start-Sleep -Seconds 1 }
}
if (-not $tunnelEndpoint) {
    throw "ngrok did not publish an HTTPS endpoint. Check your free-account status and $logDirectory\alexa-tunnel.err.log."
}
$hostname = ([uri]$tunnelEndpoint).Host
if ($profile.hostname -and $hostname -ne $profile.hostname) {
    throw "ngrok assigned '$hostname', but the saved hostname is '$($profile.hostname)'. Confirm your free dev domain in the ngrok dashboard and update the local profile."
}
$profile.hostname = $hostname
$profile | ConvertTo-Json | Set-Content -LiteralPath $profilePath -Encoding UTF8
$publicEndpoint = "$tunnelEndpoint/api/alexa/skill"

$tunnelReady = $false
$probePayload = @{
    version = "1.0"
    request = @{
        type = "LaunchRequest"
        timestamp = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
} | ConvertTo-Json -Compress
try {
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if (-not $curl) { throw "curl.exe is required to verify the public HTTPS endpoint." }
    $probePayloadPath = Join-Path $env:TEMP ("greencode-alexa-probe-" + [guid]::NewGuid().ToString("N") + ".json")
    [System.IO.File]::WriteAllText($probePayloadPath, $probePayload, [System.Text.UTF8Encoding]::new($false))
    for ($attempt = 0; $attempt -lt 30 -and -not $tunnelReady; $attempt++) {
        try {
            $probeOutput = @(& $curl.Source --silent --show-error --connect-timeout 5 --max-time 10 `
                -H "Content-Type: application/json" `
                --data-binary "@$probePayloadPath" `
                --write-out "`n%{http_code}" "$tunnelEndpoint/api/alexa/skill") -join "`n"
            if ($LASTEXITCODE -eq 0 -and $probeOutput -match '(?s)^(?<body>.*)\r?\n(?<status>\d{3})\s*$') {
                $probeBody = $Matches.body.Trim()
                $probeStatus = [int]$Matches.status
                if ($probeStatus -eq 400) {
                    try {
                        $probeError = $probeBody | ConvertFrom-Json
                        $tunnelReady = $probeError.error -eq "missing_signature"
                    } catch {
                        $tunnelReady = $false
                    }
                }
            }
        } catch {
            $tunnelReady = $false
        }
        if (-not $tunnelReady) { Start-Sleep -Seconds 2 }
    }
} finally {
    if ($probePayloadPath -and (Test-Path -LiteralPath $probePayloadPath)) {
        Remove-Item -LiteralPath $probePayloadPath -Force
    }
}
if (-not $tunnelReady) {
    throw "The public ngrok endpoint did not reach the guarded Alexa webhook. Inspect $logDirectory\alexa-tunnel.err.log."
}

if (-not $NoFrontend) {
    if (-not (Test-LocalPort 5173)) {
        $npm = Get-Command npm -ErrorAction SilentlyContinue
        $viteCli = Join-Path $repoRoot "frontend\node_modules\vite\bin\vite.js"
        if ($npm -and (Test-Path -LiteralPath $viteCli)) {
            $nodePath = $nodeCommand.Source
            Start-ManagedProcess $nodePath @($viteCli, "--host", "127.0.0.1") `
                (Join-Path $repoRoot "frontend") "frontend" | Out-Null
            try { Wait-ForHttp "http://127.0.0.1:5173/" 200 30 } catch {
                Write-Warning "Frontend did not become ready. See $logDirectory\frontend.err.log"
            }
        } else {
            Write-Warning "Frontend was not started: install frontend dependencies or use -NoFrontend."
        }
    }
}

Write-Host ""
Write-Host "GreenCode local Alexa stack is ready." -ForegroundColor Green
if (-not $NoFrontend) {
    Write-Host "Frontend: http://127.0.0.1:5173"
} else {
    Write-Host "Frontend: not started (-NoFrontend)"
}
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Alexa:    $publicEndpoint"
Write-Host "Keep this window open while testing. Press Ctrl+C to stop the services started here."

try {
    while ($true) {
        foreach ($process in $startedProcesses) {
            if ($process.HasExited) {
                throw "A managed service exited unexpectedly (PID $($process.Id)). Check its logs in $logDirectory."
            }
        }
        Start-Sleep -Seconds 2
    }
} finally {
    for ($index = $startedProcesses.Count - 1; $index -ge 0; $index--) {
        $process = $startedProcesses[$index]
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        }
    }
    if ($backendStarted) {
        Write-Host "Stopped the backend started by this launcher."
    }
}
