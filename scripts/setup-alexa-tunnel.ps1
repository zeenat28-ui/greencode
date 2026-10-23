param(
    [switch]$ResetToken
)

$ErrorActionPreference = "Stop"

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

$ngrok = Get-NgrokPath
if (-not $ngrok) {
    throw "ngrok is required. Install it with 'winget install --id Ngrok.Ngrok -e', then reopen PowerShell."
}

$ngrokConfigDirectory = Join-Path $env:LOCALAPPDATA "ngrok"
New-Item -ItemType Directory -Path $ngrokConfigDirectory -Force | Out-Null
$tempPrefix = Join-Path $env:TEMP ("greencode-ngrok-" + [guid]::NewGuid().ToString("N"))
$stdoutPath = "$tempPrefix.out"
$stderrPath = "$tempPrefix.err"
try {
    $configCheck = Start-Process -FilePath $ngrok -ArgumentList @("config", "check") `
        -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath
    if ($ResetToken -or $configCheck.ExitCode -ne 0) {
        Write-Host "A free ngrok account provides a stable development hostname without buying a domain."
        Write-Host "1. Create a free account at https://dashboard.ngrok.com/signup"
        Write-Host "2. Copy your agent authtoken from https://dashboard.ngrok.com/get-started/your-authtoken"
        $secureToken = Read-Host "Paste the token here in this local PowerShell prompt (never send it in chat)" -AsSecureString
        $tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
        try {
            $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
            $tokenProcess = Start-Process -FilePath $ngrok `
                -ArgumentList @("config", "add-authtoken", $token) `
                -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdoutPath `
                -RedirectStandardError $stderrPath
            if ($tokenProcess.ExitCode -ne 0) {
                throw "ngrok rejected the token. Check it in your dashboard and rerun setup."
            }
            $configCheck = Start-Process -FilePath $ngrok -ArgumentList @("config", "check") `
                -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdoutPath `
                -RedirectStandardError $stderrPath
            if ($configCheck.ExitCode -ne 0) {
                throw "ngrok could not validate its local configuration. Check the token and rerun setup."
            }
        } finally {
            if ($tokenPointer -ne [IntPtr]::Zero) {
                [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
            }
            $token = $null
            $secureToken.Dispose()
        }
    }
} finally {
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
}

$profileDirectory = Join-Path $env:LOCALAPPDATA "GreenCode"
$profilePath = Join-Path $profileDirectory "alexa-tunnel.json"
New-Item -ItemType Directory -Path $profileDirectory -Force | Out-Null

$profile = [ordered]@{
    provider = "ngrok"
    hostname = $null
}
$profile | ConvertTo-Json | Set-Content -LiteralPath $profilePath -Encoding UTF8

Write-Host ""
Write-Host "ngrok is authenticated. Its free account development domain is stable between runs." -ForegroundColor Green
Write-Host "Run .\scripts\start-alexa-local.ps1 to start GreenCode and discover the assigned hostname."
Write-Host "Save the printed https://<assigned-domain>/api/alexa/skill URL in the Alexa Developer Console once."
