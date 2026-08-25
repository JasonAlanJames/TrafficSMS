param(
    [Parameter(Mandatory = $true)][string]$FrontendUrl,
    [Parameter(Mandatory = $true)][string]$BackendUrl
)

$ErrorActionPreference = "Stop"
$failed = $false

function Test-Endpoint {
    param([string]$Url)
    Write-Host "Checking $Url"
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing
        if ($response.StatusCode -eq 200) { Write-Host "PASS $Url" -ForegroundColor Green }
        else { Write-Host "FAIL $Url ($($response.StatusCode))" -ForegroundColor Red; $script:failed = $true }
    } catch {
        Write-Host "FAIL $Url ($($_.Exception.Message))" -ForegroundColor Red
        $script:failed = $true
    }
}

@("/", "/privacy-policy", "/terms", "/support", "/sms-disclosure", "/sms-opt-in") | ForEach-Object { Test-Endpoint "$($FrontendUrl.TrimEnd('/'))$_" }
@("/health", "/live", "/ready") | ForEach-Object { Test-Endpoint "$($BackendUrl.TrimEnd('/'))$_" }

if ($failed) { exit 1 }
exit 0
