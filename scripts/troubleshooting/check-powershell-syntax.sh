#!/bin/bash

# PowerShell Syntax Checker for WSL/Linux
# This script validates PowerShell syntax and checks for common issues

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PS_SCRIPT="${SCRIPT_DIR}/install.ps1"
LOG_FILE="${SCRIPT_DIR}/syntax-check.log"

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

# Function to check if PowerShell is available
check_powershell() {
    if command -v pwsh &> /dev/null; then
        echo "pwsh"
        return 0
    elif command -v powershell &> /dev/null; then
        echo "powershell"
        return 0
    else
        return 1
    fi
}

# Function to validate PowerShell syntax using pwsh/powershell
validate_syntax_with_powershell() {
    local ps_cmd=$1
    local script_path=$2
    
    print_info "Validating PowerShell syntax using $ps_cmd..."
    
    # Create a temporary script to test syntax
    local temp_script=$(mktemp)
    cat > "$temp_script" << 'EOF'
param($ScriptPath)
try {
    $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Path $ScriptPath -Raw), [ref]$null)
    Write-Host "SYNTAX_OK: PowerShell syntax validation passed"
    exit 0
} catch {
    Write-Host "SYNTAX_ERROR: $($_.Exception.Message)"
    exit 1
}
EOF
    
    if $ps_cmd -File "$temp_script" -ScriptPath "$script_path" 2>&1 | tee -a "$LOG_FILE"; then
        rm -f "$temp_script"
        return 0
    else
        rm -f "$temp_script"
        return 1
    fi
}

