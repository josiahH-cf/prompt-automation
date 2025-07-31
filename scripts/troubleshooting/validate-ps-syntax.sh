#!/bin/bash

# Simple PowerShell Syntax Validation Script
# This script provides a quick way to validate PowerShell syntax from WSL/Linux

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PS_SCRIPT="${SCRIPT_DIR}/install.ps1"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}PowerShell Syntax Validator${NC}"
echo "=============================="
echo

if [ ! -f "$PS_SCRIPT" ]; then
    echo -e "${RED}ERROR: PowerShell script not found: $PS_SCRIPT${NC}"
    exit 1
fi

# Check if PowerShell is available
if command -v pwsh &> /dev/null; then
    PS_CMD="pwsh"
elif command -v powershell &> /dev/null; then
    PS_CMD="powershell"
else
    echo -e "${RED}ERROR: PowerShell not found. Install with:${NC}"
    echo "  sudo apt update"
    echo "  sudo apt install -y wget apt-transport-https software-properties-common"
    echo "  wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb"
    echo "  sudo dpkg -i packages-microsoft-prod.deb"
    echo "  sudo apt update"
    echo "  sudo apt install -y powershell"
    exit 1
fi

echo "Using PowerShell: $PS_CMD"
echo "Validating: $PS_SCRIPT"
echo

# Create temporary validation script
TEMP_VALIDATOR=$(mktemp)
cat > "$TEMP_VALIDATOR" << 'EOF'
param($ScriptPath)

try {
    Write-Host "Parsing PowerShell script..." -ForegroundColor Blue
    
    # Get the script content
    $scriptContent = Get-Content -Path $ScriptPath -Raw
    
    # Parse the script
    $errors = $null
    $tokens = [System.Management.Automation.PSParser]::Tokenize($scriptContent, [ref]$errors)
    
    if ($errors.Count -eq 0) {
        Write-Host "✓ SYNTAX VALID: No syntax errors found" -ForegroundColor Green
        Write-Host "  - Total tokens parsed: $($tokens.Count)" -ForegroundColor Gray
        Write-Host "  - Script length: $($scriptContent.Length) characters" -ForegroundColor Gray
        exit 0
    } else {
        Write-Host "✗ SYNTAX ERRORS FOUND: $($errors.Count) error(s)" -ForegroundColor Red
        Write-Host ""
        foreach ($error in $errors) {
            $line = $error.Token.StartLine
            $column = $error.Token.StartColumn
            $message = $error.Message
            Write-Host "  Line $line, Column $column : $message" -ForegroundColor Yellow
        }
        exit 1
    }
} catch {
    Write-Host "✗ VALIDATION ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 2
}
EOF

# Run the validation
if $PS_CMD -File "$TEMP_VALIDATOR" -ScriptPath "$PS_SCRIPT"; then
    echo
    echo -e "${GREEN}SUCCESS: PowerShell syntax is valid!${NC}"
    RESULT=0
else
    echo
    echo -e "${RED}FAILED: PowerShell syntax validation failed${NC}"
    RESULT=1
fi

# Clean up
rm -f "$TEMP_VALIDATOR"

echo
echo "Additional validation tools available:"
echo "  ./check-powershell-syntax.sh     - Comprehensive syntax analysis"
echo "  ./fix-powershell-syntax.sh       - Advanced syntax fixing tools"

exit $RESULT
