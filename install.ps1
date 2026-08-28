param(
    [Parameter(Mandatory = $true)]
    [string]$OutlineUrl
)

$ErrorActionPreference = "Stop"

$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $HOME ".claude\skills\outline"

New-Item -ItemType Directory -Force -Path (Join-Path $Target "scripts") | Out-Null
Copy-Item (Join-Path $Source "SKILL.md") (Join-Path $Target "SKILL.md") -Force
Copy-Item (Join-Path $Source "scripts\outline_cli.py") (Join-Path $Target "scripts\outline_cli.py") -Force

[Environment]::SetEnvironmentVariable("OUTLINE_URL", $OutlineUrl, "User")

Write-Host ""
Write-Host "Installed Outline skill to:"
Write-Host "  $Target"
Write-Host ""
Write-Host "OUTLINE_URL has been set to:"
Write-Host "  $OutlineUrl"
Write-Host ""
Write-Host "Now set your API key WITHOUT pasting it into this script:"
Write-Host '  [Environment]::SetEnvironmentVariable("OUTLINE_API_KEY", "ol_api_YOUR_NEW_KEY", "User")'
Write-Host ""
Write-Host "Then fully quit and reopen your editor/terminal so it inherits the environment variables."
