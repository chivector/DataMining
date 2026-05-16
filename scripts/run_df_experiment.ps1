$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RootDir

if (-not $env:WORKERS) { $env:WORKERS = "12" }
if (-not $env:LOG_EVERY) { $env:LOG_EVERY = "5" }
if (-not $env:FLUSH_EVERY) { $env:FLUSH_EVERY = "5" }
if (-not $env:REPEATS) { $env:REPEATS = "3" }
if (-not $env:REPEAT_MODE) { $env:REPEAT_MODE = "copy" }
if (-not $env:PROVIDER) { $env:PROVIDER = "df" }

$EnvPath = Join-Path $RootDir ".env"
if (Test-Path $EnvPath) {
    Get-Content $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        if ($line.StartsWith("export ")) {
            $line = $line.Substring(7).Trim()
        }
        $parts = $line.Split("=", 2)
        if ($parts.Count -ne 2) { return }
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        if ($key -and -not [Environment]::GetEnvironmentVariable($key, "Process")) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

if (-not $env:DF_API_URL) {
    $env:DF_API_URL = "http://123.129.219.111:3000/v1"
}

if (-not $env:DF_API_KEY) {
    $secure = Read-Host "DF_API_KEY is not set. Paste it now" -AsSecureString
    $env:DF_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
}

if (-not $env:DF_API_KEY) {
    throw "DF_API_KEY is still empty; aborting."
}

Write-Host "Running from: $RootDir"
Write-Host "Provider: $env:PROVIDER"
Write-Host "DF_API_URL: $env:DF_API_URL"
Write-Host "Workers: $env:WORKERS"
Write-Host "Repeats: $env:REPEATS"
Write-Host "Repeat mode: $env:REPEAT_MODE"
Write-Host "Log every: $env:LOG_EVERY"
Write-Host "Flush every: $env:FLUSH_EVERY"

if (-not (Test-Path "data/experiment_prompts.csv")) {
    python scripts/build_experiment_prompts.py
}

python scripts/collect_experiment_responses.py `
    --provider $env:PROVIDER `
    --repeats ([int]$env:REPEATS) `
    --repeat-mode $env:REPEAT_MODE `
    --workers ([int]$env:WORKERS) `
    --log-every ([int]$env:LOG_EVERY) `
    --flush-every ([int]$env:FLUSH_EVERY)

python scripts/build_experiment_features.py
python scripts/analyze_experiment.py --provider $env:PROVIDER --repeats ([int]$env:REPEATS)

Write-Host "Done."
Write-Host "Raw responses: data/raw/model_responses_experiment.csv"
Write-Host "Behavior features: data/processed/behavior_features_experiment.csv"
Write-Host "Analysis outputs: outputs_experiment/"
