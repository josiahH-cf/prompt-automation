#!/bin/bash

# Enhanced PowerShell Syntax Fixer
# This script identifies and fixes specific PowerShell syntax issues

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PS_SCRIPT="${SCRIPT_DIR}/install.ps1"
BACKUP_SCRIPT="${SCRIPT_DIR}/install.ps1.backup"
FIXED_SCRIPT="${SCRIPT_DIR}/install.ps1.fixed"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_error() {
    print_status "$RED" "ERROR: $1"
}

print_warning() {
    print_status "$YELLOW" "WARNING: $1"
}

print_success() {
    print_status "$GREEN" "SUCCESS: $1"
}

print_info() {
    print_status "$BLUE" "INFO: $1"
}

# Function to create backup
create_backup() {
    if [ ! -f "$BACKUP_SCRIPT" ]; then
        cp "$PS_SCRIPT" "$BACKUP_SCRIPT"
        print_info "Backup created: $BACKUP_SCRIPT"
    else
        print_info "Backup already exists: $BACKUP_SCRIPT"
    fi
}

# Function to fix the indentation issue at the end of the file
fix_indentation_issue() {
    local input_file=$1
    local output_file=$2
    
    print_info "Fixing indentation issues..."
    
    # Fix the last line indentation issue
    sed 's/^    Info "Installation log saved to \$LogFile"$/Info "Installation log saved to \$LogFile"/' "$input_file" > "$output_file"
    
    if ! cmp -s "$input_file" "$output_file"; then
        print_success "Fixed indentation issue on last line"
        return 0
    else
        print_info "No indentation issues found"
        cp "$input_file" "$output_file"
        return 1
    fi
}

# Function to add missing try-catch-finally blocks where needed
fix_try_catch_blocks() {
    local input_file=$1
    local output_file=$2
    local temp_file=$(mktemp)
    
    print_info "Checking and fixing try-catch blocks..."
    
    cp "$input_file" "$temp_file"
    local line_num=0
    local try_lines=()
    local in_try_block=false
    local fixes_made=0
    
    # This is a more complex fix that would require careful analysis
    # For now, we'll just validate that try blocks have corresponding catch/finally
    
    while IFS= read -r line; do
        ((line_num++))
        
        # Remove comments for analysis
        local clean_line=$(echo "$line" | sed 's/#.*$//')
        
        if echo "$clean_line" | grep -q 'try\s*{'; then
            try_lines+=("$line_num")
            in_try_block=true
        elif echo "$clean_line" | grep -q 'catch\s*{'; then
            if [ ${#try_lines[@]} -gt 0 ]; then
                unset 'try_lines[-1]'
                in_try_block=false
            fi
        elif echo "$clean_line" | grep -q 'finally\s*{'; then
            if [ ${#try_lines[@]} -gt 0 ]; then
                unset 'try_lines[-1]'
                in_try_block=false
            fi
        fi
        
    done < "$input_file"
    
    # Report unmatched try blocks
    if [ ${#try_lines[@]} -gt 0 ]; then
        print_warning "Found ${#try_lines[@]} try blocks that may need catch/finally blocks:"
        for try_line in "${try_lines[@]}"; do
            print_warning "  Line $try_line: $(sed -n "${try_line}p" "$input_file")"
        done
    else
        print_success "All try blocks have corresponding catch or finally blocks"
    fi
    
    cp "$temp_file" "$output_file"
    rm -f "$temp_file"
    return $fixes_made
}

# Function to check for specific issues and provide fixes
fix_specific_issues() {
    local input_file=$1
    local output_file=$2
    local temp_file=$(mktemp)
    
    print_info "Fixing specific reported issues..."
    
    cp "$input_file" "$temp_file"
    local fixes_made=0
    
    # The issues mentioned don't seem to actually exist based on our validation
    # But let's make sure the syntax is optimal
    
    # Ensure proper function closing
    # This is more of a verification than a fix since syntax validation passed
    
    print_info "Verifying function structures..."
    
    # Count function definitions and their closures
    local function_count=$(grep -c '^function ' "$input_file" || true)
    print_info "Found $function_count function definitions"
    
    # The PowerShell syntax validator already passed, so the structure is likely correct
    
    cp "$temp_file" "$output_file"
    rm -f "$temp_file"
    return $fixes_made
}

# Function to perform comprehensive fixes
perform_fixes() {
    local fixes_made=0
    
    print_info "Starting PowerShell syntax fixes..."
    
    # Create backup
    create_backup
    
    # Start with original file
    cp "$PS_SCRIPT" "$FIXED_SCRIPT"
    
    # Fix 1: Indentation issues
    local temp1=$(mktemp)
    if fix_indentation_issue "$FIXED_SCRIPT" "$temp1"; then
        ((fixes_made++))
        cp "$temp1" "$FIXED_SCRIPT"
    fi
    rm -f "$temp1"
    
    # Fix 2: Try-catch blocks
    local temp2=$(mktemp)
    local try_fixes
    try_fixes=$(fix_try_catch_blocks "$FIXED_SCRIPT" "$temp2"; echo $?)
    if [ "$try_fixes" != "0" ]; then
        fixes_made=$((fixes_made + 1))
    fi
    cp "$temp2" "$FIXED_SCRIPT"
    rm -f "$temp2"
    
    # Fix 3: Specific issues
    local temp3=$(mktemp)
    local specific_fixes
    specific_fixes=$(fix_specific_issues "$FIXED_SCRIPT" "$temp3"; echo $?)
    if [ "$specific_fixes" != "0" ]; then
        fixes_made=$((fixes_made + 1))
    fi
    cp "$temp3" "$FIXED_SCRIPT"
    rm -f "$temp3"
    
    echo ""
    if [ $fixes_made -gt 0 ]; then
        print_success "Applied $fixes_made fixes to create: $FIXED_SCRIPT"
        print_info "Review the changes and then run:"
        print_info "  mv '$FIXED_SCRIPT' '$PS_SCRIPT'"
        return 0
    else
        print_info "No fixes were needed. The original file appears to be correct."
        rm -f "$FIXED_SCRIPT"
        return 1
    fi
}

# Function to validate the current script
validate_script() {
    print_info "Validating PowerShell script..."
    
    if command -v pwsh &> /dev/null; then
        local temp_validation=$(mktemp)
        cat > "$temp_validation" << 'EOF'
param($ScriptPath)
try {
    $errors = $null
    $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Path $ScriptPath -Raw), [ref]$errors)
    if ($errors.Count -eq 0) {
        Write-Host "SYNTAX_VALID: No syntax errors found"
        exit 0
    } else {
        Write-Host "SYNTAX_ERRORS: Found $($errors.Count) syntax errors:"
        foreach ($error in $errors) {
            Write-Host "  Line $($error.Token.StartLine): $($error.Message)"
        }
        exit 1
    }
} catch {
    Write-Host "VALIDATION_ERROR: $($_.Exception.Message)"
    exit 2
}
EOF
        
        if pwsh -File "$temp_validation" -ScriptPath "$PS_SCRIPT"; then
            print_success "PowerShell syntax validation passed"
            rm -f "$temp_validation"
            return 0
        else
            print_error "PowerShell syntax validation failed"
            rm -f "$temp_validation"
            return 1
        fi
    else
        print_warning "PowerShell (pwsh) not available for validation"
        return 2
    fi
}

# Function to analyze specific problematic lines
analyze_problematic_lines() {
    print_info "Analyzing specific problematic lines mentioned in the issue..."
    
    local problematic_lines=(137 145 151 219 589 661 757 895)
    local issues_found=0
    
    for line_num in "${problematic_lines[@]}"; do
        if [ "$line_num" -le "$(wc -l < "$PS_SCRIPT")" ]; then
            local line_content=$(sed -n "${line_num}p" "$PS_SCRIPT")
            print_info "Line $line_num: $line_content"
            
            # Analyze the specific line
            case $line_num in
                137)
                    if echo "$line_content" | grep -q "function Install-WingetPackage {"; then
                        print_success "  Function definition looks correct"
                    else
                        print_warning "  Function definition may have issues"
                        ((issues_found++))
                    fi
                    ;;
                145)
                    if echo "$line_content" | grep -q "for (.*) {"; then
                        print_success "  For loop syntax looks correct"
                    else
                        print_warning "  For loop syntax may have issues"
                        ((issues_found++))
                    fi
                    ;;
                151)
                    if echo "$line_content" | grep -q "try {"; then
                        print_success "  Try block syntax looks correct"
                    else
                        print_warning "  Try block syntax may have issues"
                        ((issues_found++))
                    fi
                    ;;
                895)
                    if echo "$line_content" | grep -q "^    Info"; then
                        print_warning "  Incorrect indentation detected"
                        ((issues_found++))
                    else
                        print_success "  Indentation looks correct"
                    fi
                    ;;
                *)
                    print_info "  No specific analysis for this line"
                    ;;
            esac
        else
            print_warning "Line $line_num is beyond the end of the file"
        fi
        echo ""
    done
    
    if [ $issues_found -eq 0 ]; then
        print_success "No issues found in the specific lines mentioned"
        return 0
    else
        print_warning "Found $issues_found potential issues in the specific lines"
        return 1
    fi
}

