#!/bin/bash
# Macolint Installation Script
# Supports macOS and Linux

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# GitHub repository
REPO_URL="https://github.com/p4puniya/Macolint.git"
INSTALL_URL="git+${REPO_URL}"

# Print colored messages (using printf for better compatibility)
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
    printf "${BLUE}  Macolint Installation${NC}\n"
    printf "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n\n"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    else
        OS="unknown"
    fi
    print_info "Detected OS: $OS"
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
        DETECTED_SHELL="bash"  # Default fallback
    fi
    print_info "Detected shell: $DETECTED_SHELL"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Extract version number from Python version string (portable)
# Python version strings are like "Python 3.9.5" or "Python 2.7.18"
extract_version() {
    # Try to match "Python X.Y" pattern first
    if echo "$1" | grep -q "Python [0-9]\+\.[0-9]\+"; then
        echo "$1" | sed -n 's/.*Python \([0-9]\+\.[0-9]\+\).*/\1/p' | head -1
    else
        # Fallback: extract first X.Y pattern
        echo "$1" | sed -n 's/.*\([0-9]\+\.[0-9]\+\).*/\1/p' | head -1
    fi
}

# Compare version numbers (returns 0 if version >= 3.8)
check_version() {
    local version=$1
    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)
    
    if [[ $major -gt 3 ]] || [[ $major -eq 3 && $minor -ge 8 ]]; then
        return 0
    else
        return 1
    fi
}

# Find Python executable
find_python() {
    # Always prefer python3 if available
    if command_exists python3; then
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    elif command_exists python; then
        # Check if it's Python 3 using the most reliable method
        PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "")
        
        if [[ -z "$PYTHON_VERSION" ]]; then
            # Fallback to version string parsing
            PYTHON_VERSION_STR=$(python --version 2>&1)
            PYTHON_VERSION=$(extract_version "$PYTHON_VERSION_STR")
        fi
        
        # Only use 'python' if it's actually Python 3
        if check_version "$PYTHON_VERSION"; then
            PYTHON_CMD="python"
            PIP_CMD="pip"
        else
            print_warning "Found 'python' but it's version $PYTHON_VERSION (Python 3.8+ required)"
            return 1
        fi
    else
        return 1
    fi
    
    # Final verification using Python itself (most reliable)
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "")
    
    if [[ -z "$PYTHON_VERSION" ]]; then
        # Last resort: parse version string
        PYTHON_VERSION_STR=$($PYTHON_CMD --version 2>&1)
        PYTHON_VERSION=$(extract_version "$PYTHON_VERSION_STR")
    fi
    
    if [[ -z "$PYTHON_VERSION" ]]; then
        print_error "Could not determine Python version"
        return 1
    fi
    
    if ! check_version "$PYTHON_VERSION"; then
        print_error "Python 3.8+ required, found $PYTHON_VERSION"
        return 1
    fi
    
    print_success "Found Python $PYTHON_VERSION"
    return 0
}

# Check pip availability
check_pip() {
    if ! command_exists "$PIP_CMD"; then
        print_error "$PIP_CMD not found"
        print_info "Installing pip..."
        
        if command_exists curl; then
            $PYTHON_CMD -m ensurepip --upgrade || {
                print_warning "Could not install pip automatically"
                print_info "Please install pip manually and run this script again"
                exit 1
            }
        else
            print_error "curl not found. Please install pip manually."
            exit 1
        fi
    fi
    
    print_success "Found $PIP_CMD"
}

# Install Macolint
install_macolint() {
    print_info "Installing Macolint from GitHub..."
    
    # Try to upgrade pip first (silently, don't fail if it doesn't work)
    $PIP_CMD install --upgrade pip --quiet 2>/dev/null || true
    
    # Install Macolint
    # Capture both stdout and stderr, but show errors if they occur
    if ! $PIP_CMD install "$INSTALL_URL" 2>&1; then
        print_error "Installation failed"
        print_info "Try running manually: $PIP_CMD install $INSTALL_URL"
        exit 1
    fi
    
    print_success "Macolint installed successfully"
}

# Setup shell wrapper and PATH
setup_macolint() {
    print_info "Configuring shell wrapper and PATH..."
    
    # Check if snip command is available
    if command_exists snip; then
        SNIP_CMD="snip"
    else
        # Use Python module syntax as fallback
        SNIP_CMD="$PYTHON_CMD -m macolint.cli"
        print_warning "snip command not in PATH, using Python module syntax"
    fi
    
    # Run setup with --fix-path flag
    if $SNIP_CMD setup --fix-path 2>&1; then
        print_success "Shell wrapper and PATH configured"
    else
        print_warning "Setup encountered some issues, but installation may still work"
        print_info "You can run 'snip setup --fix-path' manually later"
    fi
}

# Get shell reload command
get_reload_command() {
    case "$DETECTED_SHELL" in
        zsh)
            echo "source ~/.zshrc"
            ;;
        bash)
            echo "source ~/.bashrc"
            ;;
        fish)
            echo "source ~/.config/fish/config.fish"
            ;;
        *)
            echo "source ~/.${DETECTED_SHELL}rc"
            ;;
    esac
}

# Main installation flow
main() {
    print_header
    
    # Detect environment
    detect_os
    if [[ "$OS" == "unknown" ]]; then
        print_warning "Unknown OS, proceeding anyway..."
    fi
    
    detect_shell
    
    # Check Python
    if ! find_python; then
        print_error "Python 3.8+ is required but not found"
        print_info "Please install Python 3.8 or higher and run this script again"
        exit 1
    fi
    
    # Check pip
    check_pip
    
    # Install Macolint
    install_macolint
    
    # Setup shell wrapper
    setup_macolint
    
    # Success message
    printf "\n"
    print_success "Installation complete!"
    printf "\n"
    print_info "To start using Macolint, reload your shell:"
    printf "  ${GREEN}%s${NC}\n" "$(get_reload_command)"
    printf "\n"
    print_info "Or simply open a new terminal window."
    printf "\n"
    print_info "Try it out:"
    printf "  ${GREEN}snip doctor${NC}  # Check installation\n"
    printf "  ${GREEN}snip save test${NC}  # Save your first snippet\n"
    printf "\n"
}

# Run main function
main "$@"

