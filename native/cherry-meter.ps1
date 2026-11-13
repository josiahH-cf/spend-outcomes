# Requires an existing Python 3.10+ on PATH. Does not change execution policy.
$ErrorActionPreference = 'Stop'
$python = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $python) {
    Write-Error 'Cherry Meter needs an existing Python 3.10+ runtime on PATH. No software was installed.'
    exit 2
}
& $python.Source (Join-Path $PSScriptRoot 'launch.py') @args
exit $LASTEXITCODE
