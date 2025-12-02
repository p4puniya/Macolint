#!/bin/bash
# Macolint Uninstall Script
# Removes Macolint from your system

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    printf "${BLUE}ℹ${NC} %s\n" "$1"
}

print_success() {
    printf "${GREEN}✓${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}✗${NC} %s\n" "$1"
}

print_header() {
    printf "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "${BLUE}  Macolint Uninstallation${NC}\n"
    printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n\n"
}

# Detect shell
detect_shell() {
    SHELL_NAME=$(basename "$SHELL" 2>/dev/null || echo "bash")
    if [[ "$SHELL_NAME" == "zsh" ]]; then
        DETECTED_SHELL="zsh"
    elif [[ "$SHELL_NAME" == "bash" ]]; then
        DETECTED_SHELL="bash"
    elif [[ "$SHELL_NAME" == "fish" ]]; then
        DETECTED_SHELL="fish"
    else
        DETECTED_SHELL="bash"
    fi
    print_info "Detected shell: $DETECTED_SHELL"
}

# Find Python executable
find_python() {
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
        PIP_CMD="pip"
    else
        print_error "Python not found"
        return 1
    fi
    return 0
}

# Uninstall Python package
uninstall_package() {
    print_info "Uninstalling Macolint Python package..."
    
    if $PIP_CMD uninstall -y macolint 2>/dev/null; then
        print_success "Python package uninstalled"
    else
        print_warning "Package may not be installed or already removed"
    fi
}

# Remove shell wrapper
remove_shell_wrapper() {
    print_info "Removing shell wrapper from config file..."
    
    case "$DETECTED_SHELL" in
        zsh)
            CONFIG_FILE="$HOME/.zshrc"
            ;;
        bash)
            CONFIG_FILE="$HOME/.bashrc"
            ;;
        fish)
            CONFIG_FILE="$HOME/.config/fish/config.fish"
            ;;
        *)
            CONFIG_FILE=""
            ;;
    esac
    
    if [[ -z "$CONFIG_FILE" ]]; then
        print_warning "Unknown shell, skipping wrapper removal"
        return
    fi
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        print_warning "Config file $CONFIG_FILE not found, skipping wrapper removal"
        return
    fi
    
    # Check if wrapper exists
    if grep -q "Macolint shell wrapper" "$CONFIG_FILE" 2>/dev/null; then
        # Create a backup
        cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        print_info "Created backup: ${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Remove the wrapper function
        # For zsh/bash: remove from "# Macolint shell wrapper" to the closing "}"
        # For fish: remove from "# Macolint shell wrapper" to "end"
        if [[ "$DETECTED_SHELL" == "fish" ]]; then
            # Fish uses "end" to close functions
            sed -i.bak '/# Macolint shell wrapper/,/^end$/d' "$CONFIG_FILE" 2>/dev/null || \
            sed -i '' '/# Macolint shell wrapper/,/^end$/d' "$CONFIG_FILE" 2>/dev/null || true
        else
            # Bash/Zsh use closing brace
            # Remove from comment to closing brace (handling multi-line)
            awk '/# Macolint shell wrapper/{flag=1} flag{if(/^}$/){flag=0; next}flag=0}1' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE" 2>/dev/null || \
            python3 -c "
import re
with open('$CONFIG_FILE', 'r') as f:
    content = f.read()
# Remove from Macolint comment to closing brace
pattern = r'# Macolint shell wrapper.*?\n\}\n'
content = re.sub(pattern, '', content, flags=re.DOTALL)
with open('$CONFIG_FILE', 'w') as f:
    f.write(content)
" 2>/dev/null || true
        fi
        
        # Clean up any remaining empty lines (more than 2 consecutive)
        sed -i.bak '/^$/N;/^\n$/d' "$CONFIG_FILE" 2>/dev/null || \
        sed -i '' '/^$/N;/^\n$/d' "$CONFIG_FILE" 2>/dev/null || true
        
        print_success "Shell wrapper removed from $CONFIG_FILE"
    else
        print_info "No shell wrapper found in $CONFIG_FILE"
    fi
}

# Remove data directory (optional)
remove_data_directory() {
    DATA_DIR="$HOME/.macolint"
    if [[ -d "$DATA_DIR" ]]; then
        print_warning "Data directory found: $DATA_DIR"
        read -p "Remove data directory? This will delete all your snippets! (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$DATA_DIR"
            print_success "Data directory removed"
        else
            print_info "Keeping data directory: $DATA_DIR"
        fi
    else
        print_info "No data directory found"
    fi
}

# Main uninstallation flow
main() {
    print_header
    
    detect_shell
    
    if ! find_python; then
        print_error "Python not found. Cannot uninstall package."
        print_info "You may need to manually remove shell wrapper from your config file"
        exit 1
    fi
    
    uninstall_package
    remove_shell_wrapper
    remove_data_directory
    
    printf "\n"
    print_success "Uninstallation complete!"
    printf "\n"
    print_info "To complete the uninstallation:"
    printf "  1. Reload your shell: ${GREEN}source ~/.${DETECTED_SHELL}rc${NC}\n"
    printf "  2. Or open a new terminal window\n"
    printf "\n"
    print_info "To reinstall, run:"
    printf "  ${GREEN}curl -fsSL https://raw.githubusercontent.com/p4puniya/Macolint/main/install.sh | sh${NC}\n"
    printf "\n"
}

# Run main function
main "$@"

