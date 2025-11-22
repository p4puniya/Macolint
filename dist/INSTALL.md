# Macolint Installation Guide

Choose the installation method that works best for your platform.

## Quick Install (Recommended)

### macOS / Linux (Homebrew)

```bash
brew tap p4puniya/macolint && brew install macolint
```

### Windows (Scoop)

```powershell
# Add bucket (if using custom bucket)
scoop bucket add macolint https://github.com/p4puniya/macolint-scoop
scoop install macolint

# Or if added to main bucket
scoop install macolint
```

### Windows (Winget)

```powershell
winget install Macolint.Macolint
```

### Arch Linux (AUR)

```bash
# Using yay
yay -S macolint

# Using paru
paru -S macolint

# Or manually
git clone https://aur.archlinux.org/macolint.git
cd macolint
makepkg -si
```

### Cargo Install (Cross-platform, requires Rust)

```bash
cargo install macolint
```

## Manual Installation

### Download Pre-built Binaries

1. Visit the [Releases page](https://github.com/p4puniya/macolint/releases)
2. Download the binary for your platform:
   - macOS: `macolint-x86_64-apple-darwin.tar.gz` or `macolint-aarch64-apple-darwin.tar.gz`
   - Linux: `macolint-x86_64-unknown-linux-gnu.tar.gz` or `macolint-aarch64-unknown-linux-gnu.tar.gz`
   - Windows: `macolint-x86_64-pc-windows-msvc.zip`

3. Extract and add to PATH:

   **macOS/Linux:**
   ```bash
   tar -xzf macolint-*.tar.gz
   sudo mv snip /usr/local/bin/
   ```

   **Windows:**
   ```powershell
   Expand-Archive macolint-*.zip
   # Add the extracted directory to your PATH
   ```

### Build from Source

```bash
# Clone the repository
git clone https://github.com/p4puniya/macolint.git
cd macolint

# Build
cargo build --release

# Install
cargo install --path .
```

## Verify Installation

After installation, verify it works:

```bash
snip --help
```

You should see the help message with available commands.

## Platform-Specific Notes

### macOS

- Homebrew is the recommended method
- The binary will be installed to `/opt/homebrew/bin/snip` (Apple Silicon) or `/usr/local/bin/snip` (Intel)

### Linux

- For Debian/Ubuntu: Consider using the `.deb` package if available
- For Fedora/RHEL: Consider using the `.rpm` package if available
- For Arch: Use AUR (see above)

### Windows

- Scoop and Winget are both good options
- Make sure the binary directory is in your PATH
- You may need to restart your terminal after installation

## Troubleshooting

### Command not found

If `snip` command is not found after installation:

1. Check if the binary is in your PATH:
   ```bash
   which snip  # Linux/macOS
   where snip  # Windows
   ```

2. Add the installation directory to your PATH if needed

3. Restart your terminal

### Permission denied

On Linux/macOS, you may need to make the binary executable:

```bash
chmod +x /path/to/snip
```

## Next Steps

After installation, see the [README.md](../README.md) for usage instructions and shell integration setup.

