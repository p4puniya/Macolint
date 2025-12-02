#!/bin/bash
# Macolint Installation Script
# Supports macOS and Linux
# Version: 1.0.1

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

# Detect shell (prefer the *current* interactive shell over login shell)
detect_shell() {
    # Prefer explicit shell-specific environment variables first
    if [[ -n "$ZSH_VERSION" ]]; then
        DETECTED_SHELL="zsh"
    elif [[ -n "$BASH_VERSION" ]]; then
        DETECTED_SHELL="bash"
    elif [[ -n "$FISH_VERSION" ]]; then
        DETECTED_SHELL="fish"
    else
        # Fallback to login shell from $SHELL
        SHELL_NAME=$(basename "$SHELL" 2>/dev/null || echo "")
        if [[ "$SHELL_NAME" == "zsh" ]]; then
            DETECTED_SHELL="zsh"
        elif [[ "$SHELL_NAME" == "bash" ]]; then
            DETECTED_SHELL="bash"
        elif [[ "$SHELL_NAME" == "fish" ]]; then
            DETECTED_SHELL="fish"
        else
            DETECTED_SHELL="bash"  # Sensible default
        fi
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

# Determine absolute Python binary path for launcher
get_python_bin_path() {
    PYTHON_BIN_PATH=$(command -v "$PYTHON_CMD" 2>/dev/null || echo "$PYTHON_CMD")
}

# Choose a system-wide launcher directory for snip (brew-like behavior)
# Prefer /usr/local/bin, then /opt/local/bin, then /opt/macolint/bin
choose_launcher_dir() {
    local candidates=(
        "/usr/local/bin"
        "/opt/local/bin"
        "/opt/macolint/bin"
    )

    for dir in "${candidates[@]}"; do
        # If directory exists and is writable, use it
        if [[ -d "$dir" && -w "$dir" ]]; then
            echo "$dir"
            return 0
        fi

        # If it doesn't exist, but parent is writable, try to create it
        if [[ ! -e "$dir" ]]; then
            local parent
            parent="$(dirname "$dir")"
            if [[ -w "$parent" ]]; then
                mkdir -p "$dir" 2>/dev/null || true
                if [[ -d "$dir" && -w "$dir" ]]; then
                    echo "$dir"
                    return 0
                fi
            fi
        fi
    done

    # No suitable directory found
    echo ""
    return 1
}

# Create a simple launcher script that always uses the detected Python
# This avoids depending on where pip dropped the console script.
create_system_launcher() {
    LAUNCHER_DIR=""
    LAUNCHER_PATH=""

    get_python_bin_path

    local chosen_dir
    chosen_dir="$(choose_launcher_dir)"

    if [[ -z "$chosen_dir" ]]; then
        print_warning "Could not create a system-wide 'snip' launcher automatically."
        print_info "You can create one manually (may require sudo). For example:"
        printf "  ${GREEN}sudo sh -c 'printf \"#!/bin/sh\nexec %s -m macolint.cli \\\"\\\$@\\\"\\n\" > /usr/local/bin/snip && chmod +x /usr/local/bin/snip'${NC}\n" "$PYTHON_BIN_PATH"
        return 1
    fi

    LAUNCHER_DIR="$chosen_dir"
    LAUNCHER_PATH="${LAUNCHER_DIR}/snip"

    cat > "$LAUNCHER_PATH" <<EOF
#!/bin/sh
# Macolint system-wide launcher
exec "$PYTHON_BIN_PATH" -m macolint.cli "\$@"
EOF

    chmod +x "$LAUNCHER_PATH" || {
        print_warning "Created launcher at $LAUNCHER_PATH but could not mark it executable."
        return 1
    }

    print_success "Created system-wide 'snip' launcher at: $LAUNCHER_PATH"
    return 0
}

# Ensure launcher directory is visible to bash/zsh shells via PATH
ensure_launcher_on_path() {
    # Only manage PATH for bash/zsh, as requested
    if [[ "$DETECTED_SHELL" != "bash" && "$DETECTED_SHELL" != "zsh" ]]; then
        return 0
    fi

    # If launcher dir is empty or already on PATH, nothing to do
    if [[ -z "$LAUNCHER_DIR" ]]; then
        return 0
    fi

    case ":$PATH:" in
        *":$LAUNCHER_DIR:"*)
            # Already on PATH
            return 0
            ;;
    esac

    # If using the standard /usr/local/bin, most systems already have it on PATH.
    # If they don't, we still avoid modifying PATH silently here.
    if [[ "$LAUNCHER_DIR" == "/usr/local/bin" ]]; then
        print_warning "'snip' launcher is in /usr/local/bin, but it is not currently on PATH."
        print_info "Consider adding this to your shell config if needed:"
        printf "  ${GREEN}export PATH=\"/usr/local/bin:\$PATH\"${NC}\n"
        return 0
    fi

    local config_file
    if [[ "$DETECTED_SHELL" == "bash" ]]; then
        config_file="$HOME/.bashrc"
    else
        config_file="$HOME/.zshrc"
    fi

    local marker="# Macolint PATH setup"
    local export_line="export PATH=\"${LAUNCHER_DIR}:\$PATH\""

    if [[ -f "$config_file" ]]; then
        if grep -q "$marker" "$config_file" 2>/dev/null || grep -q "$LAUNCHER_DIR" "$config_file" 2>/dev/null; then
            print_info "PATH for Macolint already configured in $config_file"
            return 0
        fi
    fi

    mkdir -p "$(dirname "$config_file")" 2>/dev/null || true

    {
        echo ""
        echo "$marker"
        echo "$export_line"
    } >> "$config_file"

    print_success "Added Macolint launcher directory to PATH in $config_file"
    print_info "Reload your shell config for changes to take effect:"
    printf "  ${GREEN}source %s${NC}\n" "$config_file"
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
        print_info "If you see 'Could not find an activated virtualenv (required).' then your pip is configured to require a virtualenv."
        print_info "Either activate a virtualenv before installing, or override it for this install with:"
        printf "  ${GREEN}PIP_REQUIRE_VIRTUALENV=0 $PIP_CMD install $INSTALL_URL${NC}\n"
        exit 1
    fi
    
    print_success "Macolint installed successfully"
}

# Setup shell wrapper and PATH
setup_macolint() {
    print_info "Configuring shell wrapper and PATH..."
 
    # If we created a launcher, ensure its directory is discoverable for bash/zsh
    ensure_launcher_on_path

    # Prefer the system-wide launcher if we created one
    if [[ -n "$LAUNCHER_PATH" && -x "$LAUNCHER_PATH" ]]; then
        SNIP_CMD="$LAUNCHER_PATH"
    elif command_exists snip; then
        SNIP_CMD="snip"
    else
        # Use Python module syntax as fallback
        SNIP_CMD="$PYTHON_CMD -m macolint.cli"
        print_warning "snip command not in PATH, using Python module syntax"
    fi
    
    # Run setup with --fix-path flag, telling it which shell we detected.
    # This avoids situations where the login shell is bash but you're actually
    # running zsh (or vice‑versa).
    SETUP_SHELL_FLAG=""
    if [[ "$DETECTED_SHELL" == "bash" || "$DETECTED_SHELL" == "zsh" || "$DETECTED_SHELL" == "fish" ]]; then
        SETUP_SHELL_FLAG="--shell $DETECTED_SHELL"
    fi

    if $SNIP_CMD setup --fix-path $SETUP_SHELL_FLAG 2>&1; then
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

    # Create system-wide snip launcher (brew-like behavior)
    create_system_launcher
    
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

