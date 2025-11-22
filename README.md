# Macolint

A terminal-first snippet manager with encrypted local storage.

## Phase 0 - Concept Demo

This is the initial local-only version demonstrating the core concept: save, search, and retrieve code snippets directly from the terminal.

## Features

- **Save snippets**: From clipboard or explicit content
- **List snippets**: Browse all saved snippets
- **Get snippets**: Copy to clipboard with fuzzy search
- **Encrypted storage**: AES-256-GCM encryption for all snippet content
- **Fuzzy search**: Uses `fzf` if available, falls back to interactive search

## Installation

### Prerequisites

- Rust (latest stable version)
- `fzf` (optional, but recommended for better search experience)

### Build and Install

```bash
# Clone the repository
git clone <repository-url>
cd macolint

# Build the project
cargo build --release

# Install using the install script
./scripts/install.sh

# Or manually copy the binary
cp target/release/snip ~/.local/bin/
```

Make sure `~/.local/bin` (or your chosen install directory) is in your PATH.

## Usage

### Save a snippet

```bash
# Save from clipboard
snip save deploy-prod

# Save with explicit content
snip save deploy-prod "kubectl apply -f deployment.yaml"
```

### List all snippets

```bash
snip list
```

### Get a snippet (copy to clipboard)

```bash
# Get by name
snip get deploy-prod

# Open fuzzy search (if no name provided)
snip get
```

## Shell Integration

To enable hotkey support (Ctrl+Shift+S / Cmd+Shift+S), add the appropriate configuration to your shell:

### Zsh

Add to `~/.zshrc`:

```bash
source /path/to/macolint/scripts/shell-integration/zsh.zsh
```

### Bash

Add to `~/.bashrc` or `~/.bash_profile`:

```bash
source /path/to/macolint/scripts/shell-integration/bash.sh
```

### Fish

Add to `~/.config/fish/config.fish`:

```fish
source /path/to/macolint/scripts/shell-integration/fish.fish
```

**Note**: Terminal key bindings may vary. You may need to adjust the bindings in the shell integration scripts based on your terminal emulator.

## Data Storage

- **Config**: `~/.config/macolint/config.json` (or platform-specific config directory)
- **Database**: `~/.local/share/macolint/snippets.db` (or platform-specific data directory)
- **Master Key**: Stored in config file (Phase 0). Future phases will migrate to OS keychain.

## Security

- All snippet content is encrypted using AES-256-GCM before storage
- Encryption key is derived from a master key using PBKDF2
- Master key is generated on first run and stored in the config file

**Phase 0 Note**: The master key is stored in plain text in the config file. This is acceptable for Phase 0 (local-only), but future phases will migrate to OS keychain storage.

## Future Phases

- **Phase 1-2**: Enhanced features and UX improvements
- **Phase 3**: Cloud sync, authentication, and team sharing
- **Phase 4**: Security enhancements (OS keychain, execution safety, audit logs)

## Development

### Project Structure

```
macolint/
├── src/
│   ├── main.rs           # CLI entry point
│   ├── commands/         # Command implementations
│   ├── storage/          # Database and encryption
│   ├── search/           # Fuzzy search
│   └── config.rs         # Configuration management
├── scripts/              # Installation and shell integration
└── tests/                # Tests
```

### Running Tests

```bash
cargo test
```

### Building

```bash
cargo build --release
```

## License

MIT

