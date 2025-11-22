# Macolint Phase 0 Implementation Plan

## Overview

Build a terminal-first snippet manager CLI that demonstrates the core concept: save, search, and retrieve code snippets directly from the terminal with encrypted local storage.

## Project Structure

```
macolint/
├── Cargo.toml                 # Rust project config
├── README.md                  # Setup & usage instructions
├── src/
│   ├── main.rs               # CLI entry point & command routing
│   ├── commands/
│   │   ├── mod.rs
│   │   ├── save.rs           # `snip save` implementation
│   │   ├── list.rs           # `snip list` implementation
│   │   └── get.rs            # `snip get` implementation
│   ├── storage/
│   │   ├── mod.rs
│   │   ├── database.rs       # SQLite DB initialization & queries
│   │   └── encryption.rs     # AES-256 encryption/decryption
│   ├── search/
│   │   ├── mod.rs
│   │   └── fuzzy.rs          # fzf integration + fallback
│   └── config.rs             # Config file management (data dir, key derivation)
├── scripts/
│   ├── install.sh            # Installation script
│   └── shell-integration/    # Shell config snippets
│       ├── zsh.zsh
│       ├── bash.sh
│       └── fish.fish
└── tests/
    └── integration_test.rs
```

## Core Components

### 1. CLI Framework (`src/main.rs`)

- Use `clap` for argument parsing
- Commands: `save`, `list`, `get`
- Handle config initialization (first run setup)

### 2. Storage Layer (`src/storage/`)

- **database.rs**: SQLite schema with forward-compatible fields:
  - Core: `id`, `name`, `content_encrypted`, `created_at`, `updated_at`
  - Future sync (nullable): `user_id`, `team_id`, `synced_at`, `sync_status`
  - Allows Phase 3/4 cloud sync without schema migrations
- **encryption.rs**: 
  - AES-256-GCM encryption using `aes-gcm` crate
  - Key derivation from user's master key (stored in OS keychain or config)
  - Encrypt/decrypt snippet content before DB operations
  - **Note**: Content-level encryption is cloud-sync friendly (encrypted blobs can be synced safely)
- **trait/interface**: Define `Storage` trait early (even if single implementation) to allow cloud storage adapter in Phase 3

### 3. Commands (`src/commands/`)

- **save.rs**: 
  - `snip save <name>` → read from clipboard (use `clipboard` crate)
  - `snip save <name> <content>` → save explicit content
  - Encrypt and store in DB
- **list.rs**: 
  - Query all snippets, display name + preview
  - Format: table or simple list
- **get.rs**: 
  - `snip get <name>` → decrypt, copy to clipboard
  - `snip get` (no args) → open fuzzy search

### 4. Fuzzy Search (`src/search/fuzzy.rs`)

- Try to spawn `fzf` process with snippet names
- Fallback: simple interactive prompt with fuzzy matching (use `fuzzy-matcher` crate)
- Return selected snippet name

### 5. Shell Integration (`scripts/shell-integration/`)

- Generate shell-specific configs that:
  - Add `snip` to PATH (or provide install location)
  - Create alias/function for hotkey binding
  - Instructions for binding `Ctrl+Shift+S` / `Cmd+Shift+S`

### 6. Configuration (`src/config.rs`)

- Determine data directory (OS-specific: `~/.local/share/macolint/` or `~/Library/Application Support/macolint/`)
- Master key management (first-run generation, keychain storage optional)
- SQLite DB path: `{data_dir}/snippets.db`

## Key Dependencies (Cargo.toml)

```toml
[dependencies]
clap = { version = "4.4", features = ["derive"] }
rusqlite = { version = "0.31", features = ["bundled"] }
aes-gcm = "0.10"
clipboard = "0.5"
fuzzy-matcher = "0.3"
dirs = "5.0"
anyhow = "1.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

## Implementation Order

1. **Project setup**: Cargo.toml, basic CLI structure
2. **Config & storage**: Data directory, SQLite schema, encryption utilities
3. **Core commands**: `save`, `list`, `get` (basic versions)
4. **Fuzzy search**: fzf integration + fallback
5. **Shell integration**: Scripts and documentation
6. **Polish**: Error handling, user feedback, README

## Security Considerations (Phase 0)

- Master key stored in plain config file initially (acceptable for Phase 0)
- Later phases: migrate to OS keychain
- Encryption key derived from master key using PBKDF2 or Argon2

## Testing Strategy

- Unit tests for encryption/decryption
- Integration test for save → list → get flow
- Manual testing for fzf fallback scenarios