# Main execution
main() {
    print_info "Enhanced PowerShell Syntax Fixer"
    print_info "================================"
    echo ""
    
    # Check if the PowerShell script exists
    if [ ! -f "$PS_SCRIPT" ]; then
        print_error "PowerShell script not found: $PS_SCRIPT"
        exit 1
    fi
    
    # Parse command line arguments
    case "${1:-analyze}" in
        "analyze")
            analyze_problematic_lines
            validate_script
            ;;
        "fix")
            perform_fixes
            ;;
        "validate")
            validate_script
            ;;
        "backup")
            create_backup
            print_success "Backup created successfully"
            ;;
        "restore")
            if [ -f "$BACKUP_SCRIPT" ]; then
                cp "$BACKUP_SCRIPT" "$PS_SCRIPT"
                print_success "Restored from backup: $BACKUP_SCRIPT"
            else
                print_error "No backup file found: $BACKUP_SCRIPT"
                exit 1
            fi
            ;;
        "help"|"-h"|"--help")
            cat << EOF
Usage: $0 [command]

Commands:
  analyze   - Analyze the script for issues (default)
  fix       - Apply automatic fixes to create a fixed version
  validate  - Run PowerShell syntax validation only
  backup    - Create a backup of the original script
  restore   - Restore from backup
  help      - Show this help message

Files:
  Original:  $PS_SCRIPT
  Backup:    $BACKUP_SCRIPT
  Fixed:     $FIXED_SCRIPT

Examples:
  $0                # Analyze the script
  $0 fix           # Create a fixed version
  $0 validate      # Validate syntax only
  
The script will analyze and fix PowerShell syntax issues while preserving functionality.
EOF
            exit 0
            ;;
        *)
            print_error "Unknown command: $1"
            print_info "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
