# Macolint - Quick Start Guide

A terminal-first snippet manager with encrypted local storage. Save, search, and retrieve code snippets directly from your terminal.

## Installation

### macOS / Linux (Homebrew)

```bash
brew tap p4puniya/macolint && brew install macolint
```

### Other Platforms

See [INSTALL.md](INSTALL.md) for Cargo, Windows, and other installation methods.

## Quick Commands

### Save a Snippet

**From clipboard:**
```bash
snip save deploy-prod
# Copies whatever is in your clipboard and saves it as "deploy-prod"
```

**With explicit content:**
```bash
snip save deploy-prod "kubectl apply -f deployment.yaml"
```

### List All Snippets

```bash
snip list
```

Output:
```
Found 3 snippet(s):

Name                           Updated
--------------------------------------------------
deploy-prod                    2024-01-15 10:30:00
docker-clean                   2024-01-14 15:20:00
start-db                       2024-01-13 09:15:00
```

### Get a Snippet (Copy to Clipboard)

**By name:**
```bash
snip get deploy-prod
# ✓ Copied to clipboard: deploy-prod
```

**Fuzzy search (interactive):**
```bash
snip get
# Opens fuzzy search interface (uses fzf if available)
# Type to search, select snippet, it's copied to clipboard
```

## Common Use Cases

### Save Commands You Use Often

```bash
# Save a deployment command
snip save deploy "kubectl apply -f k8s/ && kubectl rollout status deployment/app"

# Save a database command
snip save db-reset "docker-compose down -v && docker-compose up -d postgres"

# Save a cleanup command
snip save clean "docker system prune -af && npm cache clean --force"
```

### Quick Access with Fuzzy Search

```bash
# Just type "snip get" and search for what you need
snip get
# > deploy
#   docker-clean
#   start-db
# Select one, it's instantly in your clipboard!
```

### Workflow Example

```bash
# 1. Copy a command to clipboard
echo "npm run build && npm run test" | pbcopy  # macOS
# or
echo "npm run build && npm run test" | xclip   # Linux

# 2. Save it
snip save build-test

# 3. Later, retrieve it instantly
snip get build-test
# Now paste it anywhere (Cmd+V / Ctrl+V)
```

## Shell Integration (Optional)

Add hotkey support to open fuzzy search instantly:

### Zsh

Add to `~/.zshrc`:
```bash
source /path/to/macolint/scripts/shell-integration/zsh.zsh
```

### Bash

Add to `~/.bashrc`:
```bash
source /path/to/macolint/scripts/shell-integration/bash.sh
```

### Fish

Add to `~/.config/fish/config.fish`:
```fish
source /path/to/macolint/scripts/shell-integration/fish.fish
```

Then press `Ctrl+Shift+S` (or configured hotkey) to open fuzzy search!

## Data Storage

- **Config**: `~/.config/macolint/config.json`
- **Database**: `~/.local/share/macolint/snippets.db`
- All snippet content is **encrypted** with AES-256-GCM

## Tips

1. **Use descriptive names**: `deploy-prod` is better than `d1`
2. **Fuzzy search is powerful**: Just type `snip get` and search by any part of the name
3. **Works with any text**: Not just commands - save notes, config snippets, etc.
4. **Encrypted by default**: Your snippets are encrypted before storage

## Help

```bash
snip --help
```

## Share with Your Team

Share this command with your team:
```bash
brew tap p4puniya/macolint && brew install macolint
```

Then they can start using `snip` immediately!

---

**GitHub**: https://github.com/p4puniya/macolint

