#!/bin/bash

# Macolint installation script

set -e

echo "Installing Macolint..."

# Build the project
echo "Building Macolint..."
cargo build --release

# Determine install directory
INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "$INSTALL_DIR"

# Copy binary
BINARY_PATH="target/release/snip"
if [ -f "$BINARY_PATH" ]; then
    cp "$BINARY_PATH" "$INSTALL_DIR/snip"
    chmod +x "$INSTALL_DIR/snip"
    echo "✓ Installed snip to $INSTALL_DIR"
else
    echo "Error: Binary not found at $BINARY_PATH"
    echo "Please run 'cargo build --release' first"
    exit 1
fi

# Check if install directory is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "⚠️  Warning: $INSTALL_DIR is not in your PATH"
    echo "Add this to your shell config:"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
    echo ""
fi

echo ""
echo "✓ Installation complete!"
echo ""
echo "To set up shell integration, add the appropriate config to your shell:"
echo "  - zsh: source scripts/shell-integration/zsh.zsh"
echo "  - bash: source scripts/shell-integration/bash.sh"
echo "  - fish: source scripts/shell-integration/fish.fish"
echo ""
echo "Run 'snip --help' to get started!"