# Function to check brace matching manually
check_brace_matching() {
    local script_path=$1
    print_info "Checking brace matching in $script_path..."
    
    local line_num=0
    local brace_stack=()
    local errors=0
    
    while IFS= read -r line; do
        ((line_num++))
        
        # Remove comments and strings to avoid false positives
        local clean_line=$(echo "$line" | sed 's/#.*$//' | sed 's/"[^"]*"//g' | sed "s/'[^']*'//g")
        
        # Count braces
        local open_braces=$(echo "$clean_line" | grep -o '{' | wc -l)
        local close_braces=$(echo "$clean_line" | grep -o '}' | wc -l)
        
        # Add to stack
        for ((i=0; i<open_braces; i++)); do
            brace_stack+=("$line_num")
        done
        
        # Remove from stack
        for ((i=0; i<close_braces; i++)); do
            if [ ${#brace_stack[@]} -eq 0 ]; then
                print_error "Line $line_num: Unexpected closing brace '}'"
                ((errors++))
            else
                unset 'brace_stack[-1]'
            fi
        done
        
    done < "$script_path"
    
    # Check for unclosed braces
    if [ ${#brace_stack[@]} -gt 0 ]; then
        print_error "Unclosed braces found starting at lines: ${brace_stack[*]}"
        ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        print_success "Brace matching validation passed"
        return 0
    else
        print_error "Found $errors brace matching errors"
        return 1
    fi
}

# Function to check try-catch blocks
check_try_catch_blocks() {
    local script_path=$1
    print_info "Checking try-catch block structure..."
    
    local line_num=0
    local try_lines=()
    local errors=0
    
    while IFS= read -r line; do
        ((line_num++))
        
        # Remove comments
        local clean_line=$(echo "$line" | sed 's/#.*$//')
        
        if echo "$clean_line" | grep -q 'try\s*{'; then
            try_lines+=("$line_num")
        elif echo "$clean_line" | grep -q 'catch\s*{'; then
            if [ ${#try_lines[@]} -eq 0 ]; then
                print_error "Line $line_num: catch block without preceding try block"
                ((errors++))
            else
                unset 'try_lines[-1]'
            fi
        elif echo "$clean_line" | grep -q 'finally\s*{'; then
            if [ ${#try_lines[@]} -eq 0 ]; then
                print_error "Line $line_num: finally block without preceding try block"
                ((errors++))
            else
                unset 'try_lines[-1]'
            fi
        fi
        
    done < "$script_path"
    
    # Check for unmatched try blocks
    if [ ${#try_lines[@]} -gt 0 ]; then
        for try_line in "${try_lines[@]}"; do
            print_error "Line $try_line: try block without matching catch or finally block"
            ((errors++))
        done
    fi
    
    if [ $errors -eq 0 ]; then
        print_success "Try-catch block validation passed"
        return 0
    else
        print_error "Found $errors try-catch block errors"
        return 1
    fi
}

# Function to check if-else structure
check_if_else_structure() {
    local script_path=$1
    print_info "Checking if-else block structure..."
    
    local line_num=0
    local errors=0
    
    while IFS= read -r line; do
        ((line_num++))
        
        # Remove comments
        local clean_line=$(echo "$line" | sed 's/#.*$//')
        
        # Check for else without preceding if
        if echo "$clean_line" | grep -qE '^\s*}\s*else\s*{?' && \
           ! echo "$clean_line" | grep -qE 'if.*else'; then
            # This is likely a proper else after a closing brace
            continue
        elif echo "$clean_line" | grep -qE '^\s*else\s*{?' && \
             ! echo "$clean_line" | grep -qE 'if.*else'; then
            # Check if previous non-empty line ends with }
            local prev_line_num=$((line_num - 1))
            local found_closing_brace=false
            
            while [ $prev_line_num -gt 0 ]; do
                local prev_line=$(sed -n "${prev_line_num}p" "$script_path")
                local clean_prev=$(echo "$prev_line" | sed 's/#.*$//' | tr -d ' \t')
                
                if [ -n "$clean_prev" ]; then
                    if echo "$clean_prev" | grep -q '}$'; then
                        found_closing_brace=true
                    fi
                    break
                fi
                ((prev_line_num--))
            done
            
            if [ "$found_closing_brace" = false ]; then
                print_error "Line $line_num: else statement without proper preceding if block closure"
                ((errors++))
            fi
        fi
        
    done < "$script_path"
    
    if [ $errors -eq 0 ]; then
        print_success "If-else structure validation passed"
        return 0
    else
        print_error "Found $errors if-else structure errors"
        return 1
    fi
}

# Function to check function definitions
check_function_definitions() {
    local script_path=$1
    print_info "Checking function definition structure..."
    
    local line_num=0
    local function_starts=()
    local errors=0
    
    while IFS= read -r line; do
        ((line_num++))
        
        # Remove comments
        local clean_line=$(echo "$line" | sed 's/#.*$//')
        
        if echo "$clean_line" | grep -qE '^\s*function\s+[^{]*\{\s*$'; then
            function_starts+=("$line_num")
        elif echo "$clean_line" | grep -qE '^\s*function\s+[^{]*$'; then
            # Function definition without opening brace on same line
            function_starts+=("$line_num")
        fi
        
    done < "$script_path"
    
    print_info "Found ${#function_starts[@]} function definitions"
    
    if [ $errors -eq 0 ]; then
        print_success "Function definition validation passed"
        return 0
    else
        print_error "Found $errors function definition errors"
        return 1
    fi
}

# Function to perform comprehensive syntax analysis
perform_syntax_analysis() {
    local script_path=$1
    
    print_info "Starting comprehensive PowerShell syntax analysis..."
    print_info "Script: $script_path"
    print_info "Log file: $LOG_FILE"
    
    # Clear previous log
    > "$LOG_FILE"
    
    local total_errors=0
    
    # Test 1: PowerShell native syntax validation (if available)
    local ps_cmd
    if ps_cmd=$(check_powershell); then
        print_info "Found PowerShell: $ps_cmd"
        if ! validate_syntax_with_powershell "$ps_cmd" "$script_path"; then
            ((total_errors++))
        fi
    else
        print_warning "PowerShell not found in PATH. Skipping native syntax validation."
        print_info "To install PowerShell on Ubuntu/Debian:"
        print_info "  wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb"
        print_info "  sudo dpkg -i packages-microsoft-prod.deb"
        print_info "  sudo apt-get update"
        print_info "  sudo apt-get install -y powershell"
    fi
    
    # Test 2: Manual brace matching
    if ! check_brace_matching "$script_path"; then
        ((total_errors++))
    fi
    
    # Test 3: Try-catch block validation
    if ! check_try_catch_blocks "$script_path"; then
        ((total_errors++))
    fi
    
    # Test 4: If-else structure validation
    if ! check_if_else_structure "$script_path"; then
        ((total_errors++))
    fi
    
    # Test 5: Function definition validation
    if ! check_function_definitions "$script_path"; then
        ((total_errors++))
    fi
    
    echo ""
    if [ $total_errors -eq 0 ]; then
        print_success "All syntax validation tests passed!"
        return 0
    else
        print_error "Found issues in $total_errors validation categories"
        print_info "Check the log file for details: $LOG_FILE"
        return 1
    fi
}

# Function to show specific line issues mentioned in the problem
check_specific_issues() {
    print_info "Checking specific line issues mentioned..."
    
    # The specific lines mentioned in the issue
    local problematic_lines=(137 145 151 219 589 661 757 895)
    
    for line_num in "${problematic_lines[@]}"; do
        if [ "$line_num" -le "$(wc -l < "$PS_SCRIPT")" ]; then
            print_info "Line $line_num:"
            sed -n "${line_num}p" "$PS_SCRIPT" | sed 's/^/  /'
            
            # Check surrounding context
            local start=$((line_num - 2))
            local end=$((line_num + 2))
            [ $start -lt 1 ] && start=1
            
            print_info "Context (lines $start-$end):"
            sed -n "${start},${end}p" "$PS_SCRIPT" | nl -ba -v$start | sed 's/^/  /'
            echo ""
        else
            print_warning "Line $line_num is beyond the end of the file"
        fi
    done
}

# Main execution
main() {
    print_info "PowerShell Syntax Checker for WSL/Linux"
    print_info "========================================"
    echo ""
    
    # Check if the PowerShell script exists
    if [ ! -f "$PS_SCRIPT" ]; then
        print_error "PowerShell script not found: $PS_SCRIPT"
        exit 1
    fi
    
    # Parse command line arguments
    case "${1:-check}" in
        "check")
            perform_syntax_analysis "$PS_SCRIPT"
            ;;
        "specific")
            check_specific_issues
            ;;
        "fix")
            print_info "Automated fix mode is not implemented yet."
            print_info "Please review the issues found and fix them manually."
            perform_syntax_analysis "$PS_SCRIPT"
            ;;
        "help"|"-h"|"--help")
            cat << EOF
Usage: $0 [command]

Commands:
  check     - Perform comprehensive syntax analysis (default)
  specific  - Show the specific problematic lines mentioned
  fix       - Attempt automated fixes (not implemented)
  help      - Show this help message

Examples:
  $0                # Run comprehensive check
  $0 check         # Same as above
  $0 specific      # Show specific problematic lines
  
The script will create a log file at: $LOG_FILE
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
