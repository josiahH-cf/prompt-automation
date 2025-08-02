# Test script to verify component detection functions
. "$PSScriptRoot/utils.ps1"

Write-Host "=== Testing Component Detection Functions ===" -ForegroundColor Cyan

$components = @('Python', 'pipx', 'fzf', 'espanso', 'AutoHotkey', 'prompt-automation')

foreach ($component in $components) {
    Write-Host "`nTesting ${component}:" -ForegroundColor Yellow
    
    # Test smart detection
    $smartResult = Test-ComponentAvailability -ComponentName $component
    Write-Host "  Smart detection: $smartResult" -ForegroundColor $(if ($smartResult) { 'Green' } else { 'Red' })
    
    # Test basic Get-Command detection
    $basicResult = (Get-Command $component -ErrorAction SilentlyContinue) -ne $null
    Write-Host "  Basic detection: $basicResult" -ForegroundColor $(if ($basicResult) { 'Green' } else { 'Red' })
    
    # Show status
    Write-Host "  Status display: " -NoNewline
    Show-ComponentStatus -ComponentName $component
}

Write-Host "`n=== Testing Startup Configuration ===" -ForegroundColor Cyan
$startupStatus = Test-StartupConfiguration
Write-Host "AutoHotkey startup: $($startupStatus.AutoHotkey)" -ForegroundColor $(if ($startupStatus.AutoHotkey) { 'Green' } else { 'Red' })
Write-Host "espanso startup: $($startupStatus.Espanso)" -ForegroundColor $(if ($startupStatus.Espanso) { 'Green' } else { 'Red' })

if ($startupStatus.Issues.Count -gt 0) {
    Write-Host "`nIssues found:" -ForegroundColor Yellow
    foreach ($issue in $startupStatus.Issues) {
        Write-Host "  - $issue" -ForegroundColor Red
    }
}

Write-Host "`n=== Testing espanso Status ===" -ForegroundColor Cyan
$espansoCmd = Get-Command espanso -ErrorAction SilentlyContinue
if ($espansoCmd) {
    try {
        $espansoStatus = & espanso status 2>&1
        Write-Host "espanso status output: $espansoStatus"
        
        $serviceStatus = & espanso service status 2>&1
        Write-Host "espanso service status: $serviceStatus"
    } catch {
        Write-Host "Error testing espanso: $_" -ForegroundColor Red
    }
} else {
    Write-Host "espanso not found" -ForegroundColor Red
}